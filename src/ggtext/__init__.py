"""
ggtext: rich text (Markdown, HTML and CSS) for plotnine.

A Python take on the R package `ggtext <https://wilkelab.org/ggtext/>`_.

>>> from plotnine import ggplot, aes, geom_point, labs, theme
>>> from ggtext import element_markdown  # doctest: +SKIP
>>> (ggplot(df, aes("x", "y")) + geom_point()
...  + labs(title="**Bold** title with <span style='color:red'>red</span>")
...  + theme(plot_title=element_markdown()))  # doctest: +SKIP
"""

from __future__ import annotations

from ._images import options, register_image
from ._parse import parse
from ._spec import RichTextSpec
from ._style import Style
from .plotnine import (
    element_markdown,
    element_textbox,
    element_textbox_simple,
    geom_richtext,
    geom_textbox,
)

__version__ = "0.1.0"

__all__ = [
    "RichTextSpec",
    "Style",
    "element_markdown",
    "element_textbox",
    "element_textbox_simple",
    "geom_richtext",
    "geom_textbox",
    "options",
    "parse",
    "register_image",
]
