"""
Images inside text: <img> tags in tick labels and titles.

To keep this example self-contained (no downloads, no files), the
"flags" are tiny numpy arrays registered with ggtext.register_image().
With real files you would write <img src='path/to/flag.png' width='20'>.

Run:  python examples/08_images_in_labels.py
"""

import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd
from plotnine import (
    aes,
    geom_col,
    ggplot,
    labs,
    scale_x_discrete,
    theme,
    theme_minimal,
)

import ggtext
from ggtext import element_markdown

# Images go to docs/images/; tests redirect them with GGTEXT_EXAMPLES_OUT
OUT = Path(
    os.environ.get("GGTEXT_EXAMPLES_OUT")
    or Path(__file__).resolve().parent.parent / "docs" / "images"
)
OUT.mkdir(parents=True, exist_ok=True)


def stripes(colors, vertical=True, h=20, w=30):
    """A tiny striped 'flag' as an (h, w, 3) float array."""
    img = np.zeros((h, w, 3))
    n = len(colors)
    for i, c in enumerate(colors):
        rgb = np.array(matplotlib.colors.to_rgb(c))
        if vertical:
            img[:, i * w // n : (i + 1) * w // n] = rgb
        else:
            img[i * h // n : (i + 1) * h // n, :] = rgb
    return img


# Made-up flags for made-up countries
flags = {
    "Avalon": stripes(["#0072B2", "#F0E442", "#D55E00"]),
    "Brindle": stripes(["#009E73", "#F0E442"], vertical=False),
    "Corvia": stripes(["#CC79A7", "#56B4E9", "#CC79A7"], vertical=False),
    "Dunmore": stripes(["#000000", "#E69F00", "#56B4E9"]),
}
for name, img in flags.items():
    ggtext.register_image(f"flag_{name}", img)

# A color swatch for the title
ggtext.register_image("swatch", stripes(["#0072B2"], h=10, w=10))

df = pd.DataFrame({"country": list(flags), "medals": [12, 9, 7, 4]})
labels = [f"<img src='flag_{c}' height='16pt'><br>**{c}**" for c in flags]

p = (
    ggplot(df, aes("country", "medals"))
    + geom_col(fill="#0072B2", width=0.6)
    + scale_x_discrete(limits=list(flags), labels=labels)
    + labs(
        x="",
        y="Medals",
        title="<img src='swatch' height='10pt'> **Medals** by (fictional) country",
    )
    + theme_minimal()
    + theme(
        figure_size=(6.5, 4.2),
        plot_title=element_markdown(size=13),
        axis_text_x=element_markdown(size=10, linespacing=1.4),
    )
)

if __name__ == "__main__":
    p.save(OUT / "images_in_labels.png", dpi=130, verbose=False)
    print("wrote", OUT / "images_in_labels.png")
