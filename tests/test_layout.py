"""
Tests for the layout algorithm (ggtext._layout) with a fake measurer.

The fake measurer makes every character 0.6 em wide, ascent 0.8 em and
descent 0.2 em. You can compute expected positions by hand.
"""

import pytest

from ggtext._layout import layout_tokens
from ggtext._parse import ImageRun, parse
from ggtext._style import Style

BASE = Style(size=10.0)


class FakeMeasurer:
    def text(self, s, style, math):
        size = style.size
        return 0.6 * size * len(s), 0.8 * size, 0.2 * size

    def font_metrics(self, style):
        return 0.8 * style.size, 0.2 * style.size, 0.1 * style.size

    def image(self, run):
        return (run.width or 10.0), (run.height or 10.0)

    def points_to_pixels(self, points):
        return points


M = FakeMeasurer()


def lay(s, **kwargs):
    return layout_tokens(parse(s, BASE), M, BASE, **kwargs)


def test_single_line():
    L = lay("abcd")
    assert len(L.lines) == 1
    line = L.lines[0]
    assert line.width == pytest.approx(24)
    assert line.ascent == pytest.approx(8) and line.descent == pytest.approx(2)
    assert line.baseline == pytest.approx(-8)
    assert (L.width, L.height) == (pytest.approx(24), pytest.approx(10))
    assert L.descent == pytest.approx(2)


def test_runs_are_placed_side_by_side():
    L = lay("ab**cd**ef")
    xs = [f.x for f in L.lines[0].fragments]
    assert xs == [pytest.approx(0), pytest.approx(12), pytest.approx(24)]


def test_multiple_lines_stack_down():
    # each line: ascent 8 + 0.5 gap, descent 2 + 0.5 gap
    L = lay("ab\ncd\nef")
    assert [ln.baseline for ln in L.lines] == [
        pytest.approx(-8.5), pytest.approx(-19.5), pytest.approx(-30.5)
    ]  # fmt: skip
    assert L.height == pytest.approx(33)


def test_empty_line_keeps_height():
    L = lay("a\n\nb")
    assert len(L.lines) == 3
    assert L.height == pytest.approx(33)


def test_mpl310_linespacing_scales_ascent_of_later_lines():
    L = lay("a\nb", linespacing=1.5, line_model="mpl310")
    assert L.lines[1].baseline == pytest.approx(-8 - 2 - 12)


def test_mpl311_numeric_linespacing_gives_fixed_line_height():
    L = lay("a\nb\nc", linespacing=1.5)
    assert L.height == pytest.approx(3 * 1.5 * 10)


def test_mpl311_normal_linespacing_adds_line_gap_to_multiline():
    assert lay("a").height == pytest.approx(10)
    assert lay("a\nb").height == pytest.approx(2 * (10 + 1))


def test_bigger_font_in_fixed_spacing_does_not_overlap():
    L = lay("a\nb<span style='font-size:30pt'>B</span>", linespacing=1.0)
    assert L.lines[1].ascent >= 24


def test_bigger_font_makes_line_taller():
    L = lay("a<span style='font-size:20pt'>B</span>")
    assert L.lines[0].ascent == pytest.approx(16)
    assert L.lines[0].descent == pytest.approx(4)


def test_superscript_raises_line_ascent():
    L = lay("x<sup>2</sup>")
    sup = L.lines[0].fragments[1]
    assert sup.shift > 0
    assert L.lines[0].ascent >= sup.ascent


@pytest.mark.parametrize(
    "halign, expected", [("left", [0, 0]), ("center", [0, 6]), ("right", [0, 12])]
)
def test_halign(halign, expected):
    L = lay("abcd\nab", halign=halign)
    assert [ln.x for ln in L.lines] == [pytest.approx(v) for v in expected]


def test_wrapping_breaks_at_spaces():
    # "aaa bbb ccc" with 6px per char; wrap at 45px fits "aaa bbb" (42px)
    L = lay("aaa bbb ccc", wrap_width=45)
    assert [ln.text for ln in L.lines] == ["aaa bbb", "ccc"]


def test_wrapping_keeps_styles_and_merges_runs():
    L = lay("aaa **bbb ccc** ddd", wrap_width=45)
    assert [ln.text for ln in L.lines] == ["aaa bbb", "ccc ddd"]
    first = L.lines[0].fragments
    assert [f.run.style.weight for f in first] == [None, "bold"]
    # "aaa " merges into a single fragment
    assert first[0].run.text == "aaa "


def test_long_word_overflows_on_its_own_line():
    L = lay("a verylongword b", wrap_width=30)
    assert [ln.text for ln in L.lines] == ["a", "verylongword", "b"]


def test_explicit_breaks_with_wrapping():
    L = lay("aaa bbb\nccc", wrap_width=100)
    assert [ln.text for ln in L.lines] == ["aaa bbb", "ccc"]


def test_math_is_never_split():
    tokens = parse("$a b c d$ e", BASE)
    L = layout_tokens(tokens, M, BASE, wrap_width=10)
    assert L.lines[0].text == "$a b c d$"


def test_padding_and_box_width():
    L = lay("ab", padding=(1, 2, 3, 4), box_width=50)
    assert L.width == pytest.approx(50)
    assert L.height == pytest.approx(10 + 1 + 3)
    assert L.lines[0].x == pytest.approx(4)
    assert L.lines[0].baseline == pytest.approx(-1 - 8)


def test_box_width_with_center_align():
    L = lay("ab", box_width=50, padding=(0, 5, 0, 5), halign="center")
    # inner width 40, text 12 -> starts at 5 + 14
    assert L.lines[0].x == pytest.approx(19)


@pytest.mark.parametrize("valign, top", [("top", 0), ("center", 15), ("bottom", 30)])
def test_valign_in_tall_box(valign, top):
    L = lay("ab", box_height=40, valign=valign)
    assert L.height == pytest.approx(40)
    assert L.lines[0].baseline == pytest.approx(-top - 8)


def test_box_height_smaller_than_content_overflows():
    L = lay("ab", box_height=4)
    assert L.height == pytest.approx(4)
    assert L.lines[0].baseline == pytest.approx(-8)  # top aligned, overflows


def test_margin_is_outside_the_box():
    L = lay("ab", padding=(1, 1, 1, 1), margin=(2, 3, 4, 5))
    assert L.width == pytest.approx(12 + 2 + 3 + 5)
    assert L.height == pytest.approx(10 + 2 + 2 + 4)
    assert L.box == (
        pytest.approx(5),
        pytest.approx(-18 + 4),
        pytest.approx(14),
        pytest.approx(12),
    )
    assert L.lines[0].x == pytest.approx(5 + 1)
    assert L.lines[0].baseline == pytest.approx(-2 - 1 - 8)


def test_images_sit_on_baseline():
    tokens = [ImageRun("x.png", BASE, width=20, height=15)]
    L = layout_tokens(tokens, M, BASE)
    f = L.lines[0].fragments[0]
    assert f.width == 20 and f.ascent == 15 and f.descent == 0
    assert L.lines[0].ascent == pytest.approx(15)


def test_empty_input():
    L = layout_tokens([], M, BASE)
    assert len(L.lines) == 1 and L.width == 0
    assert L.height == pytest.approx(10)


def test_spaces_at_wrap_points_are_dropped():
    L = lay("aa   bb", wrap_width=15)
    assert [ln.text for ln in L.lines] == ["aa", "bb"]


def test_non_breaking_space_keeps_words_together():
    L = lay("aaa&nbsp;bbb ccc", wrap_width=30)
    assert [ln.text for ln in L.lines] == ["aaa\xa0bbb", "ccc"]
