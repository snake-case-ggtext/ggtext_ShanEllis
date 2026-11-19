"""
geom_richtext: rich text labels, with or without a box, at any angle.

Unlike plotnine's geom_label, boxed labels can be rotated.

Run:  python examples/06_geom_richtext.py
"""

import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from plotnine import (  # noqa: E402
    aes,
    coord_fixed,
    geom_point,
    ggplot,
    labs,
    lims,
    scale_fill_manual,
    theme,
    theme_void,
)

from ggtext import element_markdown, geom_richtext  # noqa: E402

# Images go to docs/images/; tests redirect them with GGTEXT_EXAMPLES_OUT
OUT = Path(
    os.environ.get("GGTEXT_EXAMPLES_OUT")
    or Path(__file__).resolve().parent.parent / "docs" / "images"
)
OUT.mkdir(parents=True, exist_ok=True)

# Labels arranged on a circle, each rotated to point outwards
angles = np.arange(0, 360, 30)
df = pd.DataFrame(
    {
        "x": 1.2 * np.cos(np.radians(angles)),
        "y": 1.2 * np.sin(np.radians(angles)),
        "angle": angles,
        "label": [f"**{a}°** <span style='color:#D55E00'>*rich*</span>" for a in angles],
        "half": np.where(angles < 180, "top", "bottom"),
    }
)
center = pd.DataFrame(
    {
        "x": [0, 0, 0],
        "y": [0.22, -0.05, -0.25],
        "label": [
            "<span style='font-size:15pt'>**geom_richtext()**</span>",
            "boxes rotate with the text",
            "H<sub>2</sub>O · x<sup>2</sup> · $\\sqrt{\\alpha}$",
        ],
    }
)

p = (
    ggplot(df, aes("x", "y"))
    + geom_point(color="#999999", size=1)
    + geom_richtext(
        aes(label="label", angle="angle", fill="half"),
        ha="left",
        nudge_x=0,
        size=9,
        label_color="#555555",
    )
    + geom_richtext(
        aes(label="label"), data=center, fill=None, label_size=0, size=10, color="#333333"
    )
    + scale_fill_manual(values={"top": "#FFF3D6", "bottom": "#DCEFFA"}, guide=None)
    + lims(x=(-1.95, 1.95), y=(-1.95, 1.95))
    + coord_fixed()
    + labs(title="Rotated, boxed **rich text labels**")
    + theme_void()
    + theme(
        figure_size=(6.5, 6.5),
        plot_title=element_markdown(size=13, margin={"t": 10}),
    )
)

if __name__ == "__main__":
    p.save(OUT / "geom_richtext.png", dpi=120, verbose=False)
    print("wrote", OUT / "geom_richtext.png")
