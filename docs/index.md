# ggtext documentation

ggtext renders **Markdown, HTML, and inline CSS** in matplotlib and plotnine plots. Use it to make a word in a title bold, color part of a label, write units with superscripts, put a small image in a tick label, or wrap a long subtitle to the width of the plot.

```python
from ggtext import element_markdown
theme(plot_title=element_markdown())   # plotnine

import ggtext
ggtext.set_title(ax, "A **rich** title")  # matplotlib
```

## Contents

| Page | What's in it |
|---|---|
| [Getting started](getting-started.md) | Install and make your first plotnine and matplotlib plots |
| [Syntax reference](syntax.md) | Every Markdown feature, HTML tag, and CSS property; math, images, escaping, units |
| [plotnine guide](plotnine.md) | `element_markdown`, `element_textbox`, `element_textbox_simple`, `geom_richtext`, `geom_textbox`, and an R → Python translation table |
| [matplotlib guide](matplotlib.md) | `RichText`, `text`, `textbox`, `annotate`, `richify`, `rich_ticklabels`, the `set_*` helpers |
| [Gallery](gallery.md) | Every example image with the code that produced it |
| [How it works](design.md) | The design, and the answer to plotnine issue #612 |
| [Comparison](comparison.md) | ggtext (R), flexitext, and highlight_text side by side |
| [Roadmap](roadmap.md) | Known limitations and ideas for the future |

## Three ideas to keep in mind

1. **Rich text is still a matplotlib `Text`.** Everything you know about `Text` still applies: `color`, `fontsize`, `rotation`, `ha`, `va`, `alpha`, `path_effects`. Those properties set the default style, and the markup changes parts of it.
2. **Layout just works.** Rich text is measured like any other text, so plotnine, `constrained_layout`, `tight_layout`, and `bbox_inches="tight"` all make room for it.
3. **Python conventions first.** `\n` starts a new line (as everywhere else in matplotlib), `snake_case_names` stay literal, options use `snake_case`, and ggplot2 spellings such as `colour`, `hjust`, and `box.colour` are accepted as aliases.
