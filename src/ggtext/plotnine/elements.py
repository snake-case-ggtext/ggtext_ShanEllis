"""
Theme elements that render plotnine text as Markdown/HTML.

These are drop-in replacements for :class:`plotnine.element_text`::

    theme(plot_title=element_markdown())
    theme(axis_text_x=element_markdown(color="gray"))
    theme(plot_subtitle=element_textbox_simple(padding=5, fill="#eee"))

How it works
------------
Every plotnine themeable styles its text artists with
``text.set(**element.properties)``. These elements add one extra
property, ``richtext``, holding a :class:`ggtext.RichTextSpec`. ggtext
registers ``richtext`` as a matplotlib ``Text`` property, so when
plotnine applies the theme the artist turns itself into a
:class:`ggtext.RichText`. plotnine's layout engine then measures the
rich text like any other text, so titles, axis labels, tick labels,
facet strips and legends all get the right amount of space.
"""

from __future__ import annotations

from typing import Any, Literal

from plotnine.themes.elements import element_text

from .._spec import Length, RichTextSpec, _normalize_kwargs

__all__ = ["element_markdown", "element_textbox", "element_textbox_simple"]

Orientation = Literal["upright", "left-rotated", "right-rotated", "inverted"]

_ORIENTATION_ANGLES = {
    "upright": 0,
    "left-rotated": 90,
    "right-rotated": 270,
    "inverted": 180,
}

# R/ggplot2 spellings accepted for compatibility with ggtext code
_GG_SPEC_ALIASES = {
    "box_colour": "box_color",
    "box.colour": "box_color",
    "box.color": "box_color",
    "linetype": "linestyle",
}


def _as_halign(value: Any) -> str | None:
    """Accept ggplot2-style numeric alignment (0, 0.5, 1) too."""
    if value is None or isinstance(value, str):
        return value
    v = float(value)
    return "left" if v < 1 / 3 else "right" if v > 2 / 3 else "center"


def _as_valign(value: Any) -> str | None:
    if value is None or isinstance(value, str):
        return value
    v = float(value)
    return "bottom" if v < 1 / 3 else "top" if v > 2 / 3 else "center"


class element_markdown(element_text):
    """
    Theme element: text with Markdown, HTML and CSS.

    A drop-in replacement for :class:`plotnine.element_text`. It works
    for every text themeable: ``plot_title``, ``plot_subtitle``,
    ``plot_caption``, ``plot_tag``, ``axis_title(_x/_y)``,
    ``axis_text(_x/_y)``, ``strip_text(_x/_y)``, ``legend_title``,
    ``legend_text`` and ``text``. The text is not word-wrapped; use
    :class:`element_textbox` for that.

    Parameters
    ----------
    fill :
        Background color of a box around the text.
    box_color :
        Outline color of the box (ggtext: ``box.colour``).
    linewidth :
        Width of the box outline, in points.
    linestyle :
        Line style of the box outline (ggtext: ``linetype``).
    r :
        Corner radius of the box, in points.
    padding :
        Space between the text and the box edge, in points. A number,
        ``(vertical, horizontal)``, ``(t, r, b, l)`` or a dict with keys
        ``t``, ``r``, ``b``, ``l``.
    halign :
        Alignment of the lines of multi-line text: ``"left"``,
        ``"center"``, ``"right"`` (or 0, 0.5, 1). Defaults to ``ma``.
    markdown :
        Interpret Markdown. If False, only HTML tags are interpreted.
    newline :
        ``"break"`` (default) makes ``"\\n"`` a line break, ``"space"``
        treats it as a space as in Markdown (then use ``<br>``).
    math :
        Render ``$...$`` with matplotlib's mathtext.
    **kwargs :
        All :class:`plotnine.element_text` parameters (``color``,
        ``size``, ``family``, ``weight``, ``style``, ``ha``, ``va``,
        ``rotation``, ``margin``, ...) and their ggplot2 spellings
        (``colour``, ``face``, ``hjust``, ``vjust``, ``angle``,
        ``lineheight``).

    Examples
    --------
    >>> from plotnine import theme
    >>> theme(plot_title=element_markdown(size=14))  # doctest: +SKIP
    >>> theme(axis_text_x=element_markdown(rotation=45, ha="right"))  # doctest: +SKIP
    """

    _spec_defaults: dict = {}

    def __init__(
        self,
        *,
        fill: Any = None,
        box_color: Any = None,
        linewidth: float | None = None,
        linestyle: Any = None,
        r: float | None = None,
        padding: Any = None,
        halign: Any = None,
        markdown: bool = True,
        newline: Literal["break", "space"] = "break",
        math: bool = True,
        **kwargs: Any,
    ):
        aliases = self._pop_spec_aliases(kwargs)
        spec_kwargs = dict(
            fill=fill,
            box_color=box_color,
            linewidth=linewidth,
            linestyle=linestyle,
            r=r,
            padding=padding,
            halign=_as_halign(halign),
            markdown=markdown,
            newline=newline,
            math=math,
        )
        self._init(spec_kwargs, kwargs, aliases)

    # -- helpers ----------------------------------------------------------
    @staticmethod
    def _pop_spec_aliases(kwargs: dict) -> dict:
        out = {}
        for alias, name in _GG_SPEC_ALIASES.items():
            if alias in kwargs:
                out[name] = kwargs.pop(alias)
        if "color" not in kwargs and "colour" in kwargs:
            kwargs["color"] = kwargs.pop("colour")
        return out

    def _init(self, spec_kwargs: dict, text_kwargs: dict, aliases: dict):
        # Drop unset options so the spec defaults (and _spec_defaults of
        # subclasses) apply. ggplot2-style aliases fill in options that
        # were not given under their Python name.
        values = dict(self._spec_defaults)
        values.update({k: v for k, v in aliases.items() if v is not None})
        values.update({k: v for k, v in spec_kwargs.items() if v is not None})
        super().__init__(**text_kwargs)
        self.properties["richtext"] = RichTextSpec(**_normalize_kwargs(values))

    @property
    def spec(self) -> RichTextSpec:
        """The :class:`ggtext.RichTextSpec` of this element."""
        return self.properties["richtext"]


class element_textbox(element_markdown):
    """
    Theme element: word-wrapped Markdown text in a box.

    Use it for long titles, subtitles and captions that should wrap to
    the width of the plot. Unlike ggtext, the box may be rotated to any
    angle with ``rotation``; ``orientation`` gives the ggtext names for
    the common angles.

    Most of the time you want :class:`element_textbox_simple`, which
    sets sensible defaults (full width, no box).

    Parameters
    ----------
    width :
        Width of the box. A float in (0, 1] is a fraction of the panel
        area (for plot titles, subtitles, captions and axis titles); a
        string may give units (``"4in"``, ``"300pt"``, ``"10cm"``,
        ``"80%"``). ``None`` sizes the box to the text.
    height :
        Height of the box, same units as *width* (fractions are of the
        panel area). Text that does not fit overflows, as in ggtext.
        ``None`` fits the box to the text.
    minwidth, maxwidth :
        Limits for the width. With a *width* they clamp it (ggtext).
        With ``width=None``, *maxwidth* gives a shrink-to-fit box: short
        text gets a tight box, long text wraps at *maxwidth*.
    minheight, maxheight :
        Limits for the height of the box.
    valign :
        Vertical alignment of the text in a box taller than the text:
        ``"top"``, ``"center"``, ``"bottom"`` (or 1, 0.5, 0).
    orientation :
        ``"upright"``, ``"left-rotated"`` (90°), ``"right-rotated"``
        (270°) or ``"inverted"`` (180°). Overrides ``rotation``.
    fill, box_color, linewidth, linestyle, r, padding, halign, markdown, newline, math :
        See :class:`element_markdown`.
    **kwargs :
        :class:`plotnine.element_text` parameters.
    """

    def __init__(
        self,
        *,
        width: Length = None,
        height: Length = None,
        minwidth: Length = None,
        maxwidth: Length = None,
        minheight: Length = None,
        maxheight: Length = None,
        valign: Any = None,
        orientation: Orientation | None = None,
        fill: Any = None,
        box_color: Any = None,
        linewidth: float | None = None,
        linestyle: Any = None,
        r: float | None = None,
        padding: Any = None,
        halign: Any = None,
        markdown: bool = True,
        newline: Literal["break", "space"] = "break",
        math: bool = True,
        **kwargs: Any,
    ):
        aliases = self._pop_spec_aliases(kwargs)
        if orientation is not None:
            try:
                kwargs["rotation"] = _ORIENTATION_ANGLES[orientation]
            except KeyError as err:
                raise ValueError(
                    f"orientation must be one of {sorted(_ORIENTATION_ANGLES)}, "
                    f"not {orientation!r}"
                ) from err
            kwargs.pop("angle", None)
        spec_kwargs = dict(
            width=width,
            height=height,
            minwidth=minwidth,
            maxwidth=maxwidth,
            minheight=minheight,
            maxheight=maxheight,
            valign=_as_valign(valign),
            fill=fill,
            box_color=box_color,
            linewidth=linewidth,
            linestyle=linestyle,
            r=r,
            padding=padding,
            halign=_as_halign(halign),
            markdown=markdown,
            newline=newline,
            math=math,
        )
        self._init(spec_kwargs, kwargs, aliases)


class element_textbox_simple(element_textbox):
    """
    Theme element: :class:`element_textbox` with sensible defaults.

    The box spans the full width of the panel area (``width=1``), has
    no background or outline, and the text is left aligned within it.
    This is the element to use for long, wrapping subtitles::

        theme(plot_subtitle=element_textbox_simple(size=10, lineheight=1.3))

    All parameters of :class:`element_textbox` can be overridden.
    """

    _spec_defaults = {"width": 1.0, "halign": "left", "valign": "top"}

    def __init__(self, **kwargs: Any):
        # ggtext's element_textbox_simple uses lineheight = 1.2
        if "linespacing" not in kwargs and "lineheight" not in kwargs:
            kwargs["linespacing"] = 1.2
        super().__init__(**kwargs)
