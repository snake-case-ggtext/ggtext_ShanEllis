# ggtext documentation

ggtext renders **Markdown, HTML, and inline CSS** in plotnine plots. Use it to make a word in a title bold or color part of a label. Other uses: superscript units, small images in tick labels, and long subtitles wrapped to the plot width.

```python
from ggtext import element_markdown

theme(plot_title=element_markdown())
```

## Contents

| Page | What's in it |
|---|---|
| [Getting started](getting-started.md) | Install and make your first plot |
| [Syntax reference](syntax.md) | Every Markdown feature, HTML tag, and CSS property; math, images, escaping, units |
| [plotnine guide](plotnine.md) | `element_markdown`, `element_textbox`, `element_textbox_simple`, `geom_richtext`, `geom_textbox`, and an R → Python translation table |
| [Gallery](gallery.md) | Every example image with the code that produced it |
| [How it works](design.md) | The design, and the answer to plotnine issue #612 |
| [Comparison](comparison.md) | ggtext (R), flexitext, and highlight_text side by side |
| [Roadmap](roadmap.md) | Known limitations and ideas for the future |

## Three ideas to keep in mind

1. **Rich text is still a matplotlib `Text`.** All `Text` properties still apply: `color`, `fontsize`, `rotation`, `ha`, `va`, `alpha`, `path_effects`. Those properties set the default style, and the markup changes parts of it.
2. **Layout just works.** Layout engines measure rich text like any other text. As a result, plotnine's layout and `bbox_inches="tight"` make room for it.
3. **Python conventions first.** `\n` starts a line (as everywhere else in matplotlib). `snake_case_names` stay literal, options use `snake_case`, and ggplot2 spellings such as `colour`, `hjust`, and `box.colour` work as aliases.
