"""
Titles, subtitles and captions.

- The title uses colored words as an inline legend (element_markdown).
- The long subtitle is word-wrapped to the width of the panel area
  (element_textbox_simple), with a light background box.
- The caption mixes italics and a link-style source note.

Run:  python examples/03_titles_and_subtitles.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from plotnine import (
    aes,
    geom_line,
    ggplot,
    labs,
    scale_color_manual,
    scale_x_datetime,
    theme,
    theme_minimal,
)
from plotnine.data import economics_long

from ggtext import element_markdown, element_textbox_simple

OUT = Path(__file__).resolve().parent.parent / "docs" / "images"
OUT.mkdir(parents=True, exist_ok=True)

BLUE, ORANGE = "#0072B2", "#D55E00"

df = economics_long[economics_long["variable"].isin(["psavert", "uempmed"])]

title = (
    f"<span style='color:{BLUE}'>**Personal savings rate**</span> and "
    f"<span style='color:{ORANGE}'>**unemployment duration**</span>, 1967–2015"
)
subtitle = (
    "This subtitle is drawn with **element_textbox_simple()**: it is "
    "word-wrapped to the width of the panel area, so you can write a real "
    "sentence or two about what the reader should notice. Styles such as "
    "*italics*, <span style='color:#0072B2'>**colored bold text**</span> and "
    "units like m<sup>2</sup> survive the line breaks."
)

p = (
    ggplot(df, aes("date", "value", color="variable"))
    + geom_line(size=0.8)
    + scale_color_manual(values={"psavert": BLUE, "uempmed": ORANGE})
    + scale_x_datetime(date_labels="%Y")
    + labs(
        title=title,
        subtitle=subtitle,
        x="",
        y="",
        caption="Source: *economics_long* (US FRED data) bundled with plotnine",
    )
    + theme_minimal()
    + theme(
        figure_size=(8, 5),
        legend_position="none",
        plot_title=element_markdown(size=14, ha="left"),
        plot_subtitle=element_textbox_simple(
            size=10,
            color="#333333",
            fill="#F2F2F2",
            padding=(6, 8),
            r=4,
            margin={"t": 4, "b": 10},
        ),
        plot_caption=element_markdown(size=8, color="#666666"),
    )
)

if __name__ == "__main__":
    p.save(OUT / "titles_and_subtitles.png", dpi=130, verbose=False)
    print("wrote", OUT / "titles_and_subtitles.png")
