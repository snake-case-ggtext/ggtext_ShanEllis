"""
Text styles and the small CSS subset that ggtext understands.

A :class:`Style` describes how one run of text is drawn. Styles are
immutable and are derived from one another, e.g. the style inside a
``<b>`` tag is the surrounding style with ``weight="bold"``.

Sizes are always stored in **points**. Colors are stored as given and
resolved by matplotlib at draw time, so anything matplotlib accepts as a
color works (``"red"``, ``"#ff0000"``, ``"C0"``, ``"tab:blue"``, ...), in
addition to the CSS ``rgb()``/``rgba()`` notations.
"""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass, field, replace
from typing import Any, Tuple

from matplotlib.colors import to_rgba
from matplotlib.font_manager import FontProperties

__all__ = ["Style", "parse_css", "parse_length", "parse_color"]

# Relative font sizes used by HTML-ish tags
SUPSUB_SCALE = 0.7  # size of <sup>/<sub> text relative to the parent
SUP_SHIFT = 0.40  # baseline shift of <sup>, in parent ems
SUB_SHIFT = -0.20  # baseline shift of <sub>, in parent ems
SMALL_SCALE = 0.833
BIG_SCALE = 1.2

# CSS absolute-size keywords in points, relative to a "medium" of 10pt
# (matplotlib's own convention, see FontProperties).
_CSS_SIZE_KEYWORDS = {
    "xx-small": 0.579,
    "x-small": 0.694,
    "small": 0.833,
    "medium": 1.0,
    "large": 1.2,
    "x-large": 1.44,
    "xx-large": 1.728,
}

_LENGTH_RE = re.compile(
    r"^\s*(?P<num>[+-]?(?:\d+\.?\d*|\.\d+))\s*(?P<unit>[a-z%]*)\s*$",
    re.IGNORECASE,
)

# points per unit
_POINTS_PER = {
    "pt": 1.0,
    "px": 0.75,  # CSS px are 1/96 in
    "in": 72.0,
    "cm": 72.0 / 2.54,
    "mm": 72.0 / 25.4,
    "pc": 12.0,
}


@dataclass(frozen=True)
class Style:
    """
    The visual style of a run of text.

    Parameters
    ----------
    family :
        Font family (a name or a generic family such as ``"serif"``).
        ``None`` means "inherit from the artist".
    size :
        Font size in points. ``None`` means "inherit from the artist".
    weight :
        Font weight, e.g. ``"normal"`` or ``"bold"``.
    style :
        Font style: ``"normal"``, ``"italic"`` or ``"oblique"``.
    variant :
        ``"normal"`` or ``"small-caps"``.
    color :
        Text color; ``None`` means "inherit from the artist".
    background :
        Highlight color drawn behind the run (CSS ``background-color``).
    underline, strike :
        Draw a line under / through the run.
    shift :
        Baseline shift in points (positive is up). Used by sup/sub.
    url :
        Hyperlink target (honored by the SVG and PDF backends).
    """

    family: Tuple[str, ...] | None = None
    size: float | None = None
    weight: Any = None
    style: str | None = None
    variant: str | None = None
    color: Any = None
    background: Any = None
    underline: bool = False
    strike: bool = False
    shift: float = 0.0
    url: str | None = None

    # -- derivation -------------------------------------------------------
    def update(self, **kwargs: Any) -> Style:
        """Return a copy of this style with some attributes replaced."""
        if "family" in kwargs and isinstance(kwargs["family"], str):
            kwargs["family"] = _split_families(kwargs["family"])
        return replace(self, **kwargs)

    def resolve(self, base: Style) -> Style:
        """
        Fill in attributes that are ``None`` from *base*.

        Used to resolve a parsed style against the artist's own font
        properties at layout time.
        """
        values = {}
        for name in ("family", "size", "weight", "style", "variant", "color"):
            if getattr(self, name) is None:
                values[name] = getattr(base, name)
        return replace(self, **values) if values else self

    def fontproperties(self) -> FontProperties:
        """The matplotlib FontProperties for this style."""
        return FontProperties(
            family=list(self.family) if self.family else None,
            size=self.size,
            weight=self.weight,
            style=self.style,
            variant=self.variant,
        )

    @classmethod
    def from_fontproperties(cls, fp: FontProperties, color: Any = None) -> Style:
        """Create a style from matplotlib FontProperties."""
        return cls(
            family=tuple(fp.get_family()),
            size=fp.get_size_in_points(),
            weight=fp.get_weight(),
            style=fp.get_style(),
            variant=fp.get_variant(),
            color=color,
        )


def _split_families(value: str) -> Tuple[str, ...]:
    """Split a CSS font-family list into individual family names."""
    parts = [p.strip().strip("'\"") for p in value.split(",")]
    return tuple(p for p in parts if p)


def parse_length(
    value: Any,
    *,
    em: float | None = None,
    allow_percent: bool = True,
) -> float | None:
    """
    Convert a CSS-like length to points.

    Parameters
    ----------
    value :
        A number (already in points) or a string such as ``"12pt"``,
        ``"16px"``, ``"0.5in"``, ``"1.5em"`` or ``"120%"``.
    em :
        Size of 1em in points, required for ``em`` and ``%`` units.
    allow_percent :
        Whether percentages are allowed.

    Returns
    -------
    float or None
        The length in points, or ``None`` if it could not be parsed.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    s = str(value).strip().lower()
    if em is not None:
        if s in _CSS_SIZE_KEYWORDS:
            # keywords are relative to matplotlib's "medium" which is the
            # rcParams font size, we use the em instead to be predictable
            return _CSS_SIZE_KEYWORDS[s] * em
        if s == "larger":
            return em * BIG_SCALE
        if s == "smaller":
            return em * SMALL_SCALE

    m = _LENGTH_RE.match(s)
    if not m:
        return None
    num = float(m["num"])
    unit = m["unit"] or "pt"
    if unit in _POINTS_PER:
        return num * _POINTS_PER[unit]
    if unit in ("em", "rem") and em is not None:
        return num * em
    if unit == "%" and allow_percent and em is not None:
        return num / 100 * em
    return None


_RGB_RE = re.compile(r"^rgba?\((?P<args>[^)]*)\)$", re.IGNORECASE)


def parse_color(value: str) -> Any:
    """
    Parse a CSS color into something matplotlib understands.

    Supports every color format matplotlib accepts plus CSS
    ``rgb(r, g, b)`` and ``rgba(r, g, b, a)`` with 0-255 channels
    (or percentages). Returns ``None`` for invalid colors.
    """
    s = value.strip()
    m = _RGB_RE.match(s.replace(" ", "") if "(" in s else s)
    if m:
        args = [a for a in re.split(r"[,\s/]+", m["args"].strip()) if a]
        try:
            chans = []
            for i, a in enumerate(args[:4]):
                if a.endswith("%"):
                    chans.append(float(a[:-1]) / 100)
                elif i < 3:
                    chans.append(float(a) / 255)
                else:
                    chans.append(float(a))
            if len(chans) in (3, 4):
                return tuple(min(max(c, 0.0), 1.0) for c in chans)
        except ValueError:
            return None
        return None
    try:
        to_rgba(s)
    except ValueError:
        return None
    return s


@dataclass
class _CSSWarnings:
    """Collect unknown CSS so we only warn once per property name."""

    seen: set = field(default_factory=set)

    def warn(self, msg: str, key: str):
        if key not in self.seen:
            self.seen.add(key)
            warnings.warn(msg, UserWarning, stacklevel=4)


_css_warnings = _CSSWarnings()


def parse_css(declarations: str, style: Style) -> Style:
    """
    Apply inline CSS *declarations* to *style*.

    Supported properties
    --------------------
    ``color``, ``font-size``, ``font-family``, ``font-weight``,
    ``font-style``, ``font-variant``, ``background-color``
    (or ``background``), ``text-decoration`` (``underline``,
    ``line-through``, ``none``) and ``vertical-align`` (``super``,
    ``sub``, ``baseline`` or a length).

    Unknown properties produce a single :class:`UserWarning` and are
    otherwise ignored.
    """
    em = style.size
    changes: dict[str, Any] = {}
    for decl in declarations.split(";"):
        if ":" not in decl:
            continue
        name, _, value = decl.partition(":")
        name = name.strip().lower()
        value = value.strip()
        if value.lower().endswith("!important"):
            value = value[: -len("!important")].strip()
        if not value:
            continue

        if name == "color":
            color = parse_color(value)
            if color is None:
                _css_warnings.warn(f"ggtext: invalid color {value!r}", value)
            else:
                changes["color"] = color
        elif name in ("background-color", "background"):
            color = parse_color(value)
            if color is not None:
                changes["background"] = color
        elif name == "font-size":
            size = parse_length(value, em=em if em is not None else 10.0)
            if size is None:
                _css_warnings.warn(f"ggtext: invalid font-size {value!r}", value)
            else:
                changes["size"] = size
        elif name == "font-family":
            changes["family"] = _split_families(value)
        elif name == "font-weight":
            changes["weight"] = int(value) if value.isdigit() else value
        elif name == "font-style":
            changes["style"] = value
        elif name == "font-variant":
            changes["variant"] = value
        elif name in ("text-decoration", "text-decoration-line"):
            v = value.lower()
            if "none" in v:
                changes["underline"] = False
                changes["strike"] = False
            if "underline" in v:
                changes["underline"] = True
            if "line-through" in v:
                changes["strike"] = True
        elif name == "vertical-align":
            v = value.lower()
            base = em if em is not None else 10.0
            if v in ("super", "sup"):
                changes["shift"] = style.shift + SUP_SHIFT * base
            elif v == "sub":
                changes["shift"] = style.shift + SUB_SHIFT * base
            elif v == "baseline":
                changes["shift"] = 0.0
            else:
                length = parse_length(v, em=base)
                if length is not None:
                    changes["shift"] = style.shift + length
        else:
            _css_warnings.warn(
                f"ggtext: unsupported CSS property {name!r} was ignored", name
            )

    if "family" in changes:
        return replace(style, **changes)
    return replace(style, **changes) if changes else style
