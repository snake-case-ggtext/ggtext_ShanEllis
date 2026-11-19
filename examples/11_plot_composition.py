"""
Plot compositions: rich text in p1 | p2.

Each plot's wrapped subtitle (element_textbox_simple, width=1) spans the
panel area of *its own* plot, not the whole figure.

Run:  python examples/11_plot_composition.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from plotnine import (
    aes,
    geom_histogram,
    geom_point,
    ggplot,
    labs,
    scale_color_manual,
    scale_fill_manual,
    theme,
    theme_minimal,
)
from plotnine.data import penguins

from ggtext import element_markdown, element_textbox_simple

OUT = Path(__file__).resolve().parent.parent / "docs" / "images"
OUT.mkdir(parents=True, exist_ok=True)

COLORS = {"Adelie": "#E69F00", "Chinstrap": "#56B4E9", "Gentoo": "#009E73"}
pg = penguins.dropna()

rich_theme = theme_minimal() + theme(
    plot_title=element_markdown(size=12),
    plot_subtitle=element_textbox_simple(
        size=9, fill="#F2F2F2", padding=4, r=3, margin={"b": 6}
    ),
    legend_position="none",
)

p1 = (
    ggplot(pg, aes("flipper_length_mm", fill="species"))
    + geom_histogram(bins=25, alpha=0.85)
    + scale_fill_manual(values=COLORS)
    + labs(
        title="**Flipper length**",
        subtitle=f"<span style='color:{COLORS['Gentoo']}'>**Gentoo**</span> penguins have "
        "clearly longer flippers; the other two species overlap.",
        x="mm",
        y="count",
    )
    + rich_theme
)

p2 = (
    ggplot(pg, aes("bill_length_mm", "bill_depth_mm", color="species"))
    + geom_point(alpha=0.8)
    + labs(
        title="**Bill shape**",
        subtitle=f"Bill depth separates <span style='color:{COLORS['Gentoo']}'>**Gentoo**</span>; "
        f"bill length separates <span style='color:{COLORS['Adelie']}'>**Adelie**</span> from the rest.",
        x="length (mm)",
        y="depth (mm)",
    )
    + scale_color_manual(values=COLORS)
    + rich_theme
)

composition = (p1 | p2) + theme(figure_size=(9, 4))

if __name__ == "__main__":
    composition.save(OUT / "plot_composition.png", dpi=130, verbose=False)
    print("wrote", OUT / "plot_composition.png")
