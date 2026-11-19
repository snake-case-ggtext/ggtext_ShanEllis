"""
Quickstart: rich text in a plotnine plot.

The colored words in the title double as the legend, so the legend
itself can be dropped. This is the classic ggtext use case.

Run:  python examples/01_quickstart_plotnine.py
"""

import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from plotnine import (  # noqa: E402
    aes,
    geom_point,
    ggplot,
    labs,
    scale_color_manual,
    theme,
    theme_minimal,
)
from plotnine.data import penguins  # noqa: E402

from ggtext import element_markdown  # noqa: E402

# Images go to docs/images/; tests redirect them with GGTEXT_EXAMPLES_OUT
OUT = Path(
    os.environ.get("GGTEXT_EXAMPLES_OUT")
    or Path(__file__).resolve().parent.parent / "docs" / "images"
)
OUT.mkdir(parents=True, exist_ok=True)

# Okabe-Ito colors, an accessible palette
COLORS = {"Adelie": "#E69F00", "Chinstrap": "#56B4E9", "Gentoo": "#009E73"}

title = (
    "Bill size of "
    f"<span style='color:{COLORS['Adelie']}'>**Adelie**</span>, "
    f"<span style='color:{COLORS['Chinstrap']}'>**Chinstrap**</span> and "
    f"<span style='color:{COLORS['Gentoo']}'>**Gentoo**</span> penguins"
)

p = (
    ggplot(penguins.dropna(), aes("bill_length_mm", "bill_depth_mm", color="species"))
    + geom_point(size=2, alpha=0.8)
    + scale_color_manual(values=COLORS)
    + labs(
        title=title,
        x="Bill length (mm)",
        y="Bill depth (mm)",
        caption="Data: *palmerpenguins* via plotnine.data",
    )
    + theme_minimal()
    + theme(
        plot_title=element_markdown(size=14),
        plot_caption=element_markdown(color="#555555"),
        legend_position="none",
        figure_size=(7, 4.5),
    )
)

if __name__ == "__main__":
    p.save(OUT / "quickstart_plotnine.png", dpi=130, verbose=False)
    print("wrote", OUT / "quickstart_plotnine.png")
