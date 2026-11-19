"""
A visual cheatsheet: every supported syntax element next to its source.

Run:  python examples/10_syntax_cheatsheet.py
"""

import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import ggtext  # noqa: E402

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

fig = plt.figure(figsize=(8.5, 10), dpi=120)
ggtext.set_suptitle(fig, "**ggtext** syntax cheatsheet", fontsize=16, x=0.06, ha="left", y=0.985)
fig.text(0.06, 0.945, "source", fontsize=9, color="#888888", family="monospace")
fig.text(0.62, 0.945, "rendered", fontsize=9, color="#888888")

y = 0.915
for source, _ in ROWS:
    if source in ("Markdown", "HTML", "Math"):
        y -= 0.008
        ggtext.text(fig, 0.06, y, f"**{source}**", fontsize=12, color="#0072B2", va="center")
        y -= 0.036
        continue
    fig.text(0.06, y, source, fontsize=8.5, family="monospace", color="#333333",
             va="center", parse_math=False)  # fmt: skip
    ggtext.text(fig, 0.62, y, source, fontsize=11, va="center")
    height = 0.055 if "<br>" in source else 0.037
    y -= height

if __name__ == "__main__":
    fig.savefig(OUT / "syntax_cheatsheet.png", bbox_inches="tight", pad_inches=0.3)
    print("wrote", OUT / "syntax_cheatsheet.png")
