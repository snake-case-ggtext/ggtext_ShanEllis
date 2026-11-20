# Changelog

This file lists all notable changes to this project. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [semantic versioning](https://semver.org/).

## [0.1.0] - unreleased

First release: a Python take on R's ggtext for plotnine.

### Added

- **Rich text in plotnine**, drawn by an internal `matplotlib.text.Text` subclass that renders Markdown, HTML, and inline CSS and is measured exactly like plain text. Works with matplotlib 3.10 and 3.11.
- **Markup:** CommonMark inline Markdown (via `markdown-it-py`). HTML tags: `b`, `strong`, `i`, `em`, `u`, `ins`, `s`, `del`, `strike`, `sup`, `sub`, `br`, `span`, `font`. More HTML tags: `code`, `kbd`, `tt`, `samp`, `small`, `big`, `mark`, `a`, `p`, `div`, and `img`. CSS properties: `color`, `font-size`, `font-family`, `font-weight`, `font-style`, `font-variant`, `background-color`, `text-decoration`, and `vertical-align`. Mathtext (`$...$`) works inside rich text.
- **Boxes and wrapping:** `width`, `maxwidth`, and `height` (fixed units or fractions of the panel area). Also `padding`, `fill`, `box_color`, `linewidth`, `linestyle`, rounded corners `r`, `halign`, and `valign`. Everything rotates to any angle.
- **Images:** local files, data URIs, URLs, and in-memory arrays via `register_image()`.
- **plotnine integration:** `element_markdown`, `element_textbox`, `element_textbox_simple`, `geom_richtext`, `geom_textbox`. They work for every text themeable (titles, axis titles, tick labels, strips, legends, tag) and in plot compositions. The package accepts ggplot2 argument spellings as aliases.
- Two-pass layout for figures that contain text whose width depends on the panel size.
- **ggtext conventions in the geoms:** labels and text boxes rotate around their anchor point (`rotation_mode="anchor"`, overridable). `ha`/`va` (aliases `hjust`/`vjust`) accept names, numbers in [0, 1], and `"inward"`/`"outward"`. The lines of a `geom_richtext` label follow its `ha` (gridtext) unless you set `halign`. `label_color`, `label_size`, `text_color` (and `box_color`, `box_size` for `geom_textbox`) are aesthetics that you can map to data.
- **Margins and size limits:** `margin` on rich text (`label_margin`, `box_margin` in the geoms). `minwidth`, `maxwidth`, `minheight`, `maxheight` with ggtext's semantics. `height` is a fixed box height (text may overflow), as in ggtext.
- **Numeric alignment:** `RichText` accepts `ha`/`va` numbers in [0, 1].
- Documentation, a gallery of runnable examples, and a notebook tour. A test suite runs on Python 3.10 + matplotlib 3.10 and Python 3.11–3.13 + matplotlib 3.11.
