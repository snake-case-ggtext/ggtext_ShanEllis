"""Tests for styles and the CSS subset (parsed by ggIR, resolved by ggtext)."""

import pytest

from ggtext._parse import parse
from ggtext._spec import parse_length
from ggtext._style import Style, parse_color


def css(declarations: str, base: Style) -> Style:
    """The style inside a span with inline CSS *declarations*."""
    (run,) = parse(f'<span style="{declarations}">x</span>', base)
    return run.style


class TestParseLength:
    """Absolute lengths (``ggtext._spec.parse_length``) in points."""

    @pytest.mark.parametrize(
        "value, expected",
        [
            (12, 12.0),
            (7.5, 7.5),
            ("12", 12.0),
            ("12pt", 12.0),
            ("16px", 12.0),  # CSS px are 0.75pt
            ("1in", 72.0),
            ("2.54cm", 72.0),
            ("25.4mm", 72.0),
            ("1pc", 12.0),
            (" 3 pt ", 3.0),
        ],
    )
    def test_absolute(self, value, expected):
        assert parse_length(value) == pytest.approx(expected)

    @pytest.mark.parametrize(
        "value, expected",
        [("1.5em", 15.0), ("150%", 15.0), ("larger", 12.0), ("smaller", 8.33),
         ("x-large", 14.4), ("medium", 10.0)],
    )  # fmt: skip
    def test_relative(self, value, expected):
        size = css(f"font-size: {value}", Style(size=10.0)).size
        assert size == pytest.approx(expected, abs=0.01)

    def test_relative_without_em_is_none(self):
        assert parse_length("1.5em") is None
        assert parse_length("50%") is None

    def test_invalid(self):
        assert parse_length("big") is None
        assert parse_length(None) is None
        assert parse_length("12furlongs") is None

    def test_percent_can_be_disallowed(self):
        assert parse_length("50%", allow_percent=False) is None


class TestParseColor:
    @pytest.mark.parametrize("c", ["red", "#ff0000", "#f00", "C0", "tab:blue", "0.5"])
    def test_matplotlib_colors(self, c):
        assert parse_color(c) == c

    def test_css_rgb(self):
        assert parse_color("rgb(255, 0, 0)") == (1.0, 0.0, 0.0)
        assert parse_color("rgba(0,0,255,0.5)") == (0.0, 0.0, 1.0, 0.5)
        assert parse_color("rgb(100%, 50%, 0%)") == (1.0, 0.5, 0.0)

    def test_invalid(self):
        assert parse_color("notacolor") is None
        assert parse_color("rgb(1,2)") is None
        assert parse_color("rgb(a,b,c)") is None


class TestParseCss:
    base = Style(size=10.0, color="black")

    def test_color_and_size(self):
        s = css("color: red; font-size: 14pt", self.base)
        assert s.color == "red"
        assert s.size == 14.0

    def test_relative_font_size(self):
        assert css("font-size: 150%", self.base).size == 15.0
        assert css("font-size: 2em", self.base).size == 20.0

    def test_font_properties(self):
        s = css(
            "font-family: 'DejaVu Serif', serif; font-weight: bold; "
            "font-style: italic; font-variant: small-caps",
            self.base,
        )
        assert s.family == ("DejaVu Serif", "serif")
        assert s.weight == "bold"
        assert s.style == "italic"
        assert s.variant == "small-caps"

    def test_numeric_weight(self):
        assert css("font-weight: 700", self.base).weight == 700

    def test_background_and_decorations(self):
        s = css(
            "background-color: yellow; text-decoration: underline line-through",
            self.base,
        )
        assert s.background == "yellow"
        assert s.underline and s.strike
        s2 = css("text-decoration: none", s)
        assert not s2.underline and not s2.strike

    def test_vertical_align(self):
        assert css("vertical-align: super", self.base).shift > 0
        assert css("vertical-align: sub", self.base).shift < 0
        assert css("vertical-align: 3pt", self.base).shift == 3.0
        up = css("vertical-align: super", self.base)
        assert css("vertical-align: baseline", up).shift == 0

    def test_important_and_whitespace(self):
        s = css("  color : blue !important ;; ", self.base)
        assert s.color == "blue"

    def test_unknown_property_warns_once(self):
        with pytest.warns(UserWarning, match="unsupported CSS property 'margin-q'"):
            css("margin-q: 3px", self.base)

    def test_invalid_values_warn(self):
        with pytest.warns(UserWarning, match="invalid color"):
            s = css("color: nocolorxyz", self.base)
        assert s.color == "black"
        with pytest.warns(UserWarning, match="invalid font-size"):
            css("font-size: hugeish", self.base)

    def test_no_changes_returns_same_object(self):
        assert css("", self.base) is self.base


class TestStyle:
    def test_update_splits_family_string(self):
        s = Style().update(family="Arial, sans-serif")
        assert s.family == ("Arial", "sans-serif")

    def test_resolve(self):
        base = Style(family=("serif",), size=12, weight="normal", color="k")
        s = Style(weight="bold").resolve(base)
        assert s.size == 12 and s.weight == "bold" and s.family == ("serif",)

    def test_fontproperties_roundtrip(self):
        s = Style(family=("monospace",), size=9, weight="bold", style="italic")
        fp = s.fontproperties()
        assert fp.get_size_in_points() == 9
        assert fp.get_weight() in ("bold", 700)
        back = Style.from_fontproperties(fp)
        assert back.size == 9 and back.style == "italic"

    def test_hashable(self):
        assert hash(Style(size=1)) == hash(Style(size=1))
