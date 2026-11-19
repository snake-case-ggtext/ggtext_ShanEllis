"""
Axis titles and tick labels.

- Axis titles with units written with <sub>/<sup>.
- Rich tick labels: each category label has its own style, and the
  labels are rotated (any angle works).

Run:  python examples/04_axis_and_tick_labels.py
"""

import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import pandas as pd  # noqa: E402
from plotnine import (  # noqa: E402
    aes,
    coord_flip,
    geom_col,
    ggplot,
    labs,
    scale_fill_manual,
    scale_x_discrete,
    theme,
    theme_minimal,
)

from ggtext import element_markdown  # noqa: E402

# Images go to docs/images/; tests redirect them with GGTEXT_EXAMPLES_OUT
OUT = Path(
    os.environ.get("GGTEXT_EXAMPLES_OUT")
    or Path(__file__).resolve().parent.parent / "docs" / "images"
)
OUT.mkdir(parents=True, exist_ok=True)

# Illustrative (made-up) emissions of some car classes
df = pd.DataFrame(
    {
        "vehicle": ["ev", "hybrid", "compact", "suv", "pickup"],
        "co2": [30, 95, 140, 210, 255],
        "kind": ["electric", "hybrid", "gas", "gas", "gas"],
    }
)
labels = {
    "ev": "<span style='color:#009E73'>**Electric**</span>",
    "hybrid": "<span style='color:#56B4E9'>**Hybrid**</span>",
    "compact": "Compact",
    "suv": "SUV",
    "pickup": "*Pickup*<br><span style='font-size:7pt;color:#777'>(full size)</span>",
}

p = (
    ggplot(df, aes("vehicle", "co2", fill="kind"))
    + geom_col(width=0.7)
    + scale_x_discrete(limits=list(labels), labels=list(labels.values()))
    + scale_fill_manual(values={"electric": "#009E73", "hybrid": "#56B4E9", "gas": "#999999"})
    + labs(
        x="",
        y="CO<sub>2</sub> emissions (g km<sup>-1</sup>)",
        title="Rich **tick labels** and **axis titles**",
        caption="Illustrative values",
    )
    + theme_minimal()
    + theme(
        figure_size=(7, 4.5),
        legend_position="none",
        plot_title=element_markdown(size=13),
        axis_title_y=element_markdown(size=11),
        axis_text_x=element_markdown(size=10, rotation=30, ha="right"),
    )
)

# The same labels on a horizontal bar chart: tick labels on the y axis
p2 = (
    p
    + coord_flip()
    + labs(title="…and on the **y axis** after `coord_flip()`")
    + theme(axis_text_x=element_markdown(rotation=0, ha="center"),
            axis_text_y=element_markdown(size=10, ha="right"),
            axis_title_x=element_markdown(size=11))
)

if __name__ == "__main__":
    p.save(OUT / "axis_and_tick_labels.png", dpi=130, verbose=False)
    p2.save(OUT / "axis_and_tick_labels_flipped.png", dpi=130, verbose=False)
    print("wrote", OUT / "axis_and_tick_labels.png")
    print("wrote", OUT / "axis_and_tick_labels_flipped.png")
