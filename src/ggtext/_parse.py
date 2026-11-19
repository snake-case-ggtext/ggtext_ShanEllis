"""
Parse Markdown / HTML / CSS strings into a flat list of styled tokens.

Parsing itself is done by `ggIR <https://github.com/snake-case-ggtext/ggIR>`_,
which turns a string into a renderer-independent document tree (see its
README for the supported Markdown, HTML and CSS), and ``ggir.resolve``
turns that tree into styled tokens using ggtext's numbers
(:data:`GGTEXT_POLICY`) and matplotlib colour validation. The token
types are ggIR's and are re-exported here. A string such as::

    "Hello **world** and <span style='color:red'>red</span>"

becomes::

    [TextRun("Hello ", base), TextRun("world", bold),
     TextRun(" and ", base), TextRun("red", red)]

Line breaks are explicit :data:`LINE_BREAK` tokens. Layout (measuring,
wrapping, aligning) happens later in :mod:`ggtext._layout`.
"""

from __future__ import annotations

import ggir
from ggir.resolve import (
    LINE_BREAK,
    ImageRun,
    LineBreak,
    Policy,
    TextRun,
    Token,
    plain_text,
)

from ._style import Style, parse_color

__all__ = [
    "GGTEXT_POLICY",
    "LINE_BREAK",
    "ImageRun",
    "LineBreak",
    "TextRun",
    "Token",
    "parse",
    "plain_text",
]

# How ggtext draws <sup>/<sub>: 0.7x the parent size, raised 0.4em or
# lowered 0.2em; 1em is 10pt (matplotlib's "medium") when no size is set.
GGTEXT_POLICY = Policy(
    default_em=10.0, script_scale=0.7, sup_shift=0.40, sub_shift=-0.20
)


def parse(
    s: str,
    base: Style | None = None,
    *,
    markdown: bool = True,
    html: bool = True,
    math: bool = True,
    newline: str = "break",
) -> list[Token]:
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
    if base is None:
        base = Style()
    doc = ggir.parse(
        str(s),
        markdown=markdown,
        html=html,
        math=math,
        newline=newline,
        # ggir.resolve warns about unsupported tags itself
        on_unknown="ignore",
    )
    return ggir.resolve(
        doc,
        base,
        policy=GGTEXT_POLICY,
        validate_color=parse_color,
        warn_prefix="ggtext",
    )
