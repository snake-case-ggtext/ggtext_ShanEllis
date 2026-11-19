"""
Image tests for ggtext.geom_richtext, ported from plotnine-ggtext.

Baselines live in tests/baseline_images/test_geom_richtext_images/. Run
``pytest --update-baselines`` to regenerate them. R renders of the
one-to-one ports are in tests/reference_r/.

Parameter translation from plotnine-ggtext: padding, margins and radii
are points (not grid units), ``label_size`` is points (mm * 72.27/25.4)
and ``\\n`` is a line break (``newline="space"`` where the original
relied on R's behavior).
"""

import pandas as pd
import pytest
from plotnine import (
    aes,
    facet_wrap,
    geom_point,
    ggplot,
    position_nudge,
    scale_color_identity,
    scale_fill_identity,
    xlim,
    ylim,
)
from plotnine.exceptions import PlotnineError

from ggtext import geom_richtext
from ggtext.plotnine.geoms import resolve_just

pytestmark = [pytest.mark.plotnine, pytest.mark.image]

MM = 72.27 / 25.4  # R line widths (mm) to points
IN = 72.27  # grid inches to points


# ggtext: test-geom-richtext.R -------------------------------------------------


def test_rotated_labels_w_colors():
    # Port of plotnine-ggtext test_geom_richtext.py::test_rotated_labels_w_colors,
    # itself a one-to-one port of R ggtext test-geom-richtext.R
    # ("Rotated labels w/ colors"); R render: reference_r/
    # richtext_rotated_labels_w_colors.png.
    # Adapted: label_size mm -> points; label_margin 0.25in -> points.
    df = pd.DataFrame(
        {
            "x": 0.5,
            "y": 0.5,
            "label": "The **quick** *brown* fox.",
            "angle": [0, 45, 90, 135],
            "label_color": ["#858E4E", "#24988F", "#8C82B8", "#B97681"],
            "fill": ["#E6EBD1", "#CDEFE9", "#E8E6FC", "#FEE1E5"],
            "label_size": [s * MM for s in (0.1, 0.25, 0.5, 1)],
        }
    )
    p = (
        ggplot()
        + geom_richtext(
            data=df,
            mapping=aes(
                "x",
                "y",
                label="label",
                label_color="label_color",
                fill="fill",
                label_size="label_size",
                angle="angle",
            ),
            label_margin=0.25 * IN,
            hjust=0,
            vjust=0.5,
        )
        + xlim(0, 1)
        + ylim(0, 1)
        + scale_fill_identity()
    )
    assert p == "rotated_labels_w_colors"


# roxygen @examples ------------------------------------------------------------

example_df = pd.DataFrame(
    {
        "label": [
            "Some text **in bold.**",
            "Linebreaks<br>Linebreaks<br>Linebreaks",
            "*x*<sup>2</sup> + 5*x* + *C*<sub>*i*</sub>",
            "Some <span style='color:blue'>blue text **in bold.**</span><br>"
            "And *italics text.*<br>\n"
            "      And some <span style='font-size:18pt; color:black'>"
            "large</span> text.",
        ],
        "x": [0.2, 0.1, 0.5, 0.9],
        "y": [0.8, 0.4, 0.1, 0.5],
        "hjust": [0.5, 0, 0, 1],
        "vjust": [0.5, 1, 0, 0.5],
        "angle": [0, 0, 45, -45],
        "color": ["black", "blue", "black", "red"],
        "fill": ["cornsilk", "white", "lightblue", "white"],
    }
)


def test_example_markup():
    # Port of plotnine-ggtext test_geom_richtext.py::test_example_markup
    # (R ggtext geom_richtext roxygen example 1).
    # Adapted: newline="space" because the last label has "<br>\n      And",
    # where R treats the newline as a space but ggtext (Python) breaks.
    p = (
        ggplot(example_df)
        + aes(
            "x",
            "y",
            label="label",
            angle="angle",
            color="color",
            fill="fill",
            hjust="hjust",
            vjust="vjust",
        )
        + geom_richtext(newline="space")
        + geom_point(color="black", fill="black", size=2)
        + scale_color_identity()
        + scale_fill_identity()
        + xlim(0, 1)
        + ylim(0, 1)
    )
    assert p == "example_markup"


def test_example_no_frame():
    # Port of plotnine-ggtext test_geom_richtext.py::test_example_no_frame
    # (R ggtext geom_richtext roxygen example 2).
    # Adapted: newline="space" (see test_example_markup); label_padding in
    # points; R label.color = NA -> label_color="none".
    p = (
        ggplot(example_df)
        + aes(
            "x",
            "y",
            label="label",
            angle="angle",
            color="color",
            hjust="hjust",
            vjust="vjust",
        )
        + geom_richtext(
            fill="none",
            label_color="none",
            label_padding=0,
            newline="space",
        )
        + geom_point(color="black", fill="black", size=2)
        + scale_color_identity()
        + xlim(0, 1)
        + ylim(0, 1)
    )
    assert p == "example_no_frame"


# additional behaviour ---------------------------------------------------------


def test_text_color_alpha_and_named_just():
    # Port of plotnine-ggtext test_geom_richtext.py::
    # test_text_color_alpha_and_named_just (no R original).
    df = pd.DataFrame(
        {
            "x": [1, 2, 3],
            "y": [1, 2, 3],
            "label": ["*left* / bottom", "**center**", "right / top"],
            "hjust": ["left", "center", "right"],
            "vjust": ["bottom", "middle", "top"],
        }
    )
    p = (
        ggplot(df, aes("x", "y", label="label", hjust="hjust", vjust="vjust"))
        + geom_richtext(color="darkblue", text_color="firebrick", alpha=0.6, size=14)
        + geom_point()
    )
    assert p == "text_color_alpha_and_named_just"


def test_inward_outward_and_nudge():
    # Port of plotnine-ggtext test_geom_richtext.py::
    # test_inward_outward_and_nudge (no R original).
    df = pd.DataFrame(
        {
            "x": [0, 0.5, 1, 0, 0.5, 1],
            "y": [1, 1, 1, 0, 0, 0],
            "label": ["in<sub>0</sub>", "in", "in<sup>1</sup>", "out", "out", "out"],
            "just": ["inward"] * 3 + ["outward"] * 3,
        }
    )
    p = (
        ggplot(df, aes("x", "y", label="label", hjust="just", vjust="just"))
        + geom_point()
        + geom_richtext(nudge_y=0.05)
        + xlim(-0.25, 1.25)
        + ylim(-0.25, 1.25)
    )
    assert p == "inward_outward_and_nudge"


def test_facets_and_legend():
    # Port of plotnine-ggtext test_geom_richtext.py::test_facets_and_legend
    # (no R original).
    df = pd.DataFrame(
        {
            "x": [1, 2, 3, 1, 2, 3],
            "y": [1, 2, 1, 2, 1, 2],
            "g": ["a", "a", "a", "b", "b", "b"],
            "label": [f"**{i}**<sup>{i}</sup>" for i in range(6)],
        }
    )
    p = (
        ggplot(df, aes("x", "y", label="label", color="g"))
        + geom_richtext()
        + facet_wrap("g")
    )
    assert p == "facets_and_legend"


# behaviour that differs from plotnine-ggtext ----------------------------------


def test_nudge_with_position_accepted():
    # Port of plotnine-ggtext test_geom_richtext.py::
    # test_nudge_with_position_accepted.
    # Adapted: ggtext (Python) inherits plotnine's geom_text handling, which
    # accepts nudge_x together with an explicit position (no error), so
    # only check that the geom is constructed.
    geom_richtext(nudge_x=1, position=position_nudge(1))


def test_unsupported_tag_warns():
    # Port of plotnine-ggtext test_geom_richtext.py::test_unsupported_tag_raises.
    # Adapted: ggtext (Python) warns and still draws the text instead of
    # raising ValueError.
    df = pd.DataFrame({"x": [1], "y": [1], "label": ["a<table>x</table>b"]})
    p = ggplot(df, aes("x", "y", label="label")) + geom_richtext()
    with pytest.warns(UserWarning):
        p.draw_test()  # pyright: ignore


# justification (plotnine-ggtext: compute_just) --------------------------------
# Equivalent here: ggtext.plotnine.geoms.resolve_just(value, npc, axis), which
# works on one label and returns a matplotlib name or a number.


def test_resolve_just_numbers():
    # Port of test_geom_base.py::test_compute_just_numbers. Adapted: scalar,
    # per-label API; the position (npc) is ignored for numbers.
    assert resolve_just(0.3, 0.1, "x") == pytest.approx(0.3)
    assert resolve_just(0.3, 0.9, "x") == pytest.approx(0.3)
    assert resolve_just(0.0, 0.5, "x") == "left"
    assert resolve_just(1.0, 0.5, "x") == "right"


@pytest.mark.parametrize(
    "axis, name, val",
    [
        ("x", "left", "left"),
        ("x", "center", "center"),
        ("x", "centre", "center"),
        ("x", "right", "right"),
        ("y", "bottom", "bottom"),
        ("y", "middle", "center"),
        ("y", "top", "top"),
    ],
)
def test_resolve_just_named(axis, name, val):
    # Port of test_geom_base.py::test_compute_just_named (returns matplotlib
    # alignment names rather than numbers).
    assert resolve_just(name, 0.2, axis) == val


def test_resolve_just_inward():
    # Port of test_geom_base.py::test_compute_just_inward.
    assert [resolve_just("inward", n, "x") for n in (0.1, 0.5, 0.9)] == [
        "left",
        "center",
        "right",
    ]
    assert [resolve_just("inward", n, "y") for n in (0.1, 0.5, 0.9)] == [
        "bottom",
        "center",
        "top",
    ]


def test_resolve_just_outward():
    # Port of test_geom_base.py::test_compute_just_outward.
    assert [resolve_just("outward", n, "x") for n in (0.1, 0.5, 0.9)] == [
        "right",
        "center",
        "left",
    ]


def test_resolve_just_inward_tolerance():
    # Port of test_geom_base.py::test_compute_just_inward_tolerance.
    assert resolve_just("inward", 0.5004, "x") == "center"


def test_resolve_just_unknown_raises():
    # Port of test_geom_base.py::test_compute_just_unknown_raises.
    with pytest.raises(PlotnineError):
        resolve_just("sideways", 0.5, "x")
