"""
plotnine integration for ggtext.

>>> from ggtext.plotnine import element_markdown, geom_richtext  # doctest: +SKIP

The same names are also available from the top-level package
(``from ggtext import element_markdown``).
"""

from __future__ import annotations

from ._theme_hook import install_theme_hook
from .elements import element_markdown, element_textbox, element_textbox_simple
from .geoms import geom_richtext, geom_textbox

install_theme_hook()  # element_markdown themes need it

__all__ = [
    "element_markdown",
    "element_textbox",
    "element_textbox_simple",
    "geom_richtext",
    "geom_textbox",
]
