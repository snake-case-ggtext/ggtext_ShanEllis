"""
ggtext: rich text (Markdown, HTML and CSS) for matplotlib and plotnine.

A Python take on the R package `ggtext <https://wilkelab.org/ggtext/>`_.

Matplotlib
----------
>>> import matplotlib.pyplot as plt
>>> import ggtext
>>> fig, ax = plt.subplots()
>>> _ = ggtext.text(ax, 0.5, 0.5, "Some **bold** and <span style='color:red'>red</span> text")
>>> _ = ggtext.set_title(ax, "A *rich* title")

plotnine
--------
>>> from plotnine import ggplot, aes, geom_point, labs, theme
>>> from ggtext import element_markdown  # doctest: +SKIP
>>> (ggplot(df, aes("x", "y")) + geom_point()
...  + labs(title="**Bold** title with <span style='color:red'>red</span>")
...  + theme(plot_title=element_markdown()))  # doctest: +SKIP
"""

from __future__ import annotations

from typing import Any

from ._artist import RichText, is_rich, make_plain, make_rich
from ._images import options, register_image
from ._parse import parse
from ._spec import RichTextSpec
from ._style import Style
from .mpl import (
    annotate,
    rich_ticklabels,
    richify,
    set_suptitle,
    set_title,
    set_xlabel,
    set_ylabel,
    text,
    textbox,
)

__version__ = "0.1.0"

__all__ = [
    # matplotlib
    "RichText",
    "RichTextSpec",
    "Style",
    "annotate",
    # plotnine (imported lazily)
    "element_markdown",
    "element_textbox",
    "element_textbox_simple",
    "geom_richtext",
    "geom_textbox",
    "is_rich",
    "make_plain",
    "make_rich",
    "options",
    "parse",
    "register_image",
    "rich_ticklabels",
    "richify",
    "set_suptitle",
    "set_title",
    "set_xlabel",
    "set_ylabel",
    "text",
    "textbox",
]

_PLOTNINE_NAMES = {
    "element_markdown",
    "element_textbox",
    "element_textbox_simple",
    "geom_richtext",
    "geom_textbox",
}


def __getattr__(name: str) -> Any:
    # plotnine is an optional dependency, so import it only when code
    # uses a plotnine helper.
    if name in _PLOTNINE_NAMES:
        from . import plotnine as _p9

        return getattr(_p9, name)
    raise AttributeError(f"module 'ggtext' has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | _PLOTNINE_NAMES)
