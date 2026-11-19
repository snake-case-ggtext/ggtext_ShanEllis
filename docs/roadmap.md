# Roadmap and known limitations

Feedback and pull requests are welcome. The items below are roughly ordered by how much they would help.

## Not yet ported from R ggtext

- **`align_widths` / `align_heights`** for `element_markdown`: give every tick label box the same width/height, so boxed tick labels line up. Each tick label is a separate artist, so this needs a small shared "group" object that measures all labels first.
- **`rotate_margins`** for `element_markdown`.

## Known limitations

- **`usetex=True`** isn't supported. The text falls back to plain TeX rendering with a warning. Mixing LaTeX with styled runs would need a different measuring strategy.
- **Images rotate only in steps of 90°.** At other angles they're drawn upright (with a warning).
- **Image vertical alignment** is fixed: images sit on the baseline. A CSS `vertical-align: middle` for images would help icons line up with lowercase text.
- **Wrapping** breaks at whitespace only. There's no hyphenation and no `text-align: justify`. Use a non-breaking space (`&nbsp;`) to keep two words on the same line.
- **Kerning across style changes** is approximate, because each run is measured on its own.
- **Legend keys** (the little glyph drawn by `geom_richtext` in a legend) are plain text ("a"), as for `geom_text`.
- `<p>` and `<div>` only start new lines. There's no paragraph spacing.

## Ideas

- **Upstream hooks.** Propose a documented text-layout protocol in matplotlib and an element hook in plotnine (see [design.md](design.md#a-path-upstream)), so the private-API pieces can go away.
- **Text on a path** (curved labels).
- **Per-run path effects** (e.g. `<span style='outline: 2px white'>`), which highlight_text users like.
- **`font-feature-settings`** (OpenType features) via matplotlib 3.11's `fontfeatures`.
- **Lists and simple tables** in text boxes (`- item` → bullet lines).
- **A `ggtext.style()` context manager** to set default rich text options for a block of matplotlib code.
- **Accessibility:** add the plain text (`get_plain_text()`) as alt/description text in SVG output.
- **Performance:** cache parsed and measured layouts across artists that share the same text (e.g. repeated facet labels).
