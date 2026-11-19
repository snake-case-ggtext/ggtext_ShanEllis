"""
Text styles.

A :class:`Style` describes how one run of text is drawn. Styles are
immutable and are derived from one another, e.g. the style inside a
``<b>`` tag is the surrounding style with ``weight="bold"``.

Sizes are always stored in **points**. Colors are stored as given and
resolved by matplotlib at draw time, so anything matplotlib accepts as a
color works (``"red"``, ``"#ff0000"``, ``"C0"``, ``"tab:blue"``, ...), in
addition to the CSS ``rgb()``/``rgba()`` notations.

Inline CSS is parsed by ggIR (``ggir.css``); :mod:`ggtext._ir` turns the
parsed values into styles.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Tuple

import ggir
from matplotlib.colors import to_rgba
from matplotlib.font_manager import FontProperties

__all__ = ["Style", "parse_color"]

# Relative font sizes used by HTML-ish tags
SUPSUB_SCALE = 0.7  # size of <sup>/<sub> text relative to the parent
SUP_SHIFT = 0.40  # baseline shift of <sup>, in parent ems
SUB_SHIFT = -0.20  # baseline shift of <sub>, in parent ems


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
            kwargs["family"] = ggir.split_families(kwargs["family"])
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


def parse_color(value: str) -> Any:
    """
    Parse a CSS color into something matplotlib understands.

    Supports every color format matplotlib accepts plus CSS
    ``rgb(r, g, b)`` and ``rgba(r, g, b, a)`` with 0-255 channels
    (or percentages), which ``ggir.parse_color`` converts to an RGBA
    tuple. Returns ``None`` for invalid colors.
    """
    color = ggir.parse_color(value)
    if color is None or isinstance(color, tuple):
        return color
    try:
        to_rgba(color)
    except ValueError:
        return None
    return color
