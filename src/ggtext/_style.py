"""
Text styles.

A :class:`Style` describes how one run of text is drawn. It is
``ggir.Style`` (an immutable dataclass; see its docstring for the fields)
plus conversion to and from matplotlib ``FontProperties``. Styles are
derived from one another, e.g. the style inside a ``<b>`` tag is the
surrounding style with ``weight="bold"``; ``ggir.resolve`` keeps this
subclass when it derives them.

Sizes are always stored in **points**. Colors are stored as given and
resolved by matplotlib at draw time, so anything matplotlib accepts as a
color works (``"red"``, ``"#ff0000"``, ``"C0"``, ``"tab:blue"``, ...), in
addition to the CSS ``rgb()``/``rgba()`` notations.
"""

from __future__ import annotations

from typing import Any

import ggir
from matplotlib.colors import to_rgba
from matplotlib.font_manager import FontProperties

__all__ = ["Style", "parse_color"]


class Style(ggir.Style):
    """
    The visual style of a run of text: ``ggir.Style`` with matplotlib
    helpers.

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
