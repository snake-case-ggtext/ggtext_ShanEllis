"""
:class:`RichText`, a matplotlib ``Text`` that understands Markdown/HTML.

How it works
------------
A matplotlib :class:`~matplotlib.text.Text` draws a string in a single
style. Everything that needs to know how big a text is — the
``constrained``/``tight`` layout engines, plotnine's layout engine,
legends (:class:`~matplotlib.offsetbox.TextArea`),
``bbox_inches="tight"`` — asks the artist through
``Text.get_window_extent()``, which in turn calls the (private)
``Text._get_layout(renderer)``.

:class:`RichText` subclasses ``Text`` and overrides exactly two methods:

``_get_layout``
    Parses the markup, measures every styled run with the renderer, wraps
    and aligns the lines, applies the rotation and the ``ha``/``va``/
    ``rotation_mode`` alignment exactly as ``Text`` does, and returns the
    result in the format the installed matplotlib expects.

``draw``
    Draws the optional box and then every run with
    ``renderer.draw_text`` at the positions computed above.

Because the artist *is* a ``Text``, every other ``Text`` method keeps
working (``set_color``, ``set_fontsize``, ``set_rotation``, ...): those
properties become the defaults for the unstyled parts of the text.

Converting existing artists
---------------------------
Libraries such as matplotlib and plotnine create their own ``Text``
artists (titles, tick labels, legend entries). :func:`make_rich` turns
such an artist into rich text *in place* by swapping its class for a
rich subclass of its own class. ggtext also registers a
``richtext`` property on ``Text``, so ``text.set(richtext=True)`` does
the same thing. That is the hook the plotnine integration uses: theme
elements pass their properties to ``text.set(**properties)``.
"""

from __future__ import annotations

import math
import warnings
from collections.abc import Callable
from functools import lru_cache
from typing import Any

import matplotlib as mpl
import numpy as np
from matplotlib import artist
from matplotlib.colors import to_rgba
from matplotlib.font_manager import findfont
from matplotlib.patches import FancyBboxPatch
from matplotlib.path import Path
from matplotlib.text import Text
from matplotlib.transforms import Affine2D, Bbox

from ._images import load_image
from ._layout import Fragment, Layout, layout_tokens
from ._parse import ImageRun, parse, plain_text
from ._spec import LENGTH_FIELDS, RichTextSpec, resolve_length
from ._style import Style

__all__ = ["RichText", "is_rich", "make_plain", "make_rich"]

MPL_VERSION = tuple(mpl.__version_info__[:2])  # type: ignore[attr-defined]
# matplotlib 3.11 changed the format of Text._get_layout and the way
# line heights are computed.
MPL_311 = MPL_VERSION >= (3, 11)

UNDERLINE_OFFSET = 0.12  # below the baseline, in ems
STRIKE_OFFSET = 0.28  # above the baseline, in ems
DECORATION_THICKNESS = 0.065  # in ems


# -----------------------------------------------------------------------
# Measuring with a matplotlib renderer
# -----------------------------------------------------------------------
class _BoundedCache(dict):
    """A dict that empties itself when it grows too large."""

    def __init__(self, maxsize: int):
        super().__init__()
        self.maxsize = maxsize

    def __setitem__(self, key, value):
        if len(self) >= self.maxsize:
            self.clear()
        super().__setitem__(key, value)


# Keys never hold renderers or figures, so nothing is kept alive.
_TEXT_METRICS = _BoundedCache(8192)
_FONT_METRICS = _BoundedCache(1024)


def _font_key(fp) -> tuple[int, str]:
    """
    Cache key for a font: its properties *and* the file they resolve to.

    A generic family such as ``"sans-serif"`` resolves through rcParams, so
    the same ``FontProperties`` can mean different fonts in different
    figures. matplotlib's ``findfont`` is itself cached and rcParams-aware.
    """
    return hash(fp), findfont(fp)


def _text_metrics(
    renderer_key: Any, renderer, s: str, fp, ismath: bool
) -> tuple[float, float, float]:
    """``(width, ascent, descent)`` of *s* in pixels."""
    key = (renderer_key, s, _font_key(fp), ismath)
    try:
        return _TEXT_METRICS[key]
    except KeyError:
        pass
    w, h, d = renderer.get_text_width_height_descent(s, fp, ismath=ismath)
    _TEXT_METRICS[key] = result = (w, h - d, d)
    return result


def _font_metrics(
    renderer_key: Any, renderer, fp, figure
) -> tuple[float, float, float]:
    """
    ``(ascent, descent, line_gap)`` of a font, as matplotlib sees it.

    We ask throw-away ``Text`` artists for their layout so that rich text
    is spaced exactly like plain text in the installed matplotlib.
    """
    key = (renderer_key, _font_key(fp))
    try:
        return _FONT_METRICS[key]
    except KeyError:
        pass
    if MPL_311:
        # Empty lines measure as the font's own ascent/descent (+ half the
        # line gap each for multi-line text)
        def lines_of(s):
            proxy = Text(0, 0, s, fontproperties=fp, linespacing="normal")
            proxy.set_figure(figure)
            return Text._get_layout(proxy, renderer)[1]

        ((_, (_, a, d), _),) = lines_of("")
        _, (_, a2, _), _ = lines_of("\n")[0]
        result = (a, d, 2 * (a2 - a))
    else:
        # matplotlib < 3.11 uses the box of "lp" as the minimum line box
        _, lp_h, lp_d = renderer.get_text_width_height_descent("lp", fp, ismath=False)
        result = (lp_h - lp_d, lp_d, 0.0)
    _FONT_METRICS[key] = result
    return result


class _Measurer:
    """Measures text and images for :func:`ggtext._layout.layout_tokens`."""

    def __init__(self, renderer, text: RichText):
        self.renderer = renderer
        self.figure = text.get_figure(root=True)
        self.dpi = self.figure.dpi if self.figure is not None else 72
        self.linespacing = text._linespacing
        # Renderer metrics depend on the renderer type and its dpi
        self.key = (type(renderer), getattr(renderer, "dpi", None), self.dpi)
        self._fps: dict[Style, Any] = {}

    def fontproperties(self, style: Style):
        fp = self._fps.get(style)
        if fp is None:
            fp = self._fps[style] = style.fontproperties()
        return fp

    def text(self, s: str, style: Style, math: bool):
        fp = self.fontproperties(style)
        if not s:
            return 0.0, 0.0, 0.0
        return _text_metrics(self.key, self.renderer, s, fp, math)

    def font_metrics(self, style: Style):
        fp = self.fontproperties(style)
        return _font_metrics(self.key, self.renderer, fp, self.figure)

    def points_to_pixels(self, points: float) -> float:
        return self.renderer.points_to_pixels(points)

    def image(self, run: ImageRun):
        arr = load_image(run.src)
        if arr is None:
            return 0.0, 0.0
        h_px, w_px = arr.shape[:2]
        aspect = w_px / h_px if h_px else 1.0
        width, height = run.width, run.height
        if width is None and height is None:
            # Default: as tall as the font size, so images sit nicely in
            # axis labels and legends.
            height = run.style.size or 10.0
        if width is None:
            width = height * aspect  # type: ignore[operator]
        elif height is None:
            height = width / aspect
        return self.points_to_pixels(width), self.points_to_pixels(height)


def _rotate(angle: float, x: float, y: float) -> tuple[float, float]:
    theta = math.radians(angle)
    c, s = math.cos(theta), math.sin(theta)
    return c * x - s * y, s * x + c * y


class _Geometry:
    """The laid out text plus how it is rotated and aligned."""

    __slots__ = ("angle", "bbox", "layout", "offsetx", "offsety", "xys")

    def __init__(self, layout, angle, offsetx, offsety, bbox, xys):
        self.layout: Layout = layout
        self.angle: float = angle
        self.offsetx: float = offsetx
        self.offsety: float = offsety
        self.bbox: Bbox = bbox  # rotated, axis aligned, relative to anchor
        self.xys: list[tuple[float, float]] = xys  # line starts

    def to_anchor(self, x: float, y: float) -> tuple[float, float]:
        """Box coordinates -> coordinates relative to the text anchor."""
        rx, ry = _rotate(self.angle, x, y)
        return rx - self.offsetx, ry - self.offsety


# Functions ``(text, figure) -> list of Axes or None`` that say which axes
# form the "panel area" of a figure-level text.
_PANEL_RESOLVERS: list[Callable[[Any, Any], Any]] = []


def register_panel_resolver(func: Callable[[Any, Any], Any]) -> None:
    """
    Register a function that finds the panel area of a figure-level text.

    *func* is called as ``func(text, figure)`` and returns the list of
    axes whose union is the reference for fractional widths, or None if
    it does not know. Used by integrations such as plotnine.
    """
    if func not in _PANEL_RESOLVERS:
        _PANEL_RESOLVERS.append(func)


# -----------------------------------------------------------------------
# The artist
# -----------------------------------------------------------------------
class RichText(Text):
    """
    A matplotlib text artist that renders Markdown, HTML and CSS.

    It accepts every argument of :class:`matplotlib.text.Text`; those
    set the default style of the text. The rich text options are given
    with *richtext*.

    Parameters
    ----------
    x, y :
        Position of the text.
    text :
        The string, with Markdown and/or HTML markup.
    richtext :
        ``True`` (default) for the default options, a
        :class:`RichTextSpec`, or a dict of :class:`RichTextSpec`
        options, e.g. ``{"width": 0.5, "fill": "lightyellow"}``.
    **kwargs :
        Any :class:`matplotlib.text.Text` properties.

    Examples
    --------
    >>> import matplotlib.pyplot as plt
    >>> from ggtext import RichText
    >>> fig, ax = plt.subplots()
    >>> t = RichText(0.5, 0.5, "Some **bold** and *italic* text",
    ...              ha="center", transform=ax.transAxes)
    >>> _ = ax.add_artist(t)
    """

    _richtext_spec: RichTextSpec | None
    _ggtext_reference: Callable[[Any], tuple[float, float]] | None = None

    def __init__(
        self,
        x: float = 0,
        y: float = 0,
        text: str = "",
        *,
        richtext: Any = True,
        **kwargs: Any,
    ):
        self._richtext_spec = RichTextSpec.coerce(richtext) or RichTextSpec()
        self._rich_cache: tuple | None = None
        super().__init__(x, y, text, **kwargs)

    def __repr__(self) -> str:
        return f"{type(self).__name__}{(self._x, self._y, self._text)!r}"

    # -- properties -------------------------------------------------------
    def set_richtext(self, richtext: Any):
        """
        Set the rich text options.

        Parameters
        ----------
        richtext : bool, dict or RichTextSpec
            ``True`` for the defaults, a dict of options or a
            :class:`RichTextSpec`. ``False``/``None`` turns the artist
            back into a plain :class:`~matplotlib.text.Text`.
        """
        spec = RichTextSpec.coerce(richtext)
        if spec is None:
            make_plain(self)
            return
        self._richtext_spec = spec
        self._rich_cache = None
        self.stale = True
        if _uses_relative_size(spec):
            _ensure_relayout(self.get_figure(root=True))

    def set_horizontalalignment(self, align):
        """
        Set the horizontal alignment.

        Besides matplotlib's ``"left"``, ``"center"`` and ``"right"``,
        rich text accepts a number in [0, 1] (ggplot2's ``hjust``): the
        fraction of the text's width that lies left of the anchor.
        """
        if _is_frac(align):
            self._horizontalalignment = float(align)
            self.stale = True
        else:
            super().set_horizontalalignment(align)

    def set_verticalalignment(self, align):
        """
        Set the vertical alignment.

        Besides matplotlib's named alignments, rich text accepts a number
        in [0, 1] (ggplot2's ``vjust``): 0 is the bottom, 1 the top.
        """
        if _is_frac(align):
            self._verticalalignment = float(align)
            self.stale = True
        else:
            super().set_verticalalignment(align)

    def get_richtext(self) -> RichTextSpec | None:
        """Return the :class:`RichTextSpec` of this artist."""
        return self._richtext_spec

    def get_plain_text(self) -> str:
        """The text with all markup removed."""
        spec = self._spec()
        return plain_text(
            parse(
                self.get_text(),
                Style(size=10.0),
                markdown=spec.markdown,
                html=spec.html,
                math=spec.math,
                newline=spec.newline,
            )
        )

    def update_from(self, other):
        # docstring inherited
        super().update_from(other)
        if isinstance(other, RichText):
            self._richtext_spec = other._richtext_spec
            self._rich_cache = None

    def _spec(self) -> RichTextSpec:
        spec = getattr(self, "_richtext_spec", None)
        if spec is None:
            spec = self._richtext_spec = RichTextSpec()
        return spec

    # -- layout -----------------------------------------------------------
    def _reference_size(self, renderer) -> tuple[float, float]:
        """
        The size (in pixels) that fractional widths/heights refer to.

        - text inside an axes: the axes,
        - figure-level text (e.g. plot titles): the *panel area*, i.e.
          the box around all axes of the figure (like ggtext's ``npc``
          units for titles); the figure if it has no axes.

        For rotated text (closer to vertical than horizontal) width and
        height are swapped, so a ``width`` always runs along the text.
        Integrations can refine the panel area by registering a function
        with :func:`register_panel_resolver` (the plotnine integration
        uses this so that, in a plot composition, a title refers to its
        own plot's panels), or override everything by setting
        ``_ggtext_reference`` to a callable.
        """
        if self._ggtext_reference is not None:
            w, h = self._ggtext_reference(renderer)
        else:
            if self.axes is not None:
                bbox = self.axes.bbox
            else:
                fig = self.get_figure(root=False) or self.get_figure(root=True)
                axes = None
                for resolver in _PANEL_RESOLVERS:
                    axes = resolver(self, fig)
                    if axes:
                        # remember: when saving, matplotlib may swap in a
                        # placeholder layout engine and the resolver can
                        # no longer tell which plot the text belongs to
                        self._ggtext_panels = axes
                        break
                if not axes:
                    cached = getattr(self, "_ggtext_panels", None) or []
                    axes = [a for a in cached if a in fig.axes]
                if not axes:
                    axes = [a for a in fig.axes if a.get_visible()]
                if axes:
                    bbox = Bbox.union([a.bbox for a in axes])
                else:
                    bbox = fig.bbox
            w, h = bbox.width, bbox.height
        angle = self.get_rotation() % 180
        if 45 < angle < 135:
            w, h = h, w
        return w, h

    def _rich_layout(self, renderer) -> Layout:
        spec = self._spec()
        fig = self.get_figure(root=True)
        dpi = fig.dpi if fig is not None else 72.0
        base = Style.from_fontproperties(self._fontproperties, color=None)

        needs_ref = _uses_relative_size(spec)
        if needs_ref:
            _ensure_relayout(fig)
            ref = self._reference_size(renderer)
        else:
            ref = (0.0, 0.0)
        wrap_mpl = self.get_wrap() and spec.width is None and spec.maxwidth is None
        halign = spec.halign or self._get_multialignment()
        if halign not in ("left", "center", "right"):
            halign = "left"

        key = (
            self.get_text(),
            base,
            spec,
            halign,
            self._linespacing,
            type(renderer),
            getattr(renderer, "dpi", None),
            dpi,
            ref,
            wrap_mpl and self._get_wrap_line_width(),
        )
        if self._rich_cache is not None and self._rich_cache[0] == key:
            return self._rich_cache[1]

        measurer = _Measurer(renderer, self)
        tokens = _parse_cached(
            self.get_text(), base, spec.markdown, spec.html, spec.math, spec.newline
        )
        padding = tuple(renderer.points_to_pixels(p) for p in spec.padding)
        margin = tuple(renderer.points_to_pixels(p) for p in spec.margin)
        _pt, pr, _pb, pl = padding

        def length(value, ref_px):
            return resolve_length(value, ref_px, dpi)

        width = length(spec.width, ref[0])
        minwidth = length(spec.minwidth, ref[0])
        maxwidth = length(spec.maxwidth, ref[0])
        if width is not None:
            # a fixed width, clamped to the limits (ggtext semantics)
            if minwidth is not None:
                width = max(width, minwidth)
            if maxwidth is not None:
                width = min(width, maxwidth)
            wrap_width: float | None = max(width - pl - pr, 1.0)
        elif maxwidth is not None:
            # shrink-to-fit, wrapping at maxwidth
            wrap_width = max(maxwidth - pl - pr, 1.0)
        elif wrap_mpl:
            wrap_width = self._get_wrap_line_width()
        else:
            wrap_width = None

        def run_layout(box_width, box_height):
            return layout_tokens(
                tokens,
                measurer,
                base,
                halign=halign,
                wrap_width=wrap_width,
                box_width=box_width,
                box_height=box_height,
                valign=spec.valign,
                padding=padding,  # type: ignore[arg-type]
                margin=margin,  # type: ignore[arg-type]
                linespacing=self._linespacing,
                line_model="mpl311" if MPL_311 else "mpl310",
            )

        layout = run_layout(width, length(spec.height, ref[1]))
        # Widen boxes of short text to minwidth, then apply the height limits
        box_w, box_h = layout.box[2], layout.box[3]
        new_w = minwidth if (minwidth is not None and box_w < minwidth) else width
        new_h = length(spec.height, ref[1])
        minheight = length(spec.minheight, ref[1])
        maxheight = length(spec.maxheight, ref[1])
        if minheight is not None and box_h < minheight:
            new_h = minheight
        if maxheight is not None and box_h > maxheight:
            new_h = maxheight
        if new_w != width or new_h != length(spec.height, ref[1]):
            layout = run_layout(new_w, new_h)
        self._rich_cache = (key, layout)
        return layout

    def _rich_geometry(self, renderer) -> _Geometry:
        """Rotate and align the layout like :meth:`Text._get_layout`."""
        L = self._rich_layout(renderer)
        W, H = L.width, L.height
        angle = self.get_rotation()

        # the corners of the unrotated box
        corners_horiz = [(0.0, -H), (0.0, 0.0), (W, 0.0), (W, -H)]
        corners_rotated = [_rotate(angle, x, y) for x, y in corners_horiz]
        xs, ys = zip(*corners_rotated, strict=True)
        xmin, xmax = min(xs), max(xs)
        ymin, ymax = min(ys), max(ys)
        width_rot, height_rot = xmax - xmin, ymax - ymin

        # distance from the top to the last baseline and from the last
        # baseline to the bottom (matplotlib aligns "baseline" to the
        # last line)
        if L.lines:
            baseline = -L.lines[-1].baseline
            descent = H - baseline
            if not MPL_311 and len(L.lines) > 1:
                # matplotlib < 3.11 computes the "baseline" of multi-line
                # text without the linespacing factor; match it so rich
                # and plain text align identically.
                ls = _numeric_linespacing(self._linespacing) or 1.0
                baseline -= (ls - 1) * L.lines[-1].ascent
        else:
            baseline, descent = H, 0.0

        halign = self._horizontalalignment
        valign = self._verticalalignment
        rotation_mode = self.get_rotation_mode()
        if rotation_mode != "anchor":
            if rotation_mode == "xtick" and hasattr(self, "_ha_for_angle"):
                halign = self._ha_for_angle(angle)
            elif rotation_mode == "ytick" and hasattr(self, "_va_for_angle"):
                valign = self._va_for_angle(angle)
            offsetx = (
                xmin + halign * (xmax - xmin) if _is_frac(halign)
                else xmin if halign == "left"
                else xmax if halign == "right"
                else (xmin + xmax) / 2
            )  # fmt: skip
            offsety = (
                ymin + valign * (ymax - ymin) if _is_frac(valign)
                else ymin if valign == "bottom"
                else ymax if valign == "top"
                else (ymin + ymax) / 2 if valign == "center"
                else ymin + descent if valign == "baseline"
                else ymin + height_rot - baseline / 2  # center_baseline
            )  # fmt: skip
        else:
            xmin1, ymin1 = corners_horiz[0]
            xmax1, ymax1 = corners_horiz[2]
            offsetx = (
                xmin1 + halign * (xmax1 - xmin1) if _is_frac(halign)
                else xmin1 if halign == "left"
                else xmax1 if halign == "right"
                else (xmin1 + xmax1) / 2
            )  # fmt: skip
            offsety = (
                ymin1 + valign * (ymax1 - ymin1) if _is_frac(valign)
                else ymin1 if valign == "bottom"
                else ymax1 if valign == "top"
                else (ymin1 + ymax1) / 2 if valign == "center"
                else ymax1 - baseline if valign == "baseline"
                else ymax1 - baseline / 2  # center_baseline
            )  # fmt: skip
            offsetx, offsety = _rotate(angle, offsetx, offsety)

        bbox = Bbox.from_bounds(xmin - offsetx, ymin - offsety, width_rot, height_rot)
        xys = []
        for line in L.lines:
            rx, ry = _rotate(angle, line.x, line.baseline)
            xys.append((rx - offsetx, ry - offsety))
        return _Geometry(L, angle, offsetx, offsety, bbox, xys)

    def _get_layout(self, renderer):
        # docstring inherited
        if self.get_usetex():
            return super()._get_layout(renderer)

        g = self._rich_geometry(renderer)
        L = g.layout
        if MPL_311:
            info = [
                (ln.text, (ln.width, ln.ascent, ln.descent), xy)
                for ln, xy in zip(L.lines, g.xys, strict=True)
            ]
            bx, by, bw, bh = L.box
            return g.bbox, info, (g.to_anchor(bx, by), (bw, bh))
        else:
            info = [
                (ln.text, (ln.width, ln.ascent + ln.descent), x, y)
                for ln, (x, y) in zip(L.lines, g.xys, strict=True)
            ]
            return g.bbox, info, L.descent

    # -- drawing ----------------------------------------------------------
    @artist.allow_rasterization
    def draw(self, renderer):
        # docstring inherited
        if renderer is not None:
            self._renderer = renderer
        if not self.get_visible():
            return
        if self.get_text() == "":
            return
        if self.get_usetex():
            warnings.warn(
                "ggtext: rich text is not supported with usetex=True; "
                "drawing it as plain text.",
                UserWarning,
                stacklevel=2,
            )
            return super().draw(renderer)

        posx, posy = self._display_position()
        if posx is None:
            return

        renderer.open_group("text", self.get_gid())
        g = self._rich_geometry(renderer)

        # Background of the whole text (Text.set_backgroundcolor/set_bbox)
        if self._bbox_patch:
            self.update_bbox_position_size(renderer)
            self._bbox_patch.draw(renderer)

        # The rich text box
        spec = self._spec()
        if spec.has_box:
            self._draw_box(renderer, g, posx, posy)

        self._draw_fragments(renderer, g, posx, posy)
        renderer.close_group("text")
        self.stale = False

    def _display_position(self) -> tuple[float | None, float | None]:
        x, y = self._x, self._y
        if np.ma.is_masked(x):
            x = np.nan
        if np.ma.is_masked(y):
            y = np.nan
        posx = float(self.convert_xunits(x))
        posy = float(self.convert_yunits(y))
        posx, posy = self.get_transform().transform((posx, posy))
        if not (np.isfinite(posx) and np.isfinite(posy)):
            return None, None
        return posx, posy

    def _draw_box(self, renderer, g: _Geometry, posx: float, posy: float):
        spec = self._spec()
        bx, by, bw, bh = g.layout.box
        r = renderer.points_to_pixels(spec.r)
        r = min(r, bw / 2, bh / 2)
        boxstyle = f"round,pad=0,rounding_size={r}" if r > 0 else "square,pad=0"
        alpha = self.get_alpha()
        patch = FancyBboxPatch(
            (bx, by),
            bw,
            bh,
            boxstyle=boxstyle,
            mutation_scale=1,
            facecolor=_with_alpha(spec.fill, alpha)
            if spec.fill is not None
            else "none",
            edgecolor=(
                _with_alpha(spec.box_color, alpha)
                if spec.box_color is not None
                else "none"
            ),
            linewidth=spec.linewidth if spec.box_color is not None else 0,
            linestyle=spec.linestyle,
            transform=Affine2D()
            .rotate_deg(g.angle)
            .translate(posx - g.offsetx, posy - g.offsety),
        )
        patch.set_figure(self.get_figure(root=False))
        patch.update(
            {
                "clip_box": self.clipbox,
                "clip_path": self._clippath,
                "clip_on": self._clipon,
            }
        )
        patch.draw(renderer)

    def _new_gc(self, renderer, color, url=None):
        gc = renderer.new_gc()
        gc.set_foreground(to_rgba(color), isRGBA=True)
        gc.set_alpha(self.get_alpha())
        gc.set_url(url if url is not None else self._url)
        gc.set_antialiased(self._antialiased)
        gc.set_snap(self.get_snap())
        self._set_gc_clip(gc)
        return gc

    def _draw_fragments(self, renderer, g: _Geometry, posx: float, posy: float):
        base_color = self.get_color()
        angle = g.angle
        canvash = renderer.get_canvas_width_height()[1]

        if self.get_path_effects():
            from matplotlib.patheffects import PathEffectRenderer

            textrenderer = PathEffectRenderer(self.get_path_effects(), renderer)
        else:
            textrenderer = renderer

        measurer = _Measurer(renderer, self)
        to_display = (
            Affine2D().rotate_deg(angle).translate(posx - g.offsetx, posy - g.offsety)
        )

        for line in g.layout.lines:
            for frag in line.fragments:
                run = frag.run
                style = run.style
                color = style.color if style.color is not None else base_color
                x0 = line.x + frag.x
                yb = line.baseline + frag.shift

                if isinstance(run, ImageRun):
                    self._draw_image(renderer, run, frag, x0, yb, to_display)
                    continue

                size_px = renderer.points_to_pixels(style.size or self.get_fontsize())
                if style.background is not None:
                    a, d, _ = measurer.font_metrics(style)
                    self._draw_rect(
                        renderer, to_display, x0, yb - d, frag.width, a + d,
                        style.background,
                    )  # fmt: skip

                if run.text.strip():
                    gc = self._new_gc(renderer, color, style.url)
                    x, y = to_display.transform((x0, yb))
                    if renderer.flipy():
                        y = canvash - y
                    textrenderer.draw_text(
                        gc,
                        x,
                        y,
                        run.text,
                        measurer.fontproperties(style),
                        angle,
                        ismath=run.math,
                        mtext=None,
                    )
                    gc.restore()

                thickness = max(DECORATION_THICKNESS * size_px, 0.5)
                if style.underline:
                    self._draw_rect(
                        renderer, to_display, x0,
                        yb - UNDERLINE_OFFSET * size_px - thickness / 2,
                        frag.width, thickness, color,
                    )  # fmt: skip
                if style.strike:
                    self._draw_rect(
                        renderer, to_display, x0,
                        yb + STRIKE_OFFSET * size_px - thickness / 2,
                        frag.width, thickness, color,
                    )  # fmt: skip

    def _draw_rect(self, renderer, transform, x, y, w, h, color):
        """Fill a rectangle given in box coordinates."""
        if w <= 0 or h <= 0:
            return
        path = Path(
            [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)],
            [Path.MOVETO, Path.LINETO, Path.LINETO, Path.LINETO, Path.CLOSEPOLY],
        )
        rgba = to_rgba(color)
        gc = self._new_gc(renderer, rgba)
        gc.set_linewidth(0)
        alpha = self.get_alpha()
        face = rgba if alpha is None else (*rgba[:3], rgba[3] * alpha)
        renderer.draw_path(gc, path, transform, face)
        gc.restore()

    def _draw_image(self, renderer, run, frag: Fragment, x0, yb, to_display):
        arr = load_image(run.src)
        if arr is None or frag.width <= 0:
            return
        from matplotlib.image import BboxImage

        angle = self.get_rotation() % 360
        # Images can only be rotated by multiples of 90 degrees
        quarter = round(angle / 90) % 4
        if not math.isclose(angle, quarter * 90, abs_tol=0.5):
            _warn_once("ggtext: images in text rotated by angles that are not "
                       "multiples of 90 degrees are drawn upright.")  # fmt: skip
        data = np.rot90(arr, k=quarter) if quarter else arr

        # The image sits on the (possibly shifted) baseline
        h = frag.ascent + frag.descent
        corners = [
            to_display.transform((x0, yb)),
            to_display.transform((x0 + frag.width, yb)),
            to_display.transform((x0 + frag.width, yb + h)),
            to_display.transform((x0, yb + h)),
        ]
        xs = [c[0] for c in corners]
        ys = [c[1] for c in corners]
        bbox = Bbox.from_extents(min(xs), min(ys), max(xs), max(ys))
        im = BboxImage(bbox, interpolation="antialiased", resample=True)
        im.set_data(data)
        im.set_figure(self.get_figure(root=False))
        im.set_alpha(self.get_alpha())
        im.update(
            {
                "clip_box": self.clipbox,
                "clip_path": self._clippath,
                "clip_on": self._clipon,
            }
        )
        im.draw(renderer)


def _is_frac(value: Any) -> bool:
    """Whether an alignment is a number (ggplot2-style justification)."""
    return isinstance(value, (int, float, np.number)) and not isinstance(value, bool)


def _uses_relative_size(spec: RichTextSpec) -> bool:
    """Whether *spec* has a width/height relative to the axes or figure."""
    return any(
        isinstance(v, float)
        or (isinstance(v, str) and v.strip().lower().endswith(("%", "npc")))
        for v in (getattr(spec, name) for name in LENGTH_FIELDS)
    )


def _ensure_relayout(fig) -> None:
    """
    Make the layout engine of *fig* run twice per draw.

    Layout engines (plotnine's, matplotlib's tight layout) measure the
    texts *before* they move the axes. A text box whose width is a
    fraction of the panel area wraps differently once the panels have
    moved, so its height can change. Running the engine a second time
    measures the text against the settled panel positions. (matplotlib's
    constrained layout already iterates internally, for the same reason.)

    Only figures that contain such relative-width rich text are touched,
    and only the engine instance of that figure is wrapped.
    """
    if fig is None or getattr(fig, "_ggtext_relayout", False):
        return
    fig._ggtext_relayout = True
    # Wrap the method on this figure instance only. Small classes instead
    # of closures keep the figure picklable.
    fig.set_layout_engine = _RelayoutSetter(fig, fig.set_layout_engine)
    _wrap_engine(fig.get_layout_engine())


class _ExecuteTwice:
    """``LayoutEngine.execute`` that runs the layout twice."""

    def __init__(self, execute):
        self.execute = execute

    def __call__(self, figure):
        self.execute(figure)
        self.execute(figure)


class _RelayoutSetter:
    """``Figure.set_layout_engine`` that wraps the new engine."""

    def __init__(self, fig, original):
        self.fig = fig
        self.original = original

    def __call__(self, *args, **kwargs):
        result = self.original(*args, **kwargs)
        _wrap_engine(self.fig.get_layout_engine())
        return result


def _wrap_engine(engine) -> None:
    if engine is None or isinstance(engine.__dict__.get("execute"), _ExecuteTwice):
        return
    engine.execute = _ExecuteTwice(engine.execute)


def _numeric_linespacing(ls: Any) -> float | None:
    try:
        return float(ls)
    except (TypeError, ValueError):
        return None


def _with_alpha(color, alpha):
    rgba = to_rgba(color)
    if alpha is None:
        return rgba
    return (*rgba[:3], rgba[3] * alpha)


def _warn_once(msg: str, _seen: set = set()):  # noqa: B006
    if msg not in _seen:
        _seen.add(msg)
        warnings.warn(msg, UserWarning, stacklevel=3)


@lru_cache(maxsize=2048)
def _parse_cached(text, base, markdown, html, math_, newline):
    return tuple(
        parse(text, base, markdown=markdown, html=html, math=math_, newline=newline)
    )


# -----------------------------------------------------------------------
# Converting existing Text artists
# -----------------------------------------------------------------------
_RICH_CLASSES: dict[type, type] = {}


def _rich_class_for(cls: type[Text]) -> type[RichText]:
    """
    The rich version of a Text (sub)class.

    For a subclass ``B`` of ``Text`` this creates ``RichB(B, RichText)``
    so that ``B``'s own behaviour (e.g. plotnine's strip text
    positioning) is kept, and its call to ``super().draw()`` reaches
    :meth:`RichText.draw`.
    """
    if issubclass(cls, RichText):
        return cls
    if cls is Text:
        return RichText
    rich = _RICH_CLASSES.get(cls)
    if rich is None:
        from matplotlib.text import Annotation

        name = f"Rich{cls.__name__}"
        namespace: dict[str, Any] = {"__module__": __name__}
        if issubclass(cls, Annotation):
            # Annotation.draw calls Text.draw(self, ...) explicitly,
            # which would skip RichText.draw
            namespace["draw"] = _annotation_draw
        rich = type(name, (cls, RichText), namespace)
        # Make the dynamic class picklable by giving it a unique,
        # importable name in this module
        qualname = f"_{name}_{id(cls):x}"
        rich.__qualname__ = qualname
        globals()[qualname] = rich
        _RICH_CLASSES[cls] = rich
    return rich


@artist.allow_rasterization
def _annotation_draw(self, renderer):
    """``Annotation.draw`` that draws the text with :meth:`RichText.draw`."""
    if renderer is not None:
        self._renderer = renderer
    if not self.get_visible() or not self._check_xy(renderer):
        return
    self.update_positions(renderer)
    self.update_bbox_position_size(renderer)
    if self.arrow_patch is not None:
        if (
            self.arrow_patch.get_figure(root=False) is None
            and (fig := self.get_figure(root=False)) is not None
        ):
            self.arrow_patch.set_figure(fig)
        self.arrow_patch.draw(renderer)
    RichText.draw(self, renderer)


def make_rich(text: Text, richtext: Any = True) -> Text:
    """
    Turn an existing matplotlib ``Text`` into rich text, in place.

    Parameters
    ----------
    text :
        Any matplotlib text artist, e.g. ``ax.title``,
        ``ax.xaxis.label`` or a tick label.
    richtext :
        ``True`` for the default options, a dict of
        :class:`RichTextSpec` options, or a spec.

    Returns
    -------
    Text
        The same object, which is now also a :class:`RichText`.
    """
    spec = RichTextSpec.coerce(richtext) or RichTextSpec()
    if not isinstance(text, RichText):
        text._ggtext_original_class = text.__class__  # type: ignore[attr-defined]
        text.__class__ = _rich_class_for(type(text))
        text._rich_cache = None  # type: ignore[attr-defined]
    text._richtext_spec = spec  # type: ignore[attr-defined]
    text._rich_cache = None  # type: ignore[attr-defined]
    text.stale = True
    if _uses_relative_size(spec):
        _ensure_relayout(text.get_figure(root=True))
    return text


def make_plain(text: Text) -> Text:
    """Undo :func:`make_rich`: draw *text* as a plain matplotlib Text."""
    original = getattr(text, "_ggtext_original_class", None)
    if original is not None:
        text.__class__ = original
        del text._ggtext_original_class  # type: ignore[attr-defined]
    elif type(text) is RichText:
        text.__class__ = Text
    text.stale = True
    return text


def is_rich(text: Any) -> bool:
    """Whether *text* is drawn as rich text."""
    return isinstance(text, RichText)


# -----------------------------------------------------------------------
# The ``richtext`` property on every Text
# -----------------------------------------------------------------------
def _text_set_richtext(self: Text, richtext: Any):
    """
    Render this text as rich text (Markdown/HTML), see ggtext.

    Parameters
    ----------
    richtext : bool, dict or ggtext.RichTextSpec
        ``True`` for the defaults or a dict/spec of rich text options.
        ``False``/``None`` leaves the text plain.
    """
    if RichTextSpec.coerce(richtext) is not None:
        make_rich(self, richtext)


def _text_get_richtext(self: Text) -> None:
    """Return the rich text options (None for plain text)."""
    return


def install_text_property() -> None:
    """
    Register ``richtext`` as a property of :class:`matplotlib.text.Text`.

    After this, ``text.set(richtext=True)`` and
    ``Text(..., richtext=True)`` work on any text artist. This only *adds*
    a property; existing behaviour of ``Text`` is unchanged. It is called
    when ggtext is imported.
    """
    if getattr(Text, "set_richtext", None) is not _text_set_richtext:
        Text.set_richtext = _text_set_richtext  # type: ignore[attr-defined]
        Text.get_richtext = _text_get_richtext  # type: ignore[attr-defined]


install_text_property()
