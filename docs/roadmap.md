# Roadmap and known limitations

Feedback and pull requests are welcome. The items below are roughly ordered by how much they would help.

Parsing (Markdown, HTML, inline CSS) now lives in [ggIR](https://github.com/snake-case-ggtext/ggIR). New tags or CSS properties, lists, tables and paragraph handling are parser work and start there; ggtext then lays out and draws what ggIR produces.

## Before a first release

- **Publish ggIR to PyPI, then ggtext.** ggtext depends on ggIR straight from GitHub (`ggir @ git+https://...`), and PyPI doesn't accept packages with such dependencies. Until then, install from GitHub: `pip install "ggtext[plotnine] @ git+https://github.com/snake-case-ggtext/ggtext_ShanEllis"`.

## Not yet ported from R ggtext

- **`align_widths` / `align_heights`** for `element_markdown`: give every tick label box the same width/height, so boxed tick labels line up. Each tick label is a separate artist, so this needs a small shared "group" object that measures all labels first.
- **`rotate_margins`** for `element_markdown`.
- **Box widths and margins.** In ggtext, a text box's `width`/`height` include its margins; here they are the size of the box itself, with `margin`/`box_margin`/`label_margin` added outside. Decide whether to switch to ggtext's meaning.

## Known limitations

- **`usetex=True`** isn't supported. The text falls back to plain TeX rendering with a warning. Mixing LaTeX with styled runs would need a different measuring strategy.
- **Images rotate only in steps of 90°.** At other angles they're drawn upright (with a warning).
- **Image vertical alignment** is fixed: images sit on the baseline. A CSS `vertical-align: middle` for images would help icons line up with lowercase text.
- **Wrapping** breaks at whitespace only. There's no hyphenation and no `text-align: justify`. Use a non-breaking space (`&nbsp;`) to keep two words on the same line.
- **Kerning across style changes** is approximate, because each run is measured on its own.
- **Legend keys** (the little glyph drawn by `geom_richtext` in a legend) are plain text ("a"), as for `geom_text`.
- `<p>` and `<div>` only start new lines. There's no paragraph spacing (parser support belongs in ggIR).
- **Image comparisons run in one environment only.** Text rasterizes differently across platforms and between the FreeType versions bundled with matplotlib 3.10 and 3.11, so the picture tests compare against baselines only on Linux with matplotlib 3.11 (elsewhere the plots are drawn and the comparison is skipped).

## Testing

- **Image tests for theme text:** titles, wrapped subtitles, axis titles and tick labels, facet strips, legends and tags are checked by geometry and pixel tests but not against baseline images (the image comparisons cover the two geoms).
- **Examples and notebook in the test suite:** the gallery examples (`python examples/run_all.py`) and `examples/ggtext_tour.ipynb` are run by hand.

## Less reliance on matplotlib internals

- **Opt-in `richtext` property.** `import ggtext` adds `set_richtext`/`get_richtext` to matplotlib's `Text`, which is what lets plotnine's theme elements become rich text. Make this an explicit opt-in (e.g. `ggtext.install()`, or done when the first `element_markdown` is created) so importing ggtext changes nothing globally.
- **Public methods where possible.** `RichText` overrides matplotlib's private `Text._get_layout()`. Titles, axis text and tick labels could be measured through the public `get_window_extent()` instead; legend text (matplotlib's `TextArea`) still needs `_get_layout()`. See [design.md](design.md) for the trade-offs.

## Ideas

- **Upstream hooks.** Propose a documented text-layout protocol in matplotlib and an element hook in plotnine (see [design.md](design.md#a-path-upstream)), so the private-API pieces can go away.
- **Text on a path** (curved labels).
- **Per-run path effects** (e.g. `<span style='outline: 2px white'>`), which highlight_text users like.
- **`font-feature-settings`** (OpenType features) via matplotlib 3.11's `fontfeatures`.
- **Lists and simple tables** in text boxes (`- item` → bullet lines); parsing would come from ggIR.
- **A `ggtext.style()` context manager** to set default rich text options for a block of matplotlib code.
- **Accessibility:** add the plain text (`get_plain_text()`) as alt/description text in SVG output.
- **Performance:** cache parsed and measured layouts across artists that share the same text (e.g. repeated facet labels).
