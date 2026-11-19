"""
Image tests for rich text in plotnine theme elements.

The geom image tests (ported from ggtext) cover labels inside the panels;
these cover the text *around* the panels, where plotnine's layout engine
has to make room for rich text: titles, subtitles and captions, axis
titles and tick labels, facet strips, legends, and tags.

Baselines live in tests/baseline_images/test_theme_images/ and are made in
the reference environment (Linux, matplotlib 3.11; see
tests/image_compare.py). Update them with ``pytest --update-baselines``.
"""

import pandas as pd
import pytest
from plotnine import (
    aes,
    facet_grid,
    geom_point,
    ggplot,
    labs,
    scale_color_discrete,
    scale_x_continuous,
    theme,
)

from ggtext import element_markdown, element_textbox, element_textbox_simple

pytestmark = [pytest.mark.plotnine, pytest.mark.image]

ORANGE, BLUE, GREEN = "#E69F00", "#0072B2", "#009E73"

df = pd.DataFrame(
    {
        "x": [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5],
        "y": [2.0, 3.1, 2.4, 4.2, 3.8, 5.0, 4.4, 5.6],
        "group": ["a", "b", "c", "a", "b", "c", "a", "b"],
        "row": [
            "first",
            "first",
            "first",
            "first",
            "second",
            "second",
            "second",
            "second",
        ],
        "col": ["left", "right", "left", "right", "left", "right", "left", "right"],
    }
)

SUBTITLE = (
    "A long subtitle drawn with **element_textbox_simple()**: it wraps to the "
    "width of the panel area, keeps *italics*, <span style='color:#0072B2'>"
    "**colored bold text**</span> and units like m<sup>2</sup> across the "
    "line breaks, and sits in a light box with rounded corners."
)


def test_title_subtitle_caption():
    p = (
        ggplot(df, aes("x", "y"))
        + geom_point()
        + labs(
            title=(
                f"<span style='color:{ORANGE}'>**Orange**</span> and "
                f"<span style='color:{BLUE}'>**blue**</span> words in a title"
            ),
            subtitle=SUBTITLE,
            caption="Source: *made-up data* &bull; ggtext",
        )
        + theme(
            plot_title=element_markdown(size=14),
            plot_subtitle=element_textbox_simple(
                size=10, fill="#EEEEEE", padding=5, r=4, margin={"b": 6}
            ),
            plot_caption=element_markdown(color="#555555"),
        )
    )
    assert p == "title_subtitle_caption"


def test_boxed_title_and_tag():
    p = (
        ggplot(df, aes("x", "y"))
        + geom_point()
        + labs(title="A **boxed** title", tag="**A**")
        + theme(
            plot_title=element_markdown(
                size=13, fill="cornsilk", box_color="#888888", r=4, padding=(3, 6)
            ),
            plot_tag=element_markdown(size=16, color=ORANGE),
        )
    )
    assert p == "boxed_title_and_tag"


def test_axis_titles_and_tick_labels():
    p = (
        ggplot(df, aes("x", "y"))
        + geom_point()
        + scale_x_continuous(
            breaks=[1, 2, 3, 4],
            labels=[
                "**one**",
                "*two*",
                f"<span style='color:{BLUE}'>three</span>",
                "fo<sup>ur</sup>",
            ],
        )
        + labs(
            x="Concentration, CO<sub>2</sub> (g m<sup>-3</sup>)",
            y="A **boxed**, rotated y-axis title that is long enough to wrap onto a second line",
        )
        + theme(
            axis_title_x=element_markdown(),
            axis_title_y=element_textbox(
                orientation="left-rotated",
                width=0.7,
                halign="center",
                fill="#E8EEF7",
                padding=4,
                r=3,
            ),
            axis_text_x=element_markdown(rotation=45, ha="right", size=10),
            axis_text_y=element_markdown(color=GREEN),
        )
    )
    assert p == "axis_titles_and_tick_labels"


def test_facet_strips_top_and_right():
    def labeller(value: str) -> str:
        return f"**{value}** <span style='color:{ORANGE}'>panel</span>"

    p = (
        ggplot(df, aes("x", "y"))
        + geom_point()
        # plotnine types `labeller` as a Literal, but it also accepts a callable
        + facet_grid("row", "col", labeller=labeller)  # pyrefly: ignore[bad-argument-type]
        + theme(
            strip_text=element_markdown(),
            strip_text_y=element_markdown(rotation=-90),
        )
    )
    assert p == "facet_strips_top_and_right"


def test_legend_rich_labels_and_title():
    p = (
        ggplot(df, aes("x", "y", color="group"))
        + geom_point(size=3)
        + scale_color_discrete(
            labels=["**Adelie**", "*Chinstrap*", "Gentoo<sup>†</sup>"]
        )
        + labs(
            color="**Species**<br><span style='font-size:8pt;color:gray'>(n = 8)</span>"
        )
        + theme(
            legend_title=element_markdown(),
            legend_text=element_markdown(),
        )
    )
    assert p == "legend_rich_labels_and_title"


def test_colorbar_title_and_bottom_legend():
    p = (
        ggplot(df, aes("x", "y", color="y"))
        + geom_point(size=3)
        + labs(color="*y* value<br><span style='font-size:8pt'>(continuous)</span>")
        + theme(
            legend_title=element_markdown(),
            legend_position="bottom",
        )
    )
    assert p == "colorbar_title_and_bottom_legend"
