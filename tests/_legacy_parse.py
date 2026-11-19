"""
A frozen copy of ggtext's own parser, from before parsing moved to ggIR.

Used only by ``test_ir_adapter.py`` as the reference ("golden") output
for ``tokens_from_document(ggir.parse(...))``. Do not edit: it records
the legacy behaviour. It produces the same token classes as ggtext, so the
two outputs compare equal with ``==``.
"""

# ruff: noqa

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass, field, replace
from functools import lru_cache
from typing import Any, List, Sequence, Tuple

from matplotlib.colors import to_rgba

from ggtext._parse import LINE_BREAK, ImageRun, TextRun, Token
from ggtext._style import Style

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
        Whether to accept percentages.

    Returns
    -------
    float or None
        The length in points, or ``None`` if the parser rejects the value.
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

    Supports every color format matplotlib accepts. It also supports CSS
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
    ``line-through``, ``none``). ``vertical-align`` takes ``super``,
    ``sub``, ``baseline`` or a length.

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


MONOSPACE = ("monospace",)


# -----------------------------------------------------------------------
# Math protection
# -----------------------------------------------------------------------
# The markdown parser must not touch mathtext segments
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
        """Start another line unless we are already at the start of one."""
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
        Interpret Markdown syntax. If False, the parser handles only HTML.
    html :
        Interpret HTML tags. Only applies when ``markdown=False``;
        with markdown the HTML tags are always recognized.
        If both are False, the parser returns the text as a single run.
    math :
        Treat ``$...$`` segments as matplotlib mathtext.
    newline :
        What a newline character (``"\\n"``) means: ``"break"`` (the
        default, as in matplotlib) starts another line. ``"space"``
        treats it as a space, as in Markdown/HTML. Use ``<br>`` or two
        trailing spaces for a break.

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
