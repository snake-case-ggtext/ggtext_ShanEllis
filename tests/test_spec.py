"""Tests for RichTextSpec and length resolution (ggtext._spec)."""

import pytest

from ggtext import RichTextSpec
from ggtext._spec import resolve_length


class TestCoerce:
    def test_true_gives_defaults(self):
        assert RichTextSpec.coerce(True) == RichTextSpec()

    @pytest.mark.parametrize("value", [None, False])
    def test_falsy_gives_none(self, value):
        assert RichTextSpec.coerce(value) is None

    def test_dict(self):
        spec = RichTextSpec.coerce({"fill": "red", "padding": 3})
        assert spec.fill == "red" and spec.padding == (3.0,) * 4

    def test_spec_passthrough(self):
        s = RichTextSpec(r=2)
        assert RichTextSpec.coerce(s) is s

    def test_bad_type(self):
        with pytest.raises(TypeError, match="richtext must be"):
            RichTextSpec.coerce("yes")

    def test_unknown_option(self):
        with pytest.raises(TypeError, match="Unknown rich text option 'colour'"):
            RichTextSpec.coerce({"colour": "red"})

    @pytest.mark.parametrize(
        "alias, field",
        [("box_colour", "box_color"), ("box.colour", "box_color"),
         ("box.color", "box_color"), ("linetype", "linestyle"), ("radius", "r")],
    )  # fmt: skip
    def test_ggplot2_aliases(self, alias, field):
        spec = RichTextSpec.coerce({alias: "dashed" if field == "linestyle" else 1})
        assert getattr(spec, field) in ("dashed", 1)


class TestPadding:
    @pytest.mark.parametrize(
        "value, expected",
        [
            (None, (0, 0, 0, 0)),
            (4, (4, 4, 4, 4)),
            ("6pt", (6, 6, 6, 6)),
            ((1, 2), (1, 2, 1, 2)),
            ((1, 2, 3, 4), (1, 2, 3, 4)),
            ([5], (5, 5, 5, 5)),
            ({"t": 1, "l": 4}, (1, 0, 0, 4)),
        ],
    )
    def test_forms(self, value, expected):
        assert RichTextSpec(padding=value).padding == tuple(map(float, expected))

    def test_bad_length(self):
        with pytest.raises(ValueError, match="padding must have"):
            RichTextSpec(padding=(1, 2, 3))


class TestValidation:
    @pytest.mark.parametrize(
        "kwargs, match",
        [
            ({"newline": "wrap"}, "newline"),
            ({"halign": "middle"}, "halign"),
            ({"valign": "middle"}, "valign"),
            ({"width": 2}, "fractions of the available space"),
            ({"width": 0}, "fractions"),
            ({"height": -0.5}, "fractions"),
            ({"maxwidth": "lots"}, "Could not understand maxwidth"),
        ],
    )
    def test_errors(self, kwargs, match):
        with pytest.raises(ValueError, match=match):
            RichTextSpec(**kwargs)

    def test_valid_lengths(self):
        RichTextSpec(width=1.0, height="2in", maxwidth="50%")
        RichTextSpec(width="0.5npc", minwidth="1in", minheight=0.2, maxheight="3cm")

    @pytest.mark.parametrize("name", ["minwidth", "minheight", "maxheight"])
    def test_limits_are_validated(self, name):
        with pytest.raises(ValueError, match=name):
            RichTextSpec(**{name: 5})


def test_margin_forms():
    assert RichTextSpec(margin=3).margin == (3.0,) * 4
    assert RichTextSpec(margin=(1, 2)).margin == (1.0, 2.0, 1.0, 2.0)


def test_has_box():
    assert not RichTextSpec().has_box
    assert RichTextSpec(fill="white").has_box
    assert RichTextSpec(box_color="k").has_box


def test_replace_and_dict():
    s = RichTextSpec().replace(fill="red", box_colour="blue")
    assert s.fill == "red" and s.box_color == "blue"
    assert s.to_dict()["fill"] == "red"


def test_lists_become_tuples_and_hashable():
    s = RichTextSpec(fill=[1, 0, 0], box_color=[0, 0, 1])
    assert isinstance(s.fill, tuple)
    hash(s)


class TestResolveLength:
    @pytest.mark.parametrize(
        "value, expected",
        [
            (None, None),
            (0.5, 50.0),
            (1, 100.0),
            ("50%", 50.0),
            ("0.25npc", 25.0),
            ("1in", 100.0),  # at 100 dpi
            ("72pt", 100.0),
            ("2.54cm", 100.0),
        ],
    )
    def test_values(self, value, expected):
        result = resolve_length(value, reference=100.0, dpi=100.0)
        assert result == (pytest.approx(expected) if expected is not None else None)

    @pytest.mark.parametrize("value", ["abc%", "xnpc", "wide"])
    def test_invalid(self, value):
        assert resolve_length(value, 100.0, 100.0) is None
