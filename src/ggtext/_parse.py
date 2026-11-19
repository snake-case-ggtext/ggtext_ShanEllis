"""
Parse Markdown / HTML / CSS strings into a flat list of styled tokens.

Parsing itself is done by `ggIR <https://github.com/snake-case-ggtext/ggIR>`_,
which turns a string into a renderer-independent document tree (see its
README for the supported Markdown, HTML and CSS). :mod:`ggtext._ir`
resolves that tree into the tokens defined here. A string such as::

    "Hello **world** and <span style='color:red'>red</span>"

becomes::

    [TextRun("Hello ", base), TextRun("world", bold),
     TextRun(" and ", base), TextRun("red", red)]

Line breaks are explicit :data:`LINE_BREAK` tokens. Layout (measuring,
wrapping, aligning) happens later in :mod:`ggtext._layout`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Union

from ._style import Style

__all__ = [
    "TextRun",
    "ImageRun",
    "LineBreak",
    "LINE_BREAK",
    "Token",
    "parse",
    "plain_text",
]


@dataclass(frozen=True)
class TextRun:
    """A run of text drawn in a single style."""

    text: str
    style: Style
    math: bool = False


@dataclass(frozen=True)
class ImageRun:
    """An inline image (``<img>`` or ``![alt](src)``)."""

    src: str
    style: Style
    width: float | None = None  # points
    height: float | None = None  # points
    alt: str = ""


class LineBreak:
    """A hard line break."""

    _instance: LineBreak | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "LINE_BREAK"


LINE_BREAK = LineBreak()

Token = Union[TextRun, ImageRun, LineBreak]


def parse(
    s: str,
    base: Style | None = None,
    *,
    markdown: bool = True,
    html: bool = True,
    math: bool = True,
    newline: str = "break",
) -> List[Token]:
    """
    Parse a rich-text string into tokens.

    Parameters
    ----------
    s :
        The string to parse.
    base :
        The style of text outside of any markup (default: an empty
        style, i.e. everything inherited from the artist).
    markdown :
        Interpret Markdown syntax. If False, only HTML is interpreted.
    html :
        Interpret HTML tags. Only applies when ``markdown=False``;
        with markdown the HTML tags are always recognized.
        If both are False the text is returned as a single run.
    math :
        Treat ``$...$`` segments as matplotlib mathtext.
    newline :
        What a newline character (``"\\n"``) means: ``"break"`` (the
        default, as in matplotlib) starts a new line; ``"space"``
        treats it as a space, as in Markdown/HTML (use ``<br>`` or two
        trailing spaces for a break).

    Returns
    -------
    list
        :class:`TextRun`, :class:`ImageRun` and :data:`LINE_BREAK`
        tokens.
    """
    import ggir

    from ._ir import tokens_from_document

    if base is None:
        base = Style()
    doc = ggir.parse(
        str(s),
        markdown=markdown,
        html=html,
        math=math,
        newline=newline,
        # tokens_from_document warns about unsupported tags itself
        on_unknown="ignore",
    )
    return tokens_from_document(doc, base)


def plain_text(tokens: Sequence[Token]) -> str:
    """The text content of *tokens* with markup removed."""
    out = []
    for t in tokens:
        if isinstance(t, TextRun):
            out.append(t.text)
        elif isinstance(t, ImageRun):
            out.append(t.alt)
        else:
            out.append("\n")
    return "".join(out)
