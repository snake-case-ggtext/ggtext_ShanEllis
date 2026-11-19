"""
Quickstart: rich text with plain matplotlib (no plotnine needed).

Run:  python examples/02_quickstart_matplotlib.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

import ggtext

OUT = Path(__file__).resolve().parent.parent / "docs" / "images"
OUT.mkdir(parents=True, exist_ok=True)

BLUE, ORANGE = "#0072B2", "#D55E00"

x = np.linspace(0, 4 * np.pi, 300)
fig, ax = plt.subplots(figsize=(7, 4.2), dpi=130, layout="constrained")
ax.plot(x, np.sin(x), color=BLUE, lw=2)
ax.plot(x, np.cos(x), color=ORANGE, lw=2)

ggtext.set_title(
    ax,
    f"<span style='color:{BLUE}'>**sin(x)**</span> and "
    f"<span style='color:{ORANGE}'>**cos(x)**</span> are a quarter turn apart",
    fontsize=13,
)
ggtext.set_xlabel(ax, "*x* (radians)")
ggtext.set_ylabel(ax, "amplitude, $A$")

ggtext.annotate(
    ax,
    "Peaks of **sin** lag those of **cos** by $\\pi/2$",
    xy=(np.pi / 2, 1),
    xytext=(3.2, 1.45),
    va="center",
    arrowprops={"arrowstyle": "->", "color": "#444444"},
    fill="#FFF8E1",
    box_color="#999999",
    padding=4,
    r=4,
    fontsize=10,
)
ax.set_ylim(-1.2, 1.75)
ax.spines[["top", "right"]].set_visible(False)

if __name__ == "__main__":
    fig.savefig(OUT / "quickstart_matplotlib.png")
    print("wrote", OUT / "quickstart_matplotlib.png")
