# Getting started

## Install

```bash
pip install "ggtext[plotnine]"   # matplotlib + plotnine helpers
pip install ggtext               # matplotlib only
```

| You have | You get |
|---|---|
| Python 3.10 | matplotlib 3.10.x (matplotlib 3.11 needs Python ≥ 3.11) |
| Python ≥ 3.11 | matplotlib 3.11.x |

ggtext works with both. It depends only on matplotlib, numpy, and [`markdown-it-py`](https://markdown-it-py.readthedocs.io/), the CommonMark parser used across the Jupyter ecosystem. plotnine is optional (version 0.15).

To install the development version from a local clone:

```bash
pip install -e ".[plotnine]"
```

## Your first plotnine plot

Write Markdown or HTML in any label, then tell the theme to render that piece of text as rich text with `element_markdown()`:

```python
from plotnine import ggplot, aes, geom_point, labs, theme
from plotnine.data import mtcars
from ggtext import element_markdown

(
    ggplot(mtcars, aes("wt", "mpg"))
    + geom_point()
    + labs(
        title="Heavier cars use **more fuel**",
        x="Weight (1000 lb)",
        y="Fuel economy, *mpg*",
    )
    + theme(
        plot_title=element_markdown(size=14),
        axis_title_y=element_markdown(),
    )
)
```

Only the themeables you set use rich text. A label is parsed as Markdown only if its theme element is an `element_markdown` (or a textbox element). To turn rich text on everywhere at once, use the `text` themeable:

```python
theme(text=element_markdown())
```

`element_markdown()` takes everything `element_text()` takes (`size`, `color`, `family`, `ha`, `rotation`, `margin`, ...), so you can swap one for the other.

### Long text that wraps

```python
from ggtext import element_textbox_simple

theme(plot_subtitle=element_textbox_simple(size=10, fill="#F2F2F2", padding=5, r=4))
```

The subtitle is word-wrapped to the width of the panel area. Wrapped lines keep their styles.

### Labels in the data

```python
from ggtext import geom_richtext, geom_textbox

ggplot(df, aes("x", "y", label="label")) + geom_richtext(angle=20)
```

## Your first matplotlib plot

The helpers mirror matplotlib's functions and take the same arguments:

```python
import matplotlib.pyplot as plt
import ggtext

fig, ax = plt.subplots(layout="constrained")
ax.plot([1, 2, 3], [2, 4, 3])

ggtext.set_title(ax, "Sales **peaked** in <span style='color:#D55E00'>February</span>")
ggtext.set_ylabel(ax, "Revenue (USD 10<sup>3</sup>)")
ggtext.text(ax, 2, 2.5, "x<sub>i</sub> marks the spot", ha="center")
```

You can also convert text that already exists:

```python
ax.set_xlabel("Month, *2025*")
ggtext.richify(ax.xaxis.label)
```

Or pass `richtext=True` wherever matplotlib accepts text properties:

```python
ax.text(0.5, 0.5, "**bold** text", richtext=True)
```

## Next steps

- See everything you can write in the [syntax reference](syntax.md).
- Browse the [gallery](gallery.md) and run the scripts in `examples/`.
- Work through the notebook tour, `examples/ggtext_tour.ipynb`.
