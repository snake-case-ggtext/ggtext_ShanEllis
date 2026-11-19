"""
geom_textbox: word-wrapped rich text in boxes of a fixed width.

Handy for annotating a plot with a few sentences.

Run:  python examples/07_geom_textbox.py
"""

import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import pandas as pd
from plotnine import (
    aes,
    geom_point,
    ggplot,
    labs,
    scale_color_manual,
    theme,
    theme_minimal,
)
from plotnine.data import penguins

from ggtext import element_markdown, geom_textbox

# Images go to docs/images/; tests redirect them with GGTEXT_EXAMPLES_OUT
OUT = Path(
    os.environ.get("GGTEXT_EXAMPLES_OUT")
    or Path(__file__).resolve().parent.parent / "docs" / "images"
)
OUT.mkdir(parents=True, exist_ok=True)

COLORS = {"Adelie": "#E69F00", "Chinstrap": "#56B4E9", "Gentoo": "#009E73"}
pg = penguins.dropna()

notes = pd.DataFrame(
    {
        "x": [2750, 6300],
        "y": [231, 172],
        "ha": ["left", "right"],
        "va": ["top", "bottom"],
        "label": [
            (
                f"<span style='color:{COLORS['Gentoo']}'>**Gentoo**</span> penguins are the "
                "heaviest, with the longest flippers: most weigh **over 4.5 kg**."
            ),
            (
                f"<span style='color:{COLORS['Adelie']}'>**Adelie**</span> and "
                f"<span style='color:{COLORS['Chinstrap']}'>**Chinstrap**</span> overlap almost "
                "completely; body mass alone *cannot* tell them apart."
            ),
        ],
        "halign": ["left", "right"],
    }
)

p = (
    ggplot(pg, aes("body_mass_g", "flipper_length_mm"))
    + geom_point(aes(color="species"), alpha=0.7)
    + geom_textbox(
        aes("x", "y", label="label", halign="halign", ha="ha", va="va"),
        data=notes,
        width="2.3in",
        size=9,
        fill="#FAFAFA",
        box_color="#BBBBBB",
    )
    + scale_color_manual(values=COLORS, guide=None)
    + labs(
        x="Body mass (g)",
        y="Flipper length (mm)",
        title="Annotating with **geom_textbox()**",
    )
    + theme_minimal()
    + theme(figure_size=(7.5, 5), plot_title=element_markdown(size=13))
)

if __name__ == "__main__":
    p.save(OUT / "geom_textbox.png", dpi=130, verbose=False)
    print("wrote", OUT / "geom_textbox.png")
