"""
The options that turn a matplotlib Text into rich text.

A :class:`RichTextSpec` is what gets attached to a text artist with
``text.set(richtext=spec)``. Everything that is not a plain matplotlib
text property lives here. It covers parsing options, word wrapping and the box
drawn around the text.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields, replace
from typing import Any

import ggir

__all__ = ["Length", "RichTextSpec", "resolve_length"]

Length = float | str | None

#: Options that hold a length (absolute with units, or a fraction)
LENGTH_FIELDS = ("width", "minwidth", "maxwidth", "height", "minheight", "maxheight")

# ggplot2 / R-style spellings that we also accept
_ALIASES = {
    "box_colour": "box_color",
    "box.colour": "box_color",
    "box.color": "box_color",
    "linetype": "linestyle",
    "label_r": "r",
    "radius": "r",
}


def parse_length(value: Any, *, allow_percent: bool = True) -> float | None:
    """An absolute CSS length (``12``, ``"16px"``, ``"1in"``) in points, or None."""
    length = ggir.parse_length(value, allow_percent=allow_percent)
    if length is None or length.unit != "pt":  # em, %, keywords
        return None
    return length.value


def _as_padding(value: Any) -> tuple[float, float, float, float]:
    """
    Normalize padding to ``(top, right, bottom, left)`` in points.

    Accepts a single number, a 2-tuple ``(vertical, horizontal)``, or a
    4-tuple in CSS order ``(top, right, bottom, left)``. It also accepts a
    dict with any of the keys ``t``, ``r``, ``b``, ``l``.
    """
    if value is None:
        return (0.0, 0.0, 0.0, 0.0)
    if isinstance(value, Mapping):
        return tuple(  # type: ignore[return-value]
            float(parse_length(value.get(k, 0)) or 0) for k in ("t", "r", "b", "l")
        )
    if isinstance(value, (int, float, str)):
        v = float(parse_length(value) or 0)
        return (v, v, v, v)
    vals = [float(parse_length(v) or 0) for v in value]
    if len(vals) == 1:
        return (vals[0],) * 4  # type: ignore[return-value]
    if len(vals) == 2:
        return (vals[0], vals[1], vals[0], vals[1])
    if len(vals) == 4:
        return tuple(vals)  # type: ignore[return-value]
    raise ValueError(f"padding must have 1, 2 or 4 values, got {value!r}")


@dataclass(frozen=True)
class RichTextSpec:
    """
    Rich text options for a matplotlib text artist.

    Parameters
    ----------
    markdown :
        Interpret Markdown syntax (``**bold**``, ``*italic*``, ...).
        HTML tags are always interpreted when this is True.
    html :
        Interpret HTML tags when ``markdown=False``.
    math :
        Render ``$...$`` segments with matplotlib's mathtext.
    newline :
        ``"break"`` (default): a newline character starts a line,
        as in matplotlib. ``"space"``: newlines are spaces, as in
        Markdown/HTML; use ``<br>`` for a line break.
    halign :
        Alignment of the lines within the text block / box: ``"left"``,
        ``"center"`` or ``"right"``. ``None`` uses the artist's own
        multialignment (``ma``).
    valign :
        Vertical alignment of the text inside a box with a fixed
        ``height``: ``"top"``, ``"center"`` or ``"bottom"``.
    width :
        Width of the box. Text is word-wrapped to fit. A float between 0
        and 1 is a fraction of the reference width. The reference is the
        panel area for plot titles. For text inside an axes, it is the axes;
        otherwise it is the figure. A string may carry units: ``"3in"``, ``"200pt"``,
        ``"8cm"``, ``"50%"``. ``None`` (default) means no wrapping.
    minwidth, maxwidth :
        Limits for the width of the box, same units as ``width``. With a
        ``width`` they clamp it (as in ggtext). Without a ``width``, ``maxwidth`` gives a shrink-to-fit box that wraps
        only when the text is longer than ``maxwidth``. ``minwidth`` widens
        boxes of short text.
    height :
        Height of the box (same units as ``width``; fractions are of the
        reference height). ``valign`` places the text in it. The text may overflow a box that is
        too small, as in ggtext. ``None``
        (default) fits the box to the text.
    minheight, maxheight :
        Limits for the height of the box.
    padding :
        Space between the text and the edge of the box, in points.
        A number, ``(vertical, horizontal)``, ``(top, right, bottom,
        left)`` or a dict with keys ``t``, ``r``, ``b``, ``l``.
    margin :
        Space outside the box, in points, same forms as ``padding``. It counts toward the text's size (so it moves the box away from the
        anchor point), but it draws nothing. Widths and heights
        refer to the box itself, excluding the margin.
    fill :
        Background color of the box. ``None`` for no background.
    box_color :
        Color of the box outline. ``None`` for no outline.
    linewidth :
        Width of the box outline in points.
    linestyle :
        Line style of the box outline (``"solid"``, ``"dashed"``, ...).
    r :
        Radius of the box's rounded corners, in points.
    """

    markdown: bool = True
    html: bool = True
    math: bool = True
    newline: str = "break"
    halign: str | None = None
    valign: str = "top"
    width: Length = None
    minwidth: Length = None
    maxwidth: Length = None
    height: Length = None
    minheight: Length = None
    maxheight: Length = None
    padding: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    margin: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    fill: Any = None
    box_color: Any = None
    linewidth: float = 0.5
    linestyle: Any = "solid"
    r: float = 0.0

    def __post_init__(self):
        object.__setattr__(self, "padding", _as_padding(self.padding))
        object.__setattr__(self, "margin", _as_padding(self.margin))
        if isinstance(self.fill, list):
            object.__setattr__(self, "fill", tuple(self.fill))
        if isinstance(self.box_color, list):
            object.__setattr__(self, "box_color", tuple(self.box_color))
        if self.newline not in ("break", "space"):
            raise ValueError(
                f"newline must be 'break' or 'space', not {self.newline!r}"
            )
        if self.halign not in (None, "left", "center", "right"):
            raise ValueError(
                f"halign must be 'left', 'center' or 'right', not {self.halign!r}"
            )
        if self.valign not in ("top", "center", "bottom"):
            raise ValueError(
                f"valign must be 'top', 'center' or 'bottom', not {self.valign!r}"
            )
        for name in LENGTH_FIELDS:
            _check_length(name, getattr(self, name))

    @property
    def has_box(self) -> bool:
        """Whether a box (background and/or outline) is drawn."""
        return self.fill is not None or self.box_color is not None

    def replace(self, **kwargs: Any) -> RichTextSpec:
        """Return a copy with some options changed."""
        return replace(self, **_normalize_kwargs(kwargs))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def coerce(cls, value: Any) -> RichTextSpec | None:
        """
        Convert *value* to a spec.

        ``True`` gives the default spec, a dict gives a spec with those
        options, and a spec passes through unchanged. ``None`` or ``False``
        give ``None`` (meaning: plain text).
        """
        if value is None or value is False:
            return None
        if value is True:
            return cls()
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(**_normalize_kwargs(dict(value)))
        raise TypeError(
            "richtext must be True, False, None, a dict or a RichTextSpec, "
            f"not {type(value).__name__}"
        )


_FIELD_NAMES = {f.name for f in fields(RichTextSpec)}


def _normalize_kwargs(kwargs: dict) -> dict:
    out = {}
    for key, value in kwargs.items():
        key = _ALIASES.get(key, key)
        if key not in _FIELD_NAMES:
            raise TypeError(f"Unknown rich text option {key!r}")
        out[key] = value
    return out


def _check_length(name: str, value: Length):
    if value is None or isinstance(value, str):
        if isinstance(value, str) and resolve_length(value, 100.0, 72.0) is None:
            raise ValueError(f"Could not understand {name}={value!r}")
        return
    if not (0 < float(value) <= 1):
        raise ValueError(
            f"{name}={value!r}: numbers are fractions of the available space "
            "and must be in (0, 1]. For an absolute size use a string with "
            f"units, e.g. {name}='{value}in' or {name}='{value}pt'."
        )


def resolve_length(value: Length, reference: float, dpi: float) -> float | None:
    """
    Convert a length to pixels.

    Parameters
    ----------
    value :
        ``None``, a fraction of *reference* (``0 < value <= 1``). A
        string with units (``"2in"``, ``"144pt"``, ``"5cm"``, ``"50%"``).
    reference :
        The reference length in pixels for fractions and percentages.
    dpi :
        Dots per inch, to convert absolute units to pixels.
    """
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip().lower()
        if s.endswith("%"):
            try:
                return float(s[:-1]) / 100 * reference
            except ValueError:
                return None
        if s.endswith("npc"):
            try:
                return float(s[:-3]) * reference
            except ValueError:
                return None
        points = parse_length(s, allow_percent=False)
        if points is None:
            return None
        return points * dpi / 72
    return float(value) * reference
