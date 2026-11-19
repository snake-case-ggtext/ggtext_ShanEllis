"""Tests for the Markdown/HTML parser (ggtext._parse)."""

import pytest

from ggtext._parse import LINE_BREAK, ImageRun, TextRun, parse, plain_text
from ggtext._style import Style

BASE = Style(family=("sans-serif",), size=10.0, color="black")


def runs(s, **kwargs):
    return parse(s, BASE, **kwargs)


def texts(tokens):
    return [t.text if isinstance(t, TextRun) else t for t in tokens]


class TestMarkdown:
    def test_plain(self):
        (t,) = runs("Hello world")
        assert t.text == "Hello world" and t.style == BASE

    @pytest.mark.parametrize(
        "src", ["**bold**", "__bold__", "<b>bold</b>", "<strong>bold</strong>"]
    )
    def test_bold(self, src):
        (t,) = runs(src)
        assert t.text == "bold" and t.style.weight == "bold"

    @pytest.mark.parametrize("src", ["*it*", "_it_", "<i>it</i>", "<em>it</em>"])
    def test_italic(self, src):
        (t,) = runs(src)
        assert t.text == "it" and t.style.style == "italic"

    def test_bold_italic(self):
        (t,) = runs("***both***")
        assert t.style.weight == "bold" and t.style.style == "italic"

    def test_strikethrough(self):
        (t,) = runs("~~gone~~")
        assert t.style.strike

    def test_code_span_is_verbatim_and_monospace(self):
        (t,) = runs("`a_b*c* $x$`")
        assert t.text == "a_b*c* $x$"
        assert t.style.family == ("monospace",)
        assert not t.math

    @pytest.mark.parametrize(
        "src",
        [
            "bill_length_mm",
            "flipper_length_mm vs body_mass_g",
            "snake_case_name",
            "x_1 and y_2",
        ],
    )
    def test_snake_case_is_not_italic(self, src):
        tokens = runs(src)
        assert plain_text(tokens) == src
        assert all(t.style.style is None and t.style.weight is None for t in tokens)

    def test_dunder_gotcha_and_fixes(self):
        # CommonMark reads __init__ as bold "init" (documented gotcha) ...
        assert runs("__init__")[0].style.weight == "bold"
        # ... use backticks or escapes to keep it literal
        assert plain_text(runs("`__init__`")) == "__init__"
        assert plain_text(runs(r"\_\_init\_\_")) == "__init__"

    def test_escapes_and_entities(self):
        assert (
            plain_text(runs(r"\*not italic\* &amp; &lt;tag&gt;"))
            == "*not italic* & <tag>"
        )

    def test_lists_and_headings_are_literal(self):
        assert plain_text(runs("1. one")) == "1. one"
        assert plain_text(runs("# hash")) == "# hash"

    def test_link_keeps_text_and_url(self):
        (t,) = runs("[docs](https://example.org)")
        assert t.text == "docs" and t.style.url == "https://example.org"

    def test_image_markdown(self):
        (img,) = runs("![a flag](flag.png)")
        assert isinstance(img, ImageRun)
        assert img.src == "flag.png" and img.alt == "a flag"

    def test_markdown_disabled(self):
        (t,) = runs("**not bold** <b>bold</b>", markdown=False)[:1]
        assert t.text == "**not bold** "
        assert runs("**x** <b>y</b>", markdown=False)[1].style.weight == "bold"

    def test_markdown_and_html_disabled(self):
        (t,) = runs("**x** <b>y</b>", markdown=False, html=False)
        assert t.text == "**x** <b>y</b>"


class TestLineBreaks:
    def test_newline_breaks_by_default(self):
        assert texts(runs("a\nb")) == ["a", LINE_BREAK, "b"]

    def test_newline_as_space(self):
        assert plain_text(runs("a\nb", newline="space")) == "a b"

    def test_br_and_hard_break(self):
        assert texts(runs("a<br>b<br/>c")) == ["a", LINE_BREAK, "b", LINE_BREAK, "c"]
        assert texts(runs("a  \nb", newline="space")) == ["a", LINE_BREAK, "b"]

    def test_paragraphs(self):
        assert texts(runs("<p>one</p><p>two</p>")) == ["one", LINE_BREAK, "two"]

    def test_newline_in_html_mode(self):
        assert texts(runs("a\nb", markdown=False)) == ["a", LINE_BREAK, "b"]
        assert plain_text(runs("a\nb", markdown=False, newline="space")) == "a b"

    def test_bad_newline_value(self):
        with pytest.raises(ValueError, match="newline"):
            runs("x", newline="wrap")


class TestHtml:
    def test_span_style(self):
        _, t, _ = runs("a <span style='color:red; font-size:15pt'>b</span> c")
        assert t.style.color == "red" and t.style.size == 15

    def test_nesting(self):
        tokens = runs("<b>bold <i>both</i> bold</b> plain")
        assert texts(tokens) == ["bold ", "both", " bold", " plain"]
        assert tokens[1].style.weight == "bold" and tokens[1].style.style == "italic"
        assert tokens[2].style.style is None
        assert tokens[3].style.weight is None

    def test_markdown_inside_html(self):
        tokens = runs("<span style='color:blue'>**x**</span>")
        assert tokens[0].style.color == "blue" and tokens[0].style.weight == "bold"

    def test_sup_sub(self):
        _x, sup, h, sub = runs("x<sup>2</sup>H<sub>2</sub>")[:4]
        assert sup.style.size < 10 and sup.style.shift > 0
        assert sub.style.size < 10 and sub.style.shift < 0
        assert h.style.shift == 0

    def test_nested_sup_accumulates(self):
        tokens = runs("e<sup>x<sup>2</sup></sup>")
        assert tokens[2].style.shift > tokens[1].style.shift > 0

    @pytest.mark.parametrize(
        "tag, attr, value",
        [
            ("u", "underline", True),
            ("ins", "underline", True),
            ("s", "strike", True),
            ("del", "strike", True),
            ("mark", "background", "yellow"),
            ("code", "family", ("monospace",)),
            ("kbd", "family", ("monospace",)),
        ],
    )
    def test_simple_tags(self, tag, attr, value):
        (t,) = runs(f"<{tag}>x</{tag}>")
        assert getattr(t.style, attr) == value

    def test_small_big(self):
        assert runs("<small>s</small>")[0].style.size < 10
        assert runs("<big>b</big>")[0].style.size > 10

    def test_font_tag(self):
        (t,) = runs("<font color='green' face='serif' size='14'>x</font>")
        assert t.style.color == "green" and t.style.family == ("serif",)
        assert t.style.size == 14

    def test_style_attribute_on_any_tag(self):
        (t,) = runs("<b style='color:red'>x</b>")
        assert t.style.weight == "bold" and t.style.color == "red"

    def test_unclosed_tag_extends_to_end(self):
        (t,) = runs("<b>to the end")
        assert t.style.weight == "bold"

    def test_mismatched_close_warns(self):
        with pytest.warns(UserWarning, match="has no opening tag"):
            runs("text</zzz>")

    def test_close_pops_intermediate(self):
        tokens = runs("<b><i>x</b>y")
        assert tokens[1].style.weight is None and tokens[1].style.style is None

    def test_unknown_tag_warns(self):
        with pytest.warns(UserWarning, match="unsupported HTML tag <blink>"):
            (t,) = runs("<blink>x</blink>")
        assert t.text == "x"

    def test_comments_are_ignored(self):
        assert plain_text(runs("a<!-- hidden -->b")) == "ab"

    def test_img(self):
        (img,) = runs("<img src='logo.png' width='20' height='10pt' alt='logo'>")
        assert img.src == "logo.png"
        assert img.width == 15.0  # 20 CSS px
        assert img.height == 10.0
        assert img.alt == "logo"

    def test_less_than_is_text(self):
        assert plain_text(runs("5 < 6 and 7 > 3")) == "5 < 6 and 7 > 3"


class TestMath:
    def test_math_segment(self):
        tokens = runs(r"The $\alpha_1 * \beta$ value")
        assert texts(tokens) == ["The ", r"$\alpha_1 * \beta$", " value"]
        assert tokens[1].math

    def test_multiple_math(self):
        tokens = runs("$a$ and $b$")
        assert [t.math for t in tokens] == [True, False, True]

    def test_escaped_dollar(self):
        assert plain_text(runs(r"costs \$5")) == "costs $5"
        assert plain_text(runs(r"costs \$5", markdown=False)) == "costs $5"

    def test_single_dollar_is_text(self):
        (t,) = runs("only $5")
        assert not t.math and t.text == "only $5"

    def test_math_disabled(self):
        tokens = runs("$x$", math=False)
        assert not any(t.math for t in tokens)

    def test_math_keeps_style(self):
        _, t = runs("<span style='color:red'>a $x$</span>")
        assert t.math and t.style.color == "red"


def test_runs_with_same_style_are_merged():
    tokens = runs("a&amp;b")
    assert len(tokens) == 1


def test_plain_text_roundtrip():
    s = "**Bold** <span style='color:red'>red</span>\nline 2 ![alt](x.png)"
    assert plain_text(runs(s)) == "Bold red\nline 2 alt"


def test_line_break_singleton():
    from ggtext._parse import LineBreak

    assert LineBreak() is LINE_BREAK
    assert repr(LINE_BREAK) == "LINE_BREAK"
