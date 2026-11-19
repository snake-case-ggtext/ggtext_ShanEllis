"""
Parse Markdown / HTML / CSS strings into a flat list of styled tokens.

The parser is deliberately renderer-agnostic: it knows nothing about
matplotlib renderers or pixel sizes. It turns a string such as::

    "Hello **world** and <span style='color:red'>red</span>"

into a list of tokens::

    [TextRun("Hello ", base), TextRun("world", bold),
     TextRun(" and ", base), TextRun("red", red)]

Line breaks are explicit :data:`LINE_BREAK` tokens. Layout (measuring,
wrapping, aligning) happens later in :mod:`ggtext._layout`.

Supported syntax
----------------
Markdown (CommonMark inline syntax, via ``markdown-it-py``)
    ``**bold**``, ``__bold__``, ``*italic*``, ``_italic_``,
    ``~~strikethrough~~``, ```code```, ``[link](url)``,
    ``![alt](image.png)``, backslash escapes and HTML entities.
    Underscores inside words (``bill_length_mm``) are left alone.

HTML
    ``<b>``, ``<strong>``, ``<i>``, ``<em>``, ``<u>``, ``<ins>``,
    ``<s>``, ``<del>``, ``<strike>``, ``<sup>``, ``<sub>``, ``<br>``,
    ``<span style=...>``, ``<font color= face= size=>``, ``<code>``,
    ``<kbd>``, ``<tt>``, ``<small>``, ``<big>``, ``<mark>``, ``<a href=>``,
    ``<p>`` and ``<img src= width= height=>``. Any tag also accepts a
    ``style`` attribute with inline CSS (see :func:`ggtext._style.parse_css`).

Math
    ``$...$`` segments are passed to matplotlib's mathtext untouched.
"""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Sequence, Tuple, Union

from ._style import (
    BIG_SCALE,
    SMALL_SCALE,
    SUB_SHIFT,
    SUP_SHIFT,
    SUPSUB_SCALE,
    Style,
    parse_color,
    parse_css,
    parse_length,
)

__all__ = [
    "TextRun",
    "ImageRun",
    "LineBreak",
    "LINE_BREAK",
    "Token",
    "parse",
    "plain_text",
]

MONOSPACE = ("monospace",)


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

# -----------------------------------------------------------------------
# Math protection
# -----------------------------------------------------------------------
# Mathtext segments must not be touched by the markdown parser
# (``$a_1 * b_2$`` has underscores and stars). We swap each segment for a
# placeholder made of private-use characters and restore it afterwards.
_PH_OPEN, _PH_CLOSE = "", ""
_PH_RE = re.compile(f"{_PH_OPEN}(\\d+){_PH_CLOSE}")
_MATH_RE = re.compile(r"(?<!\\)\$(?:\\.|[^$\\])+?(?<!\\)\$")


def _protect_math(s: str) -> Tuple[str, List[str]]:
    segments: List[str] = []

    def repl(m: re.Match) -> str:
        segments.append(m.group(0))
        return f"{_PH_OPEN}{len(segments) - 1}{_PH_CLOSE}"

    return _MATH_RE.sub(repl, s), segments


# -----------------------------------------------------------------------
# HTML tags
# -----------------------------------------------------------------------
_TAG_RE = re.compile(
    r"^<\s*(?P<close>/)?\s*(?P<name>[a-zA-Z][\w:-]*)(?P<attrs>.*?)(?P<self>/)?\s*>$",
    re.DOTALL,
)
_ATTR_RE = re.compile(
    r"""(?P<key>[^\s"'>/=]+)(?:\s*=\s*(?P<val>"[^"]*"|'[^']*'|[^\s"'>]+))?"""
)
_HTML_IN_TEXT_RE = re.compile(r"<!--.*?-->|</?[a-zA-Z][^<>]*>", re.DOTALL)

VOID_TAGS = {"br", "img", "hr", "wbr"}
KNOWN_TAGS = {
    "b", "strong", "i", "em", "u", "ins", "s", "del", "strike", "sup", "sub",
    "br", "span", "font", "code", "kbd", "tt", "samp", "small", "big",
    "mark", "a", "p", "div", "img", "wbr", "hr",
}  # fmt: skip


def _parse_tag(raw: str) -> Tuple[str, dict, str] | None:
    """
    Parse a single HTML tag.

    Returns ``(name, attrs, kind)`` where kind is ``"open"``,
    ``"close"`` or ``"void"``, or None if *raw* is not a tag (e.g. a
    comment).
    """
    m = _TAG_RE.match(raw.strip())
    if not m:
        return None
    name = m["name"].lower()
    attrs = {}
    for am in _ATTR_RE.finditer(m["attrs"] or ""):
        val = am["val"]
        if val is None:
            val = ""
        elif val[:1] in "\"'":
            val = val[1:-1]
        attrs[am["key"].lower()] = val
    if m["close"]:
        kind = "close"
    elif m["self"] or name in VOID_TAGS:
        kind = "void"
    else:
        kind = "open"
    return name, attrs, kind


def _warn_once(msg: str, _seen: set = set()):  # noqa: B006
    if msg not in _seen:
        _seen.add(msg)
        warnings.warn(msg, UserWarning, stacklevel=5)


def _style_for_tag(name: str, attrs: dict, style: Style) -> Style:
    """The style inside an opening tag *name* with *attrs*."""
    em = style.size if style.size is not None else 10.0
    s = style
    if name in ("b", "strong"):
        s = s.update(weight="bold")
    elif name in ("i", "em"):
        s = s.update(style="italic")
    elif name in ("u", "ins"):
        s = s.update(underline=True)
    elif name in ("s", "del", "strike"):
        s = s.update(strike=True)
    elif name == "sup":
        s = s.update(size=em * SUPSUB_SCALE, shift=s.shift + SUP_SHIFT * em)
    elif name == "sub":
        s = s.update(size=em * SUPSUB_SCALE, shift=s.shift + SUB_SHIFT * em)
    elif name in ("code", "kbd", "tt", "samp"):
        s = s.update(family=MONOSPACE)
    elif name == "small":
        s = s.update(size=em * SMALL_SCALE)
    elif name == "big":
        s = s.update(size=em * BIG_SCALE)
    elif name == "mark":
        s = s.update(background="yellow")
    elif name == "a":
        if "href" in attrs:
            s = s.update(url=attrs["href"])
    elif name == "font":
        if "color" in attrs and (c := parse_color(attrs["color"])) is not None:
            s = s.update(color=c)
        if "face" in attrs:
            s = s.update(family=attrs["face"])
        if "size" in attrs:
            size = parse_length(attrs["size"], em=em)
            if size is not None:
                s = s.update(size=size)
    elif name not in KNOWN_TAGS:
        _warn_once(f"ggtext: unsupported HTML tag <{name}> was ignored")

    # Any tag may carry inline CSS
    if css := attrs.get("style"):
        s = parse_css(css, s)
    return s


# -----------------------------------------------------------------------
# The token builder
# -----------------------------------------------------------------------
class _Builder:
    """Accumulates tokens while tracking a stack of open styles."""

    def __init__(self, base: Style, math_segments: Sequence[str]):
        self.base = base
        self.stack: List[Tuple[str, Style]] = []
        self.tokens: List[Token] = []
        self.math_segments = math_segments

    @property
    def style(self) -> Style:
        return self.stack[-1][1] if self.stack else self.base

    # text ----------------------------------------------------------------
    def text(self, s: str, *, verbatim: bool = False):
        """Add text, restoring any protected math segments."""
        if not s:
            return
        style = self.style
        pos = 0
        for m in _PH_RE.finditer(s):
            if m.start() > pos:
                self._add_text(s[pos : m.start()], style)
            seg = self.math_segments[int(m.group(1))]
            if verbatim:
                self._add_text(seg, style)
            else:
                self.tokens.append(TextRun(seg, style, math=True))
            pos = m.end()
        if pos < len(s):
            self._add_text(s[pos:], style)

    def _add_text(self, s: str, style: Style):
        # Merge with the previous run if the style is the same
        if (
            self.tokens
            and isinstance(prev := self.tokens[-1], TextRun)
            and not prev.math
            and prev.style == style
        ):
            self.tokens[-1] = TextRun(prev.text + s, style)
        else:
            self.tokens.append(TextRun(s, style))

    def line_break(self):
        self.tokens.append(LINE_BREAK)

    # styles --------------------------------------------------------------
    def push(self, key: str, style: Style):
        self.stack.append((key, style))

    def pop(self, key: str):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == key:
                del self.stack[i:]
                return
        if not key.startswith("md:"):
            _warn_once(f"ggtext: closing tag </{key}> has no opening tag")

    # html ----------------------------------------------------------------
    def html_tag(self, raw: str):
        parsed = _parse_tag(raw)
        if parsed is None:  # comments, doctype, ...
            return
        name, attrs, kind = parsed
        if kind == "close":
            if name in ("p", "div"):
                self._paragraph_break()
            if name not in VOID_TAGS:
                self.pop(name)
            return

        if name == "br":
            self.line_break()
        elif name == "img":
            self.image(attrs.get("src", ""), attrs)
        elif name in ("p", "div"):
            self._paragraph_break()
            if kind == "open":
                self.push(name, _style_for_tag(name, attrs, self.style))
        elif name in ("wbr", "hr"):
            pass
        elif kind == "open":
            self.push(name, _style_for_tag(name, attrs, self.style))
        # a self-closed non-void tag (<span/>) has no content: ignore

    def _paragraph_break(self):
        """Start a new line unless we are already at the start of one."""
        if self.tokens and self.tokens[-1] is not LINE_BREAK:
            self.line_break()

    def image(self, src: str, attrs: dict, alt: str = ""):
        style = self.style
        if css := attrs.get("style"):
            style = parse_css(css, style)
        em = style.size if style.size is not None else 10.0
        width = parse_length(attrs.get("width"), em=em) if "width" in attrs else None
        height = parse_length(attrs.get("height"), em=em) if "height" in attrs else None
        # Bare numbers in width/height attributes are CSS pixels
        if "width" in attrs and _is_number(attrs["width"]):
            width = float(attrs["width"]) * 0.75
        if "height" in attrs and _is_number(attrs["height"]):
            height = float(attrs["height"]) * 0.75
        self.tokens.append(
            ImageRun(src, style, width, height, alt or attrs.get("alt", ""))
        )


def _is_number(s: str) -> bool:
    try:
        float(s)
    except (TypeError, ValueError):
        return False
    return True


@lru_cache(maxsize=1)
def _markdown_parser():
    from markdown_it import MarkdownIt

    return MarkdownIt("commonmark", {"html": True}).enable("strikethrough")


_MD_STYLES = {
    "strong_open": ("md:strong", "b"),
    "em_open": ("md:em", "i"),
    "s_open": ("md:s", "s"),
}
_MD_CLOSE = {
    "strong_close": "md:strong",
    "em_close": "md:em",
    "s_close": "md:s",
    "link_close": "md:a",
}


def _split_newlines(b: _Builder, s: str, newline: str):
    """Add text that may contain newline characters."""
    parts = s.split("\n")
    for i, part in enumerate(parts):
        if i:
            if newline == "break":
                b.line_break()
            else:
                b.text(" ")
        b.text(part)


def _parse_markdown(s: str, b: _Builder, newline: str):
    md = _markdown_parser()
    # parseInline returns a single "inline" token holding the children
    blocks = md.parseInline(s)
    children = blocks[0].children if blocks and blocks[0].children else []
    for tok in children:
        t = tok.type
        if t == "text":
            _split_newlines(b, tok.content, newline)
        elif t == "softbreak":
            if newline == "break":
                b.line_break()
            else:
                b.text(" ")
        elif t == "hardbreak":
            b.line_break()
        elif t in _MD_STYLES:
            key, tag = _MD_STYLES[t]
            b.push(key, _style_for_tag(tag, {}, b.style))
        elif t in _MD_CLOSE:
            b.pop(_MD_CLOSE[t])
        elif t == "code_inline":
            b.push("md:code", _style_for_tag("code", {}, b.style))
            b.text(tok.content, verbatim=True)
            b.pop("md:code")
        elif t == "link_open":
            href = tok.attrGet("href") or ""
            b.push("md:a", _style_for_tag("a", {"href": href}, b.style))
        elif t == "image":
            alt = tok.content or ""
            b.image(str(tok.attrGet("src") or ""), {}, alt=alt)
        elif t == "html_inline":
            b.html_tag(tok.content)
        else:  # pragma: no cover - future token types
            _split_newlines(b, tok.content, newline)


def _parse_html(s: str, b: _Builder, newline: str):
    """Parse a string that may contain HTML tags but no markdown."""
    import html

    def unescape(chunk: str) -> str:
        return html.unescape(chunk).replace(r"\$", "$")

    pos = 0
    for m in _HTML_IN_TEXT_RE.finditer(s):
        if m.start() > pos:
            _split_newlines(b, unescape(s[pos : m.start()]), newline)
        b.html_tag(m.group(0))
        pos = m.end()
    if pos < len(s):
        _split_newlines(b, unescape(s[pos:]), newline)


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
    if newline not in ("break", "space"):
        raise ValueError(f"newline must be 'break' or 'space', not {newline!r}")

    if base is None:
        base = Style()
    s = str(s)
    segments: List[str] = []
    if math and s.count("$") - s.count(r"\$") >= 2:
        s, segments = _protect_math(s)

    b = _Builder(base, segments)
    if markdown:
        _parse_markdown(s, b, newline)
    elif html:
        _parse_html(s, b, newline)
    else:
        _split_newlines(b, s.replace(r"\$", "$") if math else s, newline)

    tokens = b.tokens
    # A trailing </p> should not create an empty last line
    if tokens and tokens[-1] is LINE_BREAK and re.search(r"</(p|div)>\s*$", s):
        tokens.pop()
    return tokens


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
