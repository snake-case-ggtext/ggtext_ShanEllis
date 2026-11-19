"""
Facet strips and legends.

- Facet labels built with a labeller function that returns markup.
- Legend title on two lines, with a smaller grey second line.
- Legend labels with mixed styles.

Run:  python examples/05_facet_strips_and_legends.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from plotnine import (  # noqa: E402
    aes,
    facet_wrap,
    geom_point,
    ggplot,
    labs,
    scale_color_manual,
    theme,
    theme_bw,
)
from plotnine.data import penguins  # noqa: E402

from ggtext import element_markdown  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "docs" / "images"
OUT.mkdir(parents=True, exist_ok=True)

ISLAND_N = penguins.dropna().groupby("island", observed=True).size().to_dict()


def island_label(island: str) -> str:
    """Facet label: bold island name and a grey sample size."""
    return f"**{island}** <span style='color:#666666'>(*n* = {ISLAND_N[island]})</span>"


p = (
    ggplot(penguins.dropna(), aes("flipper_length_mm", "body_mass_g", color="sex"))
    + geom_point(alpha=0.7)
    + facet_wrap("island", labeller=island_label)
    + scale_color_manual(
        values={"female": "#CC79A7", "male": "#0072B2"},
        labels=[
            "<span style='color:#CC79A7'>**female**</span>",
            "<span style='color:#0072B2'>**male**</span>",
        ],
    )
    + labs(
        x="Flipper length (mm)",
        y="Body mass (g)",
        color="**Sex**<br><span style='font-size:8pt;color:#777777'>as recorded</span>",
        title="Rich **facet strips** and **legends**",
    )
    + theme_bw()
    + theme(
        figure_size=(8, 3.8),
        plot_title=element_markdown(size=13),
        strip_text=element_markdown(size=10),
        legend_title=element_markdown(),
        legend_text=element_markdown(),
    )
)

if __name__ == "__main__":
    p.save(OUT / "facet_strips_and_legends.png", dpi=130, verbose=False)
    print("wrote", OUT / "facet_strips_and_legends.png")
