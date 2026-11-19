# Comparison with ggtext (R), flexitext, and highlight_text

These three projects tackle the same problem, styling parts of a label, in different ways. This page tries to be fair about what each does well.

| | **ggtext (this package)** | **ggtext (R)** | **flexitext** | **highlight_text** |
|---|---|---|---|---|
| Language / stack | Python, matplotlib, plotnine | R, ggplot2, grid | Python, matplotlib | Python, matplotlib |
| Markup | Markdown + HTML + CSS subset | Markdown + HTML + CSS subset | own tags: `<color:red, size:12>text</>` | `<highlighted>` substrings + a list of style dicts |
| Theme elements (titles, axis titles) | ✅ `element_markdown`, `element_textbox(_simple)` | ✅ | ❌ (place text manually) | ❌ |
| Rich tick labels | ✅ any angle | ✅ (`element_markdown`) | ❌ | ❌ |
| Facet strips, legend text | ✅ | ✅ | ❌ | ❌ |
| Labels in the data (geoms) | ✅ `geom_richtext`, `geom_textbox` | ✅ | ❌ | ❌ |
| Seen by layout engines | ✅ (a real `Text`) | ✅ (grobs) | ❌ (offset box) | ❌ (offset box) |
| Rotation | ✅ any angle, boxes too | ✅ for `richtext`; textboxes only 0/90/180/270 | ❌ | ❌ |
| Word wrapping | ✅ fixed / max / fractional width | ✅ | ❌ | ❌ |
| Boxes (fill, outline, rounded corners, padding) | ✅ | ✅ | ❌ | partial (via `AnnotationBbox`) |
| Bold / italic / color / size / family | ✅ | ✅ | ✅ | ✅ |
| Super/subscript | ✅ | ✅ | ❌ | ❌ |
| Underline / strikethrough / highlight | ✅ | ❌ | ❌ | ✅ highlight via path effects / bbox |
| Inline images | ✅ files, URLs, data URIs, numpy arrays | ✅ files, URLs | ❌ | ❌ |
| Math | ✅ mathtext inside rich text | ❌ (use `plotmath` separately) | ❌ | ❌ |
| Hyperlinks (SVG/PDF) | ✅ | ❌ | ❌ | ❌ |
| Any matplotlib text property per run | ⚠️ the CSS subset only | n/a | ✅ any `Text` kwarg | ✅ any `Text` kwarg |
| Equal-width tick boxes (`align_widths`) | ⏳ not yet | ✅ | ❌ | ❌ |
| `minwidth` / `minheight` / `maxheight` | ✅ | ✅ | ❌ | ❌ |
| Geoms: rotation around the anchor, `inward`/`outward`, mappable outline colors | ✅ | ✅ | ❌ | ❌ |

## When to use which

- **ggtext (this package):** you want rich text in plot furniture (titles, axes, ticks, strips, legends) in plotnine or matplotlib. The package handles layout.
- **highlight_text:** you want to highlight a few words in an annotation with per-word matplotlib properties, such as path effects. You place the text yourself.
- **flexitext:** a small, dependency-light way to style parts of an annotation with a compact tag syntax.
- **R ggtext:** you're in R. Its `align_widths` option is still ahead of this port.

## Differences from R ggtext in detail

- **Newlines.** Python: `\n` is a line break by default (`newline="space"` gives R's behavior).
- **Units.** Sizes are points; widths are fractions of the panel area or strings with units (`"2in"`), not grid `unit()`s. Box widths and heights exclude margins (R includes them).
- **Images** without a size are as tall as the font (R: natural pixel size).
- **Relative sizes** in CSS (`em`, `%`, `large`) are relative to the surrounding text.
- **Rotation** works at any angle for every element and geom.
- **Extras:** underline, strikethrough, `<mark>`, inline code, links, mathtext, `register_image`.
