"""
Golden test: ggIR + the adapter give the tokens ggtext's own parser gave.

Parsing moved to ggIR (``ggir.parse`` builds a document tree) and
``ggtext._ir.tokens_from_document`` resolves the tree into tokens. This
test runs both on a large corpus, under every option combination and
with bases with and without a size, and asserts the token lists are
equal. The old parser is frozen in ``tests/_legacy_parse.py``.

Inputs where the new pipeline deliberately differs (ggIR is more
correct) are listed in ``EXPECTED_DIFFERENCES`` with the new output.
"""

from __future__ import annotations

import ast
import itertools
import json
import re
import warnings
from pathlib import Path

import ggir
import ggir.css
import ggir.ir
import pytest

from ggtext import _ir
from ggtext._ir import tokens_from_document
from ggtext._parse import LINE_BREAK, TextRun
from ggtext._style import Style

from . import _legacy_parse

ROOT = Path(__file__).resolve().parents[1]

BASES = {
    "sized": Style(family=("sans-serif",), size=12.0, color="black"),
    "unsized": Style(),
}

# Hand-written edge cases, on top of every string found in the repo
EDGE_CASES = [
    "",
    " ",
    "\n",
    "\n\n",
    "a\n\nb",
    "a  \nb",
    "a\\\nb",
    "trailing  ",
    "\xa0x\xa0",
    "&nbsp;&amp;&lt;&gt;&bull;&#36;&quot;",
    # markdown
    "**a** **b**",
    "**a**b**c**",
    "***x*** __y__ _z_",
    "*a **b** c*",
    "**unclosed",
    "~~s~~ ~single~",
    "`code` and ``co`de``",
    "`$x$` and $`y`$",
    "[link](http://x.org) [empty]() [**bold link**](u)",
    "[a](u1)[b](u1)",
    "![alt](img.png) ![](b.png) ![a *b*](c.png)",
    "<http://autolink.org>",
    "\\*esc\\* \\_ \\$ \\\\",
    "# heading",
    "- item\n- item",
    "> quote",
    "1. one\n2. two",
    "line one\nline two\nline three",
    # math
    "$x$",
    "$x$$y$",
    "$a_1 * b_2$ and *c*",
    "price $5 and $6",
    "\\$5 and \\$6",
    "$x\\$y$",
    "$",
    "$$",
    "$ $",
    "**$x^2$**",
    "<b>$x$</b>",
    "<code>$x$</code>",
    "`a $b$ c`",
    "$x$\n$y$",
    # html
    "<b>a</b><b>b</b>",
    "<b>a</b><i>b</i>",
    "<B>upper</B>",
    "<b >spaced</ b>",
    "<span>plain</span>",
    "<span/>",
    "<b><i>x</b>y</i>z",
    "</b>stray",
    "<blink>x</blink>",
    "<!-- c -->x<!-- d -->",
    "a<br>b<br/>c<br />d<BR>",
    "<br>",
    "<br><br>",
    "a<wbr>b<hr>c",
    "x<sup>2</sup>",
    "x<sub>i</sub>",
    "e<sup>x<sup>2</sup></sup>",
    "a<sub>b<sup>c</sup></sub>",
    "<small>s</small> <big>b</big> <small><small>ss</small></small>",
    "<big><sup>x</sup></big>",
    "<sup><small>x</small></sup>",
    "<mark>m</mark>",
    "<a href='u'>link</a> <a>no href</a> <a href=''>empty</a>",
    '<a href="http://x.org/?a=1&amp;b=2">q</a>',
    "<code>c</code><kbd>k</kbd><tt>t</tt><samp>s</samp>",
    "<u>u</u><ins>i</ins><s>s</s><del>d</del><strike>st</strike>",
    "<font color='red' face='serif' size='14'>f</font>",
    "<font color='nocolorxyz'>bad</font>",
    "<font color=''>empty</font>",
    "<font face='Arial, \"DejaVu Sans\", sans-serif'>f</font>",
    "<font size='2em'>f</font> <font size='large'>l</font> <font size=12>n</font>",
    "<font size='bogus'>f</font>",
    # css
    "<span style='color:red'>r</span>",
    "<span style='color: rgb(255, 0, 0)'>r</span>",
    "<span style='color: rgba(0,0,255,0.5)'>r</span>",
    "<span style='color: rgb(100%, 50%, 0%)'>r</span>",
    "<span style='color: rgb(1,2)'>bad</span>",
    "<span style='color: nocolorxyz'>bad</span>",
    "<span style='color: #ff0000; color: C1'>two</span>",
    "<span style='color:tab:blue'>tab</span>",
    "<span style='color: 0.5'>gray</span>",
    "<span style='background-color: yellow'>bg</span>",
    "<span style='background: nocolorxyz'>bad bg</span>",
    "<span style='font-size: 14pt'>a</span>",
    "<span style='font-size: 20px'>a</span>",
    "<span style='font-size: 1in'>a</span>",
    "<span style='font-size: 150%'>a</span>",
    "<span style='font-size: 2em'>a</span>",
    "<span style='font-size: 2rem'>a</span>",
    "<span style='font-size: x-large'>a</span>",
    "<span style='font-size: larger'>a</span>",
    "<span style='font-size: smaller'>a</span>",
    "<span style='font-size: hugeish'>a</span>",
    "<span style='font-size: 2em'><span style='font-size: 50%'>a</span></span>",
    "<span style='font-family: \"DejaVu Serif\", serif'>a</span>",
    "<span style='font-family: monospace'>a</span>",
    "<span style='font-weight: 700'>a</span>",
    "<span style='font-weight: bold'>a</span><b>b</b>",
    "<span style='font-style: italic'>a</span>",
    "<span style='font-variant: small-caps'>a</span>",
    "<span style='text-decoration: underline line-through'>a</span>",
    "<u><span style='text-decoration: none'>a</span></u>",
    "<span style='vertical-align: super'>a</span>",
    "<span style='vertical-align: sup'>a</span>",
    "<span style='vertical-align: sub'>a</span>",
    "<span style='vertical-align: 3pt'>a</span>",
    "<span style='vertical-align: -0.5em'>a</span>",
    "<span style='vertical-align: 20%'>a</span>",
    "<span style='vertical-align: bogus'>a</span>",
    "<sup><span style='vertical-align: baseline'>a</span></sup>",
    "<sup style='vertical-align: super'>a</sup>",
    "<sup style='font-size: 2em'>a</sup>",
    "<sub style='font-size: 14pt; vertical-align: 1em'>a</sub>",
    "<span style='font-size: 20pt; vertical-align: super'>a</span>",
    "<span style='color: blue !important ;; '>a</span>",
    "<span style='margin-q: 3px'>a</span>",
    "<span style=''>a</span>",
    "<span style='color'>a</span>",
    "<b style='color:red'>x</b>",
    "<span style=color:red>unquoted</span>",
    '<span style="color:red">double</span>',
    "<span style='color:red'>a</span><span style='color:red'>b</span>",
    "<span style='color:red'>**a** $x$ `c`</span>",
    "<span style='font-size:20pt'>a <sup>2</sup> <small>s</small></span>",
    # paragraphs
    "<p>one</p><p>two</p>",
    "<p>one</p>",
    "<p>one</p>  ",
    "<p>one</p>\n",
    "<p>one</p>\ntwo",
    "a<p>b</p>c",
    "a<p></p>b",
    "<p></p>",
    "<p>a<br></p>b",
    "<div>a</div><div>b</div>",
    "<div>a<p>b</p>c</div>",
    "<p style='color:red'>a</p>b",
    "<p style='font-size:20pt'>a<sup>2</sup></p>",
    "<p><b>a</p>b</b>c",
    "<b><p>a</p>b</b>",
    "<p>a<p>b</p>c</p>d",
    "<p>a</p>\n\n<p>b</p>",
    "x<br><p>a</p>",
    # images
    "<img src='logo.png'>",
    "<img src='logo.png' width='20' height='10pt' alt='logo'>",
    "<img src='a.png' width='2em' height='50%'>",
    "<img src='a.png' width='small' height='bogus'>",
    "<img src='a.png' width='' height=''>",
    "<img src='a.png' style='font-size:20pt' width='2em'>",
    "<img src='a.png' style='vertical-align:-2pt; color:red'>",
    "<img src='a.png'/>",
    "<img>",
    "text <img src='a.png'> text",
    "<span style='font-size:20pt'><img src='a.png' width='1em'></span>",
    "<sup><img src='a.png' height='1em'></sup>",
    "<img src='a.png'><img src='b.png'>",
    # mixed / messy
    "<b>**both**</b>",
    "**<i>x</i>**",
    "**a <i>b** c</i>",
    "5 < 6 and 7 > 3",
    "a <3 b",
    "<<b>>x",
    "< b>x</b>",
    "<b\nclass='x'>multi\nline tag</b>",
    "<span style='color:red'>a\nb</span>",
    "a\n<br>\nb",
    "x\n\n<p>y</p>\n",
]

# Expected differences: (input, options, new output with the sized base).
# Each is a case where ggIR's tree is more correct than the old parser.
# The options are a subset: the input is exempt from the corpus check
# under every combination that includes them, and checked under the
# defaults plus these options below.
_S = BASES["sized"]
_LITERAL = {"markdown": False, "html": False, "newline": "break"}

EXPECTED_DIFFERENCES: list[tuple[str, dict, list]] = [
    # A self-closed <p/> is empty: it no longer starts a new line.
    ("a<p/>b", {}, [TextRun("ab", _S)]),
    # A stray </p> with no opening <p> no longer starts a new line.
    ("a</p>b", {}, [TextRun("ab", _S)]),
    # A trailing paragraph leaves no empty last line even when an inline
    # tag closes after it (the old parser only looked for a literal
    # "</p>" at the end of the string) ...
    ("<b><p>a</p></b>", {}, [TextRun("a", _S.update(weight="bold"))]),
    # ... or when the <p> is never closed.
    ("<p>a<br>", {}, [TextRun("a", _S)]),
    # With markup off, a literal "</p>" at the end no longer swallows the
    # final newline (the old parser checked the raw string for "</p>").
    ("<p>one</p>\n", _LITERAL, [TextRun("<p>one</p>", _S), LINE_BREAK]),
    (
        "x\n\n<p>y</p>\n",
        _LITERAL,
        [TextRun("x", _S), LINE_BREAK, LINE_BREAK, TextRun("<p>y</p>", _S), LINE_BREAK],
    ),
    # An empty face='' is ignored instead of setting an empty family.
    ("<font face=''>x</font>", {}, [TextRun("x", _S)]),
    # CSS vertical-align does not apply to block elements.
    ("<p style='vertical-align:super'>x</p>", {}, [TextRun("x", _S)]),
    # CSS font-size on <small>/<big>/<font> is relative to the parent,
    # as in CSS, not to the tag's own size (ggIR keeps one size per node).
    (
        "<small style='font-size:2em'>x</small>",
        {},
        [TextRun("x", _S.update(size=24.0))],
    ),
]


def _is_expected_difference(s: str, options: dict) -> bool:
    return any(
        s == e and all(options[k] == v for k, v in when.items())
        for e, when, _ in EXPECTED_DIFFERENCES
    )


# -----------------------------------------------------------------------
# The corpus
# -----------------------------------------------------------------------
def _python_strings(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    return [
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    ]


def _markdown_strings(text: str) -> list[str]:
    out = []
    # fenced code: Python strings if it parses, else every line
    for block in re.findall(r"```[^\n]*\n(.*?)```", text, re.DOTALL):
        strings = _python_strings(block)
        out.extend(strings if strings else block.splitlines())
    prose = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    # inline code (``x`` and `x`)
    out.extend(m[1] or m[2] for m in re.finditer(r"``\s?(.+?)\s?``|`([^`\n]+)`", prose))
    return out


def _repo_strings() -> list[str]:
    strings: list[str] = []
    for path in sorted((ROOT / "tests").glob("*.py")):
        if path.name != "_legacy_parse.py":
            strings += _python_strings(path.read_text(encoding="utf-8"))
    for path in sorted((ROOT / "examples").glob("*.py")):
        strings += _python_strings(path.read_text(encoding="utf-8"))
    for path in sorted((ROOT / "examples").glob("*.ipynb")):
        nb = json.loads(path.read_text(encoding="utf-8"))
        for cell in nb.get("cells", []):
            src = "".join(cell.get("source", []))
            if cell.get("cell_type") == "code":
                strings += _python_strings(src)
            else:
                strings += _markdown_strings(src)
    for path in sorted((ROOT / "docs").glob("*.md")) + [ROOT / "README.md"]:
        strings += _markdown_strings(path.read_text(encoding="utf-8"))
    return strings


def _corpus() -> list[str]:
    seen: dict[str, None] = {}
    for s in EDGE_CASES + _repo_strings():
        if len(s) <= 5000:
            seen.setdefault(s, None)
    return list(seen)


CORPUS = _corpus()

OPTIONS_DEFAULT = dict(markdown=True, html=True, math=True, newline="break")
OPTIONS = [
    dict(markdown=md, html=h, math=m, newline=nl)
    for md, h, m, nl in itertools.product(
        (True, False), (True, False), (True, False), ("break", "space")
    )
]


def _new(s: str, base: Style, **options) -> list:
    return tokens_from_document(ggir.parse(s, **options), base)


def _show(tokens) -> list:
    return [
        t if t is LINE_BREAK else (type(t).__name__, getattr(t, "text", None), t)
        for t in tokens
    ]


@pytest.fixture(autouse=True)
def _keep_warn_once_state():
    """
    Parsing the corpus would use up the warn-once messages that other
    tests check for (e.g. ``<blink>``), so restore them afterwards.
    """
    sets = [ggir.ir._warned, ggir.css._warned, _ir._warned]
    saved = [set(s) for s in sets]
    yield
    for s, old in zip(sets, saved, strict=True):
        s.clear()
        s.update(old)


def test_corpus_is_large():
    assert len(CORPUS) > 1000


@pytest.mark.parametrize("base_name", list(BASES))
@pytest.mark.parametrize(
    "options", OPTIONS, ids=lambda o: "-".join(f"{k}={v}" for k, v in o.items())
)
def test_same_tokens_as_legacy_parser(options, base_name):
    base = BASES[base_name]
    failures = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for s in CORPUS:
            if _is_expected_difference(s, options):
                continue
            old = _legacy_parse.parse(s, base, **options)
            new = _new(s, base, **options)
            if old != new:
                failures.append((s, _show(old), _show(new)))
    assert not failures, (
        f"{len(failures)} of {len(CORPUS)} inputs differ; first:\n"
        + "\n".join(f"{s!r}\n  old: {o}\n  new: {n}" for s, o, n in failures[:5])
    )


@pytest.mark.parametrize(
    "s, when, expected",
    EXPECTED_DIFFERENCES,
    ids=[repr(s) for s, *_ in EXPECTED_DIFFERENCES],
)
def test_expected_differences(s, when, expected):
    options = {**OPTIONS_DEFAULT, **when}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        old = _legacy_parse.parse(s, _S, **options)
        new = _new(s, _S, **options)
    assert new == expected
    assert old != new  # still a real difference, else delete the entry
