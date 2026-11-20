"""
A visual cheatsheet: every supported syntax element next to its source.

Run:  python examples/10_syntax_cheatsheet.py
"""

import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd
from plotnine import (
    aes,
    annotate,
    geom_text,
    ggplot,
    labs,
    scale_x_continuous,
    scale_y_continuous,
    theme,
    theme_void,
)

import ggtext
from ggtext import element_markdown, geom_richtext

# Images go to docs/images/; tests redirect them with GGTEXT_EXAMPLES_OUT
OUT = Path(
    os.environ.get("GGTEXT_EXAMPLES_OUT")
    or Path(__file__).resolve().parent.parent / "docs" / "images"
)
OUT.mkdir(parents=True, exist_ok=True)

ggtext.register_image("dot", np.array([[[0, 114, 178]]], dtype=np.uint8))

ROWS = [
    ("Markdown", None),
    ("**bold** and __bold__", None),
    ("*italic* and _italic_", None),
    ("***bold italic***", None),
    ("~~strikethrough~~", None),
    ("`inline code`", None),
    ("[a link](https://wilkelab.org/ggtext)", None),
    ("snake_case_names stay literal", None),
    ("\\*escaped\\* &amp; entities &lt;3", None),
    ("HTML", None),
    ("<b>b</b> <i>i</i> <u>u</u> <s>s</s>", None),
    ("x<sup>2</sup> and H<sub>2</sub>O", None),
    ("<span style='color:#D55E00'>color</span>", None),
    ("<span style='font-size:16pt'>size</span>", None),
    ("<span style='font-family:serif'>family</span>", None),
    ("<span style='background-color:#F0E442'>background</span>", None),
    ("<mark>mark</mark> <small>small</small> <big>big</big>", None),
    ("<code>code</code> <kbd>kbd</kbd>", None),
    ("line one<br>line two", None),
    ("<img src='dot' width='12' height='12'> image", None),
    ("Math", None),
    ("$\\alpha^2 + \\sqrt{\\beta_i}$", None),
]

SECTIONS = ("Markdown", "HTML", "Math")

# One row per line of the cheatsheet, top to bottom
rows = []
y = 0.0
for source, _ in ROWS:
    if source in SECTIONS:
        y -= 0.4
        rows.append({"y": y, "source": "", "rendered": f"**{source}**", "head": True})
        y -= 1.0
        continue
    # matplotlib would read $...$ in the plain source column as math
    shown = source.replace("$", "\\$")
    rows.append({"y": y, "source": shown, "rendered": source, "head": False})
    y -= 1.5 if "<br>" in source else 1.0
df = pd.DataFrame(rows)
heads, entries = df[df["head"]], df[~df["head"]]

p = (
    ggplot(mapping=aes(y="y"))
    + geom_text(
        aes(x=0, label="source"), entries,
        ha="left", size=8.5, family="monospace", color="#333333",
    )
    + geom_richtext(
        aes(x=1, label="rendered"), entries,
        hjust=0, size=11, fill="none", label_color="none", label_padding=0,
    )
    + geom_richtext(
        aes(x=0, label="rendered"), heads,
        hjust=0, size=12, color="#0072B2",
        fill="none", label_color="none", label_padding=0,
    )
    + annotate("text", x=[0, 1], y=0.9, label=["source", "rendered"],
               ha="left", size=9, color="#888888")
    + scale_x_continuous(limits=(0, 1.8), expand=(0, 0))
    + scale_y_continuous(expand=(0.02, 0))
    + labs(title="**ggtext** syntax cheatsheet")
    + theme_void()
    + theme(
        figure_size=(8.5, 10),
        dpi=120,
        plot_margin=0.03,
        plot_title=element_markdown(size=16, ha="left"),
    )
)  # fmt: skip

if __name__ == "__main__":
    p.save(OUT / "syntax_cheatsheet.png", verbose=False)
    print("wrote", OUT / "syntax_cheatsheet.png")
