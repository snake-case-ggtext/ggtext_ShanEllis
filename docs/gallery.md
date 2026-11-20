# Gallery

Every image in the documentation, with the code that made it. The scripts live in `examples/`; run `python examples/run_all.py` to regenerate the images and `python examples/make_gallery.py` to rebuild this page.

| Example | Script |
|---|---|
| [Quickstart: rich text in a plotnine plot](#quickstart-plotnine) | `examples/01_quickstart_plotnine.py` |
| [Titles, subtitles and captions](#titles-and-subtitles) | `examples/03_titles_and_subtitles.py` |
| [Axis titles and tick labels](#axis-and-tick-labels) | `examples/04_axis_and_tick_labels.py` |
| [Facet strips and legends](#facet-strips-and-legends) | `examples/05_facet_strips_and_legends.py` |
| [geom_richtext: rich text labels, with or without a box, at any angle](#geom-richtext) | `examples/06_geom_richtext.py` |
| [geom_textbox: word-wrapped rich text in boxes of a fixed width](#geom-textbox) | `examples/07_geom_textbox.py` |
| [Images inside text: &lt;img&gt; tags in tick labels and titles](#images-in-labels) | `examples/08_images_in_labels.py` |
| [A visual cheatsheet: every supported syntax element next to its source](#syntax-cheatsheet) | `examples/10_syntax_cheatsheet.py` |
| [Plot compositions: rich text in p1 \| p2](#plot-composition) | `examples/11_plot_composition.py` |

<a id="quickstart-plotnine"></a>

## Quickstart: rich text in a plotnine plot

The colored words in the title double as the legend, so the legend
itself can be dropped. This is the classic ggtext use case.

![Quickstart: rich text in a plotnine plot](images/quickstart_plotnine.png)

<details><summary>Code: <code>examples/01_quickstart_plotnine.py</code></summary>

```python
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

from ggtext import element_markdown

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
```

</details>

<a id="titles-and-subtitles"></a>

## Titles, subtitles and captions

- The title uses colored words as an inline legend (element_markdown).
- The long subtitle is word-wrapped to the width of the panel area
  (element_textbox_simple), with a light background box.
- The caption mixes italics and a link-style source note.

![Titles, subtitles and captions](images/titles_and_subtitles.png)

<details><summary>Code: <code>examples/03_titles_and_subtitles.py</code></summary>

```python
"""
Titles, subtitles and captions.

- The title uses colored words as an inline legend (element_markdown).
- The long subtitle is word-wrapped to the width of the panel area
  (element_textbox_simple), with a light background box.
- The caption mixes italics and a link-style source note.

Run:  python examples/03_titles_and_subtitles.py
"""

import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from plotnine import (
    aes,
    geom_line,
    ggplot,
    labs,
    scale_color_manual,
    scale_x_datetime,
    theme,
    theme_minimal,
)
from plotnine.data import economics_long

from ggtext import element_markdown, element_textbox_simple

# Images go to docs/images/; tests redirect them with GGTEXT_EXAMPLES_OUT
OUT = Path(
    os.environ.get("GGTEXT_EXAMPLES_OUT")
    or Path(__file__).resolve().parent.parent / "docs" / "images"
)
OUT.mkdir(parents=True, exist_ok=True)

BLUE, ORANGE = "#0072B2", "#D55E00"

df = economics_long[economics_long["variable"].isin(["psavert", "uempmed"])]

title = (
    f"<span style='color:{BLUE}'>**Personal savings rate**</span> and "
    f"<span style='color:{ORANGE}'>**unemployment duration**</span>, 1967–2015"
)
subtitle = (
    "This subtitle is drawn with **element_textbox_simple()**: it is "
    "word-wrapped to the width of the panel area, so you can write a real "
    "sentence or two about what the reader should notice. Styles such as "
    "*italics*, <span style='color:#0072B2'>**colored bold text**</span> and "
    "units like m<sup>2</sup> survive the line breaks."
)

p = (
    ggplot(df, aes("date", "value", color="variable"))
    + geom_line(size=0.8)
    + scale_color_manual(values={"psavert": BLUE, "uempmed": ORANGE})
    + scale_x_datetime(date_labels="%Y")
    + labs(
        title=title,
        subtitle=subtitle,
        x="",
        y="",
        caption="Source: *economics_long* (US FRED data) bundled with plotnine",
    )
    + theme_minimal()
    + theme(
        figure_size=(8, 5),
        legend_position="none",
        plot_title=element_markdown(size=14, ha="left"),
        plot_subtitle=element_textbox_simple(
            size=10,
            color="#333333",
            fill="#F2F2F2",
            padding=(6, 8),
            r=4,
            margin={"t": 4, "b": 10},
        ),
        plot_caption=element_markdown(size=8, color="#666666"),
    )
)

if __name__ == "__main__":
    p.save(OUT / "titles_and_subtitles.png", dpi=130, verbose=False)
    print("wrote", OUT / "titles_and_subtitles.png")
```

</details>

<a id="axis-and-tick-labels"></a>

## Axis titles and tick labels

- Axis titles with units written with <sub>/<sup>.
- Rich tick labels: each category label has its own style, and the
  labels are rotated (any angle works).

![Axis titles and tick labels](images/axis_and_tick_labels.png)

![Axis titles and tick labels](images/axis_and_tick_labels_flipped.png)

<details><summary>Code: <code>examples/04_axis_and_tick_labels.py</code></summary>

```python
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

import pandas as pd
from plotnine import (
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

from ggtext import element_markdown

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
    + scale_fill_manual(
        values={"electric": "#009E73", "hybrid": "#56B4E9", "gas": "#999999"}
    )
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
    + theme(
        axis_text_x=element_markdown(rotation=0, ha="center"),
        axis_text_y=element_markdown(size=10, ha="right"),
        axis_title_x=element_markdown(size=11),
    )
)

if __name__ == "__main__":
    p.save(OUT / "axis_and_tick_labels.png", dpi=130, verbose=False)
    p2.save(OUT / "axis_and_tick_labels_flipped.png", dpi=130, verbose=False)
    print("wrote", OUT / "axis_and_tick_labels.png")
    print("wrote", OUT / "axis_and_tick_labels_flipped.png")
```

</details>

<a id="facet-strips-and-legends"></a>

## Facet strips and legends

- Facet labels built with a labeller function that returns markup.
- Legend title on two lines, with a smaller grey second line.
- Legend labels with mixed styles.

![Facet strips and legends](images/facet_strips_and_legends.png)

<details><summary>Code: <code>examples/05_facet_strips_and_legends.py</code></summary>

```python
"""
Facet strips and legends.

- Facet labels built with a labeller function that returns markup.
- Legend title on two lines, with a smaller grey second line.
- Legend labels with mixed styles.

Run:  python examples/05_facet_strips_and_legends.py
"""

import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from plotnine import (
    aes,
    facet_wrap,
    geom_point,
    ggplot,
    labs,
    scale_color_manual,
    theme,
    theme_bw,
)
from plotnine.data import penguins

from ggtext import element_markdown

# Images go to docs/images/; tests redirect them with GGTEXT_EXAMPLES_OUT
OUT = Path(
    os.environ.get("GGTEXT_EXAMPLES_OUT")
    or Path(__file__).resolve().parent.parent / "docs" / "images"
)
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
```

</details>

<a id="geom-richtext"></a>

## geom_richtext: rich text labels, with or without a box, at any angle

Unlike plotnine's geom_label, boxed labels can be rotated.

![geom_richtext: rich text labels, with or without a box, at any angle](images/geom_richtext.png)

<details><summary>Code: <code>examples/06_geom_richtext.py</code></summary>

```python
"""
geom_richtext: rich text labels, with or without a box, at any angle.

Unlike plotnine's geom_label, boxed labels can be rotated.

Run:  python examples/06_geom_richtext.py
"""

import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd
from plotnine import (
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

from ggtext import element_markdown, geom_richtext

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
        "label": [
            f"**{a}°** <span style='color:#D55E00'>*rich*</span>" for a in angles
        ],
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
        aes(label="label"),
        data=center,
        fill=None,
        label_size=0,
        size=10,
        color="#333333",
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
```

</details>

<a id="geom-textbox"></a>

## geom_textbox: word-wrapped rich text in boxes of a fixed width

Handy for annotating a plot with a few sentences.

![geom_textbox: word-wrapped rich text in boxes of a fixed width](images/geom_textbox.png)

<details><summary>Code: <code>examples/07_geom_textbox.py</code></summary>

```python
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
```

</details>

<a id="images-in-labels"></a>

## Images inside text: &lt;img&gt; tags in tick labels and titles

To keep this example self-contained (no downloads, no files), the
"flags" are tiny numpy arrays registered with ggtext.register_image().
With real files you would write <img src='path/to/flag.png' width='20'>.

![Images inside text: &lt;img&gt; tags in tick labels and titles](images/images_in_labels.png)

<details><summary>Code: <code>examples/08_images_in_labels.py</code></summary>

```python
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
```

</details>

<a id="syntax-cheatsheet"></a>

## A visual cheatsheet: every supported syntax element next to its source

![A visual cheatsheet: every supported syntax element next to its source](images/syntax_cheatsheet.png)

<details><summary>Code: <code>examples/10_syntax_cheatsheet.py</code></summary>

```python
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
```

</details>

<a id="plot-composition"></a>

## Plot compositions: rich text in p1 | p2

Each plot's wrapped subtitle (element_textbox_simple, width=1) spans the
panel area of *its own* plot, not the whole figure.

![Plot compositions: rich text in p1 \| p2](images/plot_composition.png)

<details><summary>Code: <code>examples/11_plot_composition.py</code></summary>

```python
"""
Plot compositions: rich text in p1 | p2.

Each plot's wrapped subtitle (element_textbox_simple, width=1) spans the
panel area of *its own* plot, not the whole figure.

Run:  python examples/11_plot_composition.py
"""

import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from plotnine import (
    aes,
    geom_histogram,
    geom_point,
    ggplot,
    labs,
    scale_color_manual,
    scale_fill_manual,
    theme,
    theme_minimal,
)
from plotnine.data import penguins

from ggtext import element_markdown, element_textbox_simple

# Images go to docs/images/; tests redirect them with GGTEXT_EXAMPLES_OUT
OUT = Path(
    os.environ.get("GGTEXT_EXAMPLES_OUT")
    or Path(__file__).resolve().parent.parent / "docs" / "images"
)
OUT.mkdir(parents=True, exist_ok=True)

COLORS = {"Adelie": "#E69F00", "Chinstrap": "#56B4E9", "Gentoo": "#009E73"}
pg = penguins.dropna()

rich_theme = theme_minimal() + theme(
    plot_title=element_markdown(size=12),
    plot_subtitle=element_textbox_simple(
        size=9, fill="#F2F2F2", padding=4, r=3, margin={"b": 6}
    ),
    legend_position="none",
)

p1 = (
    ggplot(pg, aes("flipper_length_mm", fill="species"))
    + geom_histogram(bins=25, alpha=0.85)
    + scale_fill_manual(values=COLORS)
    + labs(
        title="**Flipper length**",
        subtitle=f"<span style='color:{COLORS['Gentoo']}'>**Gentoo**</span> penguins have "
        "clearly longer flippers; the other two species overlap.",
        x="mm",
        y="count",
    )
    + rich_theme
)

p2 = (
    ggplot(pg, aes("bill_length_mm", "bill_depth_mm", color="species"))
    + geom_point(alpha=0.8)
    + labs(
        title="**Bill shape**",
        subtitle=f"Bill depth separates <span style='color:{COLORS['Gentoo']}'>**Gentoo**</span>; "
        f"bill length separates <span style='color:{COLORS['Adelie']}'>**Adelie**</span> from the rest.",
        x="length (mm)",
        y="depth (mm)",
    )
    + scale_color_manual(values=COLORS)
    + rich_theme
)

composition = (p1 | p2) + theme(figure_size=(9, 4))

if __name__ == "__main__":
    composition.save(OUT / "plot_composition.png", dpi=130, verbose=False)
    print("wrote", OUT / "plot_composition.png")
```

</details>
