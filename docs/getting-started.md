# Getting started

## Install

```bash
pip install ggtext   # also installs matplotlib, plotnine, and pandas
```

| You have | You get |
|---|---|
| Python 3.10 | matplotlib 3.10.x (matplotlib 3.11 needs Python ≥ 3.11) |
| Python ≥ 3.11 | matplotlib 3.11.x |

ggtext works with both. It depends on matplotlib, numpy, plotnine (version 0.15), pandas, and [ggIR](https://github.com/snake-case-ggtext/ggIR), which parses the markup with [`markdown-it-py`](https://markdown-it-py.readthedocs.io/), the CommonMark parser used across the Jupyter ecosystem. All of them are installed with ggtext.

To install the development version from a local clone:

```bash
pip install -e .
```

## Your first plotnine plot

Write Markdown or HTML in any label. Then tell the theme to render that piece of text as rich text with `element_markdown()`:

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

Only the themeables you set use rich text. ggtext parses a label as Markdown only if its theme element is an `element_markdown` (or a textbox element). To turn rich text on everywhere at once, use the `text` themeable:

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

## Next steps

- See everything you can write in the [syntax reference](syntax.md).
- Browse the [gallery](gallery.md) and run the scripts in `examples/`.
- Work through the notebook tour, `examples/ggtext_tour.ipynb`.
