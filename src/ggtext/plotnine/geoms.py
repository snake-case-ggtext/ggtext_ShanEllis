"""
Geoms that draw rich text labels in plotnine plots.

- :class:`geom_richtext`: Markdown/HTML labels, optionally in a box, at
  any angle (ggtext's ``geom_richtext``).
- :class:`geom_textbox`: word-wrapped Markdown/HTML in boxes of a fixed
  width (ggtext's ``geom_textbox``).

Both follow ggtext's conventions where they differ from plotnine's
``geom_text``/``geom_label``:

- labels are rotated around their anchor point (``rotation_mode="anchor"``),
  so ``ha``/``va`` keep their meaning along the rotated text;
- ``ha``/``va`` (alias ``hjust``/``vjust``) accept names, numbers in
  [0, 1] and ggplot2's ``"inward"``/``"outward"``;
- the outline color and width and the text color are aesthetics, so they
  can be mapped to data.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
from plotnine._utils import to_rgba
from plotnine.exceptions import PlotnineError
from plotnine.geoms.geom_text import geom_text

from .._artist import RichText
from .._spec import RichTextSpec
from .elements import _ORIENTATION_ANGLES, _as_halign, _as_valign

try:  # plotnine's docstring templating; optional
    from plotnine.doctools import document
except ImportError:  # pragma: no cover

    def document(cls):  # type: ignore[no-redef]
        return cls


if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from plotnine.coords.coord import coord
    from plotnine.iapi import panel_view

__all__ = ["geom_richtext", "geom_textbox"]

# ggplot2/ggtext spellings accepted as aesthetics and parameters
_AES_ALIASES = {
    "hjust": "ha",
    "vjust": "va",
    "label_colour": "label_color",
    "box_colour": "box_color",
    "text_colour": "text_color",
}

_HA_NAMES = {"left": 0.0, "center": 0.5, "centre": 0.5, "middle": 0.5, "right": 1.0}
_VA_NAMES = {"bottom": 0.0, "center": 0.5, "centre": 0.5, "middle": 0.5, "top": 1.0}
_VA_PASSTHROUGH = {"baseline", "center_baseline"}


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.lower() in ("none", "na", "")
    try:
        return bool(np.isnan(value))
    except (TypeError, ValueError):
        return False


def _rgba_or_none(value: Any, alpha: Any):
    if _is_missing(value):
        return None
    return to_rgba(value, alpha)


def _to_npc(values: pd.Series, rng: Any) -> np.ndarray:
    lo, hi = rng
    v = np.asarray(values, dtype=float)
    if hi == lo:
        return np.full(len(v), 0.5)
    return (v - lo) / (hi - lo)


def resolve_just(value: Any, npc: float, axis: str) -> Any:
    """
    Resolve a justification value for one label.

    Parameters
    ----------
    value :
        A name (``"left"``, ``"center"``, ``"right"``, ``"bottom"``,
        ``"top"``, ``"middle"``, and for ``va`` also ``"baseline"`` and
        ``"center_baseline"``), a number in [0, 1], or ``"inward"`` /
        ``"outward"`` (ggplot2): justify towards / away from the center
        of the panel.
    npc :
        Position of the label in the panel, 0 to 1 (for inward/outward).
    axis :
        ``"x"`` for ``ha``, ``"y"`` for ``va``.

    Returns
    -------
    str or float
        A matplotlib alignment name, or a number in [0, 1].
    """
    names = _HA_NAMES if axis == "x" else _VA_NAMES
    lo, hi = ("left", "right") if axis == "x" else ("bottom", "top")
    if isinstance(value, str):
        v = value.lower()
        if v in ("inward", "outward"):
            tol = 1e-3
            if abs(npc - 0.5) <= tol:
                return "center"
            low_side = npc < 0.5
            if v == "inward":
                return lo if low_side else hi
            return hi if low_side else lo
        if axis == "y" and v in _VA_PASSTHROUGH:
            return v
        if v not in names:
            raise PlotnineError(f"Unknown justification {value!r}")
        v = names[v]
    else:
        v = float(value)
    # Prefer matplotlib names for the usual values
    if v == 0.0:
        return lo
    if v == 1.0:
        return hi
    if v == 0.5:
        return "center"
    return v


def _halign_from_just(just: Any) -> str:
    """gridtext aligns the lines of a label like the label itself."""
    if isinstance(just, str):
        return {"left": "left", "right": "right"}.get(just, "center")
    return _as_halign(just) or "center"


_richtext_aes = geom_text.DEFAULT_AES.copy()
_richtext_aes.update(
    {
        "fill": "white",
        "label_color": None,
        "label_size": 0.7,
        "text_color": None,
    }
)

_richtext_params = geom_text.DEFAULT_PARAMS.copy()
_richtext_params.update(
    {
        "label_padding": 3.3,
        "label_margin": 0,
        "label_r": 2.0,
        "halign": None,
        "rotation_mode": "anchor",
        "markdown": True,
        "newline": "break",
    }
)
_richtext_params.pop("parse", None)


class _RichGeomMixin:
    """Shared behaviour of the rich text geoms."""

    def __init__(self, mapping=None, data=None, **kwargs: Any):
        from plotnine._utils import order_as_data_mapping

        data, mapping = order_as_data_mapping(data, mapping)
        if mapping is not None:
            for alias, name in _AES_ALIASES.items():
                if alias in mapping:
                    mapping[name] = mapping.pop(alias)
        for alias, name in _AES_ALIASES.items():
            if alias in kwargs:
                kwargs[name] = kwargs.pop(alias)
        super().__init__(mapping, data, **kwargs)  # type: ignore[call-arg]

    def setup_data(self, data: pd.DataFrame) -> pd.DataFrame:
        # ggplot2 names mapped at the plot level, e.g. ggplot(aes(hjust=...))
        for alias, name in _AES_ALIASES.items():
            if alias in data.columns and name not in data.columns:
                data = data.rename(columns={alias: name})
        fmt = self.params.get("format_string")  # type: ignore[attr-defined]
        if fmt:
            data["label"] = [
                None if _is_missing(v) else fmt.format(v) for v in data["label"]
            ]
        return data

    @staticmethod
    def _outline(row: pd.Series, color_col: str, size_col: str, text_color):
        """Outline color and width: None inherits the text color."""
        lw = row.get(size_col, 0)
        lw = 0.0 if _is_missing(lw) else float(lw)
        edge = row.get(color_col)
        if lw <= 0:
            return None, 0.0
        if edge is None or (isinstance(edge, float) and np.isnan(edge)):
            return text_color, lw
        if _is_missing(edge):  # "none"/"NA": explicitly no outline
            return None, 0.0
        return to_rgba(edge, row.get("alpha")), lw

    @staticmethod
    def _text_color(row: pd.Series):
        color = row.get("text_color")
        if _is_missing(color):
            color = row["color"]
        return to_rgba(color, row.get("alpha", 1))

    @staticmethod
    def _text_kwargs(row: pd.Series, color, ha, va, params: dict) -> dict:
        kw = {
            "color": color,
            "size": row["size"],
            "rotation": row.get("angle", 0),
            "rotation_mode": params.get("rotation_mode", "anchor"),
            "linespacing": row.get("lineheight", 1.2),
            "ha": ha,
            "va": va,
            "fontweight": row.get("fontweight", "normal"),
            "fontstyle": row.get("fontstyle", "normal"),
            "zorder": params["zorder"],
            "rasterized": params.get("raster", False),
            "clip_on": True,
        }
        if not _is_missing(row.get("family")):
            kw["family"] = row["family"]
        if not _is_missing(row.get("fontvariant")):
            kw["fontvariant"] = row["fontvariant"]
        return kw

    @classmethod
    def _make_artists(
        cls, data: pd.DataFrame, panel_params, ax: Axes, params: dict
    ) -> list:
        x_npc = _to_npc(data["x"], panel_params.x.range)
        y_npc = _to_npc(data["y"], panel_params.y.range)
        texts = []
        for i, (_, row) in enumerate(data.iterrows()):
            label = row["label"]
            if _is_missing(label):
                continue
            ha = resolve_just(row.get("ha", "center"), x_npc[i], "x")
            va = resolve_just(row.get("va", "center"), y_npc[i], "y")
            color = cls._text_color(row)
            spec = cls._spec_for_row(row, params, color, ha)  # type: ignore[attr-defined]
            kw = cls._text_kwargs(row, color, ha, va, params)
            t = RichText(row["x"], row["y"], str(label), richtext=spec, **kw)
            t.set_transform(ax.transData)
            if params.get("path_effects"):
                t.set_path_effects(params["path_effects"])
            ax.add_artist(t)
            t.set_clip_path(ax.patch)
            texts.append(t)
        return texts


@document
class geom_richtext(_RichGeomMixin, geom_text):  # type: ignore[misc]
    """
    Rich text labels (Markdown, HTML and CSS)

    {usage}

    Labels may contain Markdown (``**bold**``, ``*italic*``), HTML
    (``<span style='color:red'>``, ``<sup>``, ``<br>``, ...) and
    mathtext (``$\\alpha$``). Unlike [](`~plotnine.geom_label`), labels
    with a box can be rotated to any angle.

    Following ggtext, labels rotate around their anchor point, and
    ``ha``/``va`` (or ``hjust``/``vjust``) accept names, numbers in
    [0, 1] and ``"inward"``/``"outward"``.

    Parameters
    ----------
    {common_parameters}
    label_padding : float, default=3.3
        Padding between the text and the edge of the box, in points.
        Also accepts ``(vertical, horizontal)`` or
        ``(top, right, bottom, left)``.
    label_margin : float, default=0
        Space outside the box, in points (same forms as
        ``label_padding``). Moves the box away from the anchor point.
    label_r : float, default=2.0
        Radius of the rounded corners of the box, in points.
    halign : str, default=None
        Alignment of the lines of multi-line labels: ``"left"``,
        ``"center"`` or ``"right"``. ``None`` follows ``ha``, as in
        ggtext.
    rotation_mode : str, default="anchor"
        ``"anchor"`` (ggtext) rotates the label around its anchor point.
        ``"default"`` (plotnine's ``geom_text``) rotates first and then
        aligns the rotated bounding box.
    markdown : bool, default=True
        Interpret Markdown. If False, only HTML is interpreted.
    newline : str, default="break"
        ``"break"`` makes ``"\\n"`` a line break; ``"space"`` treats it
        as a space (as in Markdown).
    nudge_x : float, default=0
        Horizontal adjustment to apply to the text.
    nudge_y : float, default=0
        Vertical adjustment to apply to the text.
    format_string : str, default=None
        If not None, labels are formatted with this string using
        [](`str.format`).
    path_effects : list, default=None
        matplotlib path effects applied to the text.

    Notes
    -----
    Besides the usual text aesthetics, ``label_color`` (outline color;
    None uses the text color, ``"none"`` draws no outline),
    ``label_size`` (outline width in points; 0 for none) and
    ``text_color`` (overrides ``color`` for the text only) can be mapped
    to data. Set ``fill=None`` and ``label_size=0`` for labels without a
    box (ggtext: ``fill = NA, label.colour = NA``).

    See Also
    --------
    plotnine.geom_text
    plotnine.geom_label
    ggtext.geom_textbox
    """

    DEFAULT_AES = _richtext_aes
    DEFAULT_PARAMS = _richtext_params

    @staticmethod
    def _spec_for_row(row: pd.Series, params: dict, text_color, ha) -> RichTextSpec:
        fill = _rgba_or_none(row.get("fill"), row.get("alpha"))
        edge, lw = _RichGeomMixin._outline(row, "label_color", "label_size", text_color)
        halign = params.get("halign")
        halign = _as_halign(halign) if halign is not None else _halign_from_just(ha)
        return RichTextSpec(
            markdown=params.get("markdown", True),
            newline=params.get("newline", "break"),
            halign=halign,
            fill=fill,
            box_color=edge,
            linewidth=lw,
            r=params.get("label_r", 0) or 0,
            padding=params.get("label_padding", 0) or 0,
            margin=params.get("label_margin", 0) or 0,
        )

    @staticmethod
    def draw_group(
        data: pd.DataFrame,
        panel_params: panel_view,
        coord: coord,
        ax: Axes,
        params: dict[str, Any],
    ):
        data = coord.transform(data, panel_params)
        texts = geom_richtext._make_artists(data, panel_params, ax, params)
        if params.get("adjust_text") is not None and texts:
            from plotnine.geoms.geom_text import do_adjust_text

            do_adjust_text(
                texts,
                ax,
                params["adjust_text"],
                to_rgba(data["color"].iloc[0], data["alpha"].iloc[0]),
                float(data["size"].mean()),
                params["zorder"],
            )


_textbox_aes = geom_text.DEFAULT_AES.copy()
_textbox_aes.update(
    {
        "fill": "white",
        "halign": "left",
        "valign": "top",
        "orientation": "upright",
        "box_color": None,
        "box_size": 0.7,
        "text_color": None,
    }
)

_textbox_params = geom_text.DEFAULT_PARAMS.copy()
_textbox_params.pop("parse", None)
_textbox_params.update(
    {
        "width": "2in",
        "minwidth": None,
        "maxwidth": None,
        "height": None,
        "minheight": None,
        "maxheight": None,
        "box_padding": 5.5,
        "box_margin": 0,
        "box_r": 5.5,
        "rotation_mode": "anchor",
        "markdown": True,
        "newline": "break",
    }
)


@document
class geom_textbox(_RichGeomMixin, geom_text):  # type: ignore[misc]
    """
    Word-wrapped rich text in boxes

    {usage}

    Each label is drawn in a box of a fixed width and word-wrapped to
    fit. The ``ha``/``va`` aesthetics (or ``hjust``/``vjust``) place the
    box relative to the point (default: centered); ``halign``/``valign``
    align the text inside the box.

    Parameters
    ----------
    {common_parameters}
    width : str | float, default="2in"
        Width of the boxes: a string with units (``"2in"``,
        ``"150pt"``, ``"5cm"``) or a fraction (0, 1] of the panel
        width. ``None`` sizes each box to its text (see *maxwidth*).
    minwidth, maxwidth : str | float, default=None
        Limits for the width. With a *width* they clamp it, as in
        ggtext. With ``width=None``, *maxwidth* gives shrink-to-fit boxes
        that wrap at *maxwidth*.
    height : str | float, default=None
        Height of the boxes, same units as *width* (fractions are of the
        panel height). Text that does not fit overflows, as in ggtext.
        ``None`` fits each box to its text.
    minheight, maxheight : str | float, default=None
        Limits for the height.
    box_padding : float, default=5.5
        Padding inside the box, in points.
    box_margin : float, default=0
        Space outside the box, in points.
    box_r : float, default=5.5
        Radius of the rounded corners, in points.
    rotation_mode : str, default="anchor"
        How rotated (``orientation``) boxes are placed; see
        [](`~ggtext.geom_richtext`).
    markdown : bool, default=True
        Interpret Markdown. If False, only HTML is interpreted.
    newline : str, default="break"
        ``"break"`` makes ``"\\n"`` a line break; ``"space"`` treats it
        as a space.

    Notes
    -----
    ``box_color`` (outline color; None uses the text color, ``"none"``
    draws no outline), ``box_size`` (outline width in points),
    ``text_color``, ``halign``, ``valign`` and ``orientation``
    (``"upright"``, ``"left-rotated"``, ``"right-rotated"``,
    ``"inverted"``) are aesthetics and can be mapped to data.

    See Also
    --------
    ggtext.geom_richtext
    ggtext.element_textbox
    """

    DEFAULT_AES = _textbox_aes
    DEFAULT_PARAMS = _textbox_params

    @staticmethod
    def _spec_for_row(row: pd.Series, params: dict, text_color, ha) -> RichTextSpec:
        fill = _rgba_or_none(row.get("fill"), row.get("alpha"))
        edge, lw = _RichGeomMixin._outline(row, "box_color", "box_size", text_color)
        return RichTextSpec(
            markdown=params.get("markdown", True),
            newline=params.get("newline", "break"),
            width=params.get("width"),
            minwidth=params.get("minwidth"),
            maxwidth=params.get("maxwidth"),
            height=params.get("height"),
            minheight=params.get("minheight"),
            maxheight=params.get("maxheight"),
            halign=_as_halign(row.get("halign", "left")),
            valign=_as_valign(row.get("valign", "top")),
            fill=fill,
            box_color=edge,
            linewidth=lw,
            r=params.get("box_r", 0) or 0,
            padding=params.get("box_padding", 0) or 0,
            margin=params.get("box_margin", 0) or 0,
        )

    @staticmethod
    def _text_kwargs(row: pd.Series, color, ha, va, params: dict) -> dict:
        kw = _RichGeomMixin._text_kwargs(row, color, ha, va, params)
        orientation = row.get("orientation", "upright")
        if _is_missing(orientation):
            orientation = "upright"
        if orientation not in _ORIENTATION_ANGLES:
            raise PlotnineError(
                f"Unknown orientation {orientation!r}, must be one of "
                f"{list(_ORIENTATION_ANGLES)}"
            )
        if orientation != "upright":
            kw["rotation"] = _ORIENTATION_ANGLES[orientation]
        return kw

    @staticmethod
    def draw_group(
        data: pd.DataFrame,
        panel_params: panel_view,
        coord: coord,
        ax: Axes,
        params: dict[str, Any],
    ):
        data = coord.transform(data, panel_params)
        geom_textbox._make_artists(data, panel_params, ax, params)
