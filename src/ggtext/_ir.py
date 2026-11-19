"""
Turn a ggIR document tree into ggtext's flat list of styled tokens.

Parsing (Markdown, HTML, inline CSS, ``$math$``) is done by
`ggIR <https://github.com/snake-case-ggtext/ggIR>`_, which returns a
renderer-independent tree of style *overrides*. This module walks that
tree and resolves it into concrete :class:`~ggtext._style.Style` objects:
relative sizes become points, ``<sup>``/``<sub>`` and
``vertical-align`` become baseline shifts, and colours are validated
with matplotlib. The result is what :mod:`ggtext._layout` consumes.
"""

from __future__ import annotations

import warnings
from typing import List, Sequence

from ggir import Document, Image, LineBreak, Math, Paragraph, Span, Text

from ._parse import LINE_BREAK, ImageRun, TextRun, Token
from ._style import SUB_SHIFT, SUP_SHIFT, SUPSUB_SCALE, Style, parse_color

__all__ = ["tokens_from_document"]

# 1em when the base style has no size (matplotlib's "medium")
DEFAULT_EM = 10.0

# Tags whose own meaning sets the font size. Their size is resolved
# against the parent (it may also come from the tag's inline CSS; ggIR
# keeps one size per node).
_SIZING_TAGS = {"small", "big", "font"}

# Tags ggtext knows how to draw; others are drawn as plain spans
_KNOWN_TAGS = {
    "b", "strong", "i", "em", "u", "ins", "s", "del", "strike", "sup", "sub",
    "span", "font", "code", "kbd", "tt", "samp", "small", "big", "mark", "a",
    "p", "div", "img",
}  # fmt: skip

_warned: set = set()


def _warn_once(msg: str):
    if msg not in _warned:
        _warned.add(msg)
        warnings.warn(msg, UserWarning, stacklevel=5)


def _color(value, warn: bool):
    """A validated colour, or None (with a warning if *warn*)."""
    if isinstance(value, tuple):  # CSS rgb()/rgba(), already converted
        return value
    color = parse_color(value)
    if color is None and warn:
        _warn_once(f"ggtext: invalid color {value!r}")
    return color


def _derive(node: Span | Paragraph, style: Style) -> Style:
    """The style inside *node*, a container in the parent *style*."""
    if node.tag not in _KNOWN_TAGS:
        _warn_once(f"ggtext: unsupported HTML tag <{node.tag}> was ignored")

    em = style.size if style.size is not None else DEFAULT_EM
    changes: dict = {}
    shift = style.shift

    # What the tag itself does
    size = style.size
    script = getattr(node, "script", None)
    if script == "sup":
        size = em * SUPSUB_SCALE
        shift = shift + SUP_SHIFT * em
    elif script == "sub":
        size = em * SUPSUB_SCALE
        shift = shift + SUB_SHIFT * em
    if node.size is not None and node.tag in _SIZING_TAGS:
        size = node.size.to_pt(em)

    # Inline CSS: relative values are relative to the size after the tag
    css_em = size if size is not None else DEFAULT_EM
    if node.size is not None and node.tag not in _SIZING_TAGS:
        size = node.size.to_pt(css_em)
    valign = getattr(node, "valign", None)
    if valign == "super":
        shift = shift + SUP_SHIFT * css_em
    elif valign == "sub":
        shift = shift + SUB_SHIFT * css_em
    elif valign == "baseline":
        shift = 0.0
    elif valign is not None:
        shift = shift + valign.to_pt(css_em)

    if size != style.size:
        changes["size"] = size
    if shift != style.shift:
        changes["shift"] = shift
    for name in ("weight", "style", "variant", "family", "underline", "strike"):
        value = getattr(node, name)
        if value is not None:
            changes[name] = value
    if node.color is not None and (c := _color(node.color, warn=True)) is not None:
        changes["color"] = c
    if (
        node.background is not None
        and (c := _color(node.background, warn=False)) is not None
    ):
        changes["background"] = c
    if node.href is not None:
        changes["url"] = node.href
    return style.update(**changes) if changes else style


class _Walker:
    def __init__(self):
        self.tokens: List[Token] = []
        # True after a paragraph closes, until real content follows: a
        # trailing paragraph must not leave an empty last line
        self.after_paragraph = False

    def walk(self, nodes: Sequence, style: Style):
        for node in nodes:
            if isinstance(node, Text):
                self.text(node.text, style)
            elif isinstance(node, Math):
                self.tokens.append(TextRun(f"${node.tex}$", style, math=True))
                self.after_paragraph = False
            elif isinstance(node, LineBreak):
                self.tokens.append(LINE_BREAK)
            elif isinstance(node, Image):
                self.image(node, style)
            elif isinstance(node, Paragraph):
                self.paragraph_break()
                self.walk(node.children, _derive(node, style))
                self.paragraph_break()
                self.after_paragraph = True
            elif isinstance(node, Span):
                self.walk(node.children, _derive(node, style))
            else:  # pragma: no cover - a node type from a newer ggIR
                raise TypeError(f"ggtext: unknown ggIR node {node!r}")

    def text(self, s: str, style: Style):
        if not s:
            return
        if s.strip():
            self.after_paragraph = False
        tokens = self.tokens
        # Merge with the previous run if the style is the same
        if (
            tokens
            and isinstance(prev := tokens[-1], TextRun)
            and not prev.math
            and prev.style == style
        ):
            tokens[-1] = TextRun(prev.text + s, style)
        else:
            tokens.append(TextRun(s, style))

    def image(self, node: Image, style: Style):
        em = style.size if style.size is not None else DEFAULT_EM
        width = node.width.to_pt(em) if node.width is not None else None
        height = node.height.to_pt(em) if node.height is not None else None
        self.tokens.append(ImageRun(node.src, style, width, height, node.alt))
        self.after_paragraph = False

    def paragraph_break(self):
        """Start a new line unless we are already at the start of one."""
        if self.tokens and self.tokens[-1] is not LINE_BREAK:
            self.tokens.append(LINE_BREAK)

    def finish(self) -> List[Token]:
        if self.after_paragraph and self.tokens and self.tokens[-1] is LINE_BREAK:
            self.tokens.pop()
        return self.tokens


def tokens_from_document(doc: Document, base: Style) -> List[Token]:
    """
    Resolve a ggIR document into ggtext tokens.

    Parameters
    ----------
    doc :
        The output of :func:`ggir.parse`.
    base :
        The style of text outside of any markup.

    Returns
    -------
    list
        :class:`~ggtext._parse.TextRun` (``math=True`` for ``$...$``,
        delimiters included), :class:`~ggtext._parse.ImageRun` and
        :data:`~ggtext._parse.LINE_BREAK` tokens. Adjacent runs with the
        same style are merged. A paragraph starts and ends a line, and a
        trailing paragraph does not leave an empty last line.
    """
    walker = _Walker()
    walker.walk(doc.children, base)
    return walker.finish()
