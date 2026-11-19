"""
Image tests for ggtext.geom_textbox, ported from plotnine-ggtext.

Baselines live in tests/baseline_images/test_geom_textbox_images/. Run
``pytest --update-baselines`` to regenerate them. R renders of the
one-to-one ports are in tests/reference_r/.

Parameter translation from plotnine-ggtext: widths are strings
(``"1.5in"``) or fractions, margins/padding/r are points, ``box_size`` is
points (mm * 72.27/25.4), and ``width``/``height`` exclude the margins.
"""

import pandas as pd
import pytest
from plotnine import (
    aes,
    geom_point,
    ggplot,
    scale_color_identity,
    scale_fill_identity,
    xlim,
    ylim,
)
from plotnine.exceptions import PlotnineError

from ggtext import geom_textbox

pytestmark = [pytest.mark.plotnine, pytest.mark.image]

MM = 72.27 / 25.4  # R line widths (mm) to points
IN = 72.27  # grid inches to points

# ggtext: test-geom-textbox.R --------------------------------------------------


def test_rotated_boxes_w_colors_and_alignments():
    # Port of plotnine-ggtext test_geom_textbox.py::
    # test_rotated_boxes_w_colors_and_alignments, itself a one-to-one port of
    # R ggtext test-geom-textbox.R ("Rotated boxes w/ colors and alignments");
    # R render: reference_r/textbox_rotated_boxes_w_colors_and_alignments.png.
    # Adapted: R's width/height 1.5in include the 0.25in margins, ggtext
    # (Python) widths exclude them, so width = height = 1.5in - 2 * 0.25in
    # = 1in; box_size mm -> points.
    df = pd.DataFrame(
        {
            "x": 0.5,
            "y": 0.5,
            "label": "The quick brown fox **jumps over** the *lazy* dog.",
            "orientation": [
                "upright",
                "left-rotated",
                "inverted",
                "right-rotated",
            ],
            "box_color": ["#858E4E", "#24988F", "#8C82B8", "#B97681"],
            "fill": ["#E6EBD1", "#CDEFE9", "#E8E6FC", "#FEE1E5"],
            "halign": [0, 0.5, 1, 0.5],
            "valign": [1, 0.5, 0.5, 0],
            "box_size": [s * MM for s in (0.1, 0.25, 0.5, 1)],
        }
    )
    p = (
        ggplot()
        + geom_textbox(
            data=df,
            mapping=aes(
                "x",
                "y",
                label="label",
                box_color="box_color",
                fill="fill",
                halign="halign",
                valign="valign",
                box_size="box_size",
                orientation="orientation",
            ),
            width="1in",
            height="1in",
            box_margin=0.25 * IN,
            hjust=0,
            vjust=1,
        )
        + xlim(0, 1)
        + ylim(0, 1)
        + scale_fill_identity()
    )
    assert p == "rotated_boxes_w_colors_and_alignments"


# roxygen @examples ------------------------------------------------------------


def test_example_npc_width():
    # Port of plotnine-ggtext test_geom_textbox.py::test_example_npc_width
    # (R ggtext geom_textbox roxygen example).
    # Adapted: unit(0.4, "npc") -> 0.4; newline="space" because the label
    # has "\n    " inside a paragraph (R: a space; ggtext Python: a break).
    label = (
        "Lorem ipsum dolor **sit amet,** consectetur adipiscing elit,\n"
        "    sed do *eiusmod tempor incididunt* ut labore et dolore magna\n"
        "    aliqua."
    )
    df = pd.DataFrame(
        {
            "label": [label, label],
            "x": [0, 0.6],
            "y": [1, 0.6],
            "hjust": [0, 0],
            "vjust": [1, 0],
            "orientation": ["upright", "right-rotated"],
            "color": ["black", "blue"],
            "fill": ["cornsilk", "white"],
        }
    )
    p = (
        ggplot(df)
        + aes(
            "x",
            "y",
            label="label",
            color="color",
            fill="fill",
            hjust="hjust",
            vjust="vjust",
            orientation="orientation",
        )
        + geom_textbox(width=0.4, newline="space")
        + geom_point(color="black", fill="black", size=2)
        + scale_color_identity()
        + scale_fill_identity()
        + xlim(0, 1)
        + ylim(0, 1)
    )
    assert p == "example_npc_width"


# additional behaviour ---------------------------------------------------------

lorem = (
    "Lorem ipsum dolor sit amet, *consectetur* adipiscing elit. "
    "<span style='color:#B97681'>Quisque tincidunt</span> eget arcu in "
    "**pulvinar**.<br>Morbi varius leo<sup>2</sup> vel consectetur."
)


def test_size_limits_and_paragraphs():
    # Port of plotnine-ggtext test_geom_textbox.py::
    # test_size_limits_and_paragraphs (no R original).
    # Adapted: unit() values -> "2.5in"/"1in"/"1.8in", 0.6 npc -> 0.6,
    # box_r in points.
    df = pd.DataFrame(
        {
            "x": [0, 1, 0, 1],
            "y": [1, 1, 0, 0],
            "label": [lorem, lorem, "short", lorem + "\n\nA second paragraph."],
        }
    )
    p = (
        ggplot(df, aes("x", "y", label="label"))
        + geom_textbox(
            width=0.6,
            maxwidth="2.5in",
            minheight="1in",
            maxheight="1.8in",
            fill="#F0F7FF",
            box_color="#748696",
            box_r=3,
            valign=0.5,
        )
        + xlim(-0.5, 1.5)
        + ylim(-0.5, 1.5)
    )
    assert p == "size_limits_and_paragraphs"


def test_native_width_no_wrap():
    # Port of plotnine-ggtext test_geom_textbox.py::test_native_width_no_wrap
    # (no R original). width=None is supported as in plotnine-ggtext.
    df = pd.DataFrame(
        {"x": [0.5], "y": [0.5], "label": ["No wrapping<br>with **width=None**"]}
    )
    p = (
        ggplot(df, aes("x", "y", label="label"))
        + geom_textbox(width=None, box_color="none", fill="lightyellow", size=16)
        + xlim(0, 1)
        + ylim(0, 1)
    )
    assert p == "native_width_no_wrap"


def test_bad_orientation():
    # Port of plotnine-ggtext test_geom_textbox.py::test_bad_orientation.
    df = pd.DataFrame({"x": [1], "y": [1], "label": ["x"]})
    p = ggplot(df, aes("x", "y", label="label")) + geom_textbox(
        orientation="sideways"
    )
    with pytest.raises(PlotnineError, match="orientation"):
        p.draw_test()  # pyright: ignore
