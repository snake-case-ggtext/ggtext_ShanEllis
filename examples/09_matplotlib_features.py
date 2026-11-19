"""
A tour of the matplotlib helpers.

- ggtext.text / textbox / annotate / set_title / set_xlabel / set_ylabel
- rich tick labels with ggtext.rich_ticklabels
- turning an existing artist into rich text with ggtext.richify
- boxes, rotation, highlights, underline/strikethrough, mathtext

Run:  python examples/09_matplotlib_features.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

import ggtext

OUT = Path(__file__).resolve().parent.parent / "docs" / "images"
OUT.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(1)
groups = ["control", "low", "high"]
values = [rng.normal(m, 1, 40) for m in (5, 6, 8)]

fig, ax = plt.subplots(figsize=(8, 5), dpi=130, layout="constrained")
ax.boxplot(values, widths=0.5)
ax.set_xlim(0.3, 5.4)
ax.set_ylim(1, 13)
ax.spines[["top", "right"]].set_visible(False)

# Titles and axis labels
ggtext.set_title(ax, "The **matplotlib** side of ggtext", fontsize=14, loc="left")
ggtext.set_ylabel(ax, "Response, *y* (mg L<sup>-1</sup>)")
ggtext.set_xlabel(ax, "Dose group <span style='color:#777777'>(*n* = 40 each)</span>")

# Rich tick labels
ax.set_xticks(
    [1, 2, 3],
    [
        "Control",
        "<span style='color:#E69F00'>**Low**</span>",
        "<span style='color:#D55E00'>**High**</span>",
    ],
)
ggtext.rich_ticklabels(ax, "x")

# An existing artist, converted in place
ax.text(
    0.45, 12.2, "Mean of *high* ≈ **8** (made-up data)", fontsize=9, color="#444444"
)
ggtext.richify(ax.texts[-1])

# Inline styles
ggtext.text(
    ax, 3.7, 11.6,
    "<mark>highlight</mark>, <u>underline</u>, ~~strike~~,<br>"
    "`code`, x<sup>2</sup>, H<sub>2</sub>O and $\\bar{x} \\pm \\sigma$",
    fontsize=10, va="top",
)  # fmt: skip

# A word-wrapped text box
ggtext.textbox(
    ax, 4.55, 6.3,
    "**textbox()** wraps text to a fixed width. "
    "<span style='color:#0072B2'>Colors</span>, *italics* and **bold** survive the wrapping.",
    width="1.9in", fontsize=9, fill="#F4F8FB", box_color="#0072B2",
)  # fmt: skip

# Rotated text with a box
ggtext.text(
    ax, 3.55, 2.3, "rotated **30°**", rotation=30, fontsize=10,
    fill="#FFF3D6", box_color="#E69F00", padding=3, r=3,
)  # fmt: skip

# An annotation whose arrow attaches to the rich box
ggtext.annotate(
    ax, "**Outlier?** check the<br>raw data",
    xy=(3, values[2].max()), xytext=(1.25, 10.6),
    arrowprops={"arrowstyle": "->", "color": "#555555"},
    fontsize=9, fill="white", box_color="#999999", padding=3, r=3,
)  # fmt: skip

if __name__ == "__main__":
    fig.savefig(OUT / "matplotlib_features.png")
    print("wrote", OUT / "matplotlib_features.png")
