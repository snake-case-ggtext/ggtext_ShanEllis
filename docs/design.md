# How it works, and the answer to plotnine #612

## The question

[plotnine issue #612](https://github.com/has2k1/plotnine/issues/612) asked for ggtext-style rich text in plotnine. The maintainer's answer was that the matplotlib graphics stack makes it "nearly impossible", and that it would need long-term work.

**Short answer: it is possible today, without changing plotnine or matplotlib.** This page explains why it looked impossible, what ggtext does instead, and where the sharp edges are.

## Why it looked impossible

A matplotlib [`Text`](https://matplotlib.org/stable/api/text_api.html) artist draws *one* string in *one* style: one font, one size, one color. Rich text needs several styles inside one label.

The obvious workaround is to draw several `Text` artists side by side. That is what [flexitext](https://github.com/tomicapretto/flexitext) and [highlight_text](https://github.com/znstrider/highlight_text) do. They pack `TextArea`s into `HPacker`/`VPacker` offset boxes inside an `AnnotationBbox`. That works for annotations, but not for plot furniture:

1. **Layout engines can't see it.** plotnine's layout engine, like matplotlib's `constrained_layout`, decides how much room to leave for the title, the axis labels, and the legend. It does that by asking the *existing* `Text` artists for their size. A separate offset box isn't one of those artists, so no room is reserved for it.
2. **It can't rotate.** Offset boxes are always axis-aligned. A y-axis title needs 90°, and rotated tick labels need arbitrary angles.
3. **It can't replace plotnine's artists.** plotnine creates its own `Text` objects for titles, tick labels, strips, and legends, and styles them through the theme. A rich-text solution has to work through those objects, not next to them.

## What ggtext does instead

### 1. `RichText` *is* a `Text`

Everything in matplotlib that needs to know how big a piece of text is goes through one private method, `Text._get_layout(renderer)`. That includes `get_window_extent()`, `TextArea` (legends), the layout engines, `bbox_inches="tight"`, `adjustText`, and plotnine's layout.

`ggtext.RichText` subclasses `Text` and overrides exactly two methods:

| Method | What the override does |
|---|---|
| `_get_layout(renderer)` | parses the markup → measures each styled run with the renderer → wraps and stacks lines → applies rotation and the `ha`/`va`/`rotation_mode` alignment **with the same arithmetic as `Text`** → returns the result in the format the installed matplotlib expects |
| `draw(renderer)` | draws the optional box, then each run with `renderer.draw_text()` at the computed positions, rotated about the text's anchor; underlines, strikethroughs, highlights, and images are drawn as paths or images |

Every other `Text` method keeps working (`set_color`, `set_fontsize`, `set_rotation`, `set_position`, ...). Those properties become the default style for the unstyled parts of the text.

Parsing comes from [ggIR](https://github.com/snake-case-ggtext/ggIR), which turns markdown, HTML and inline CSS into a renderer-independent document tree. `ggir.resolve` then turns the tree into styled tokens (sizes in points, sup/sub shifts), with ggtext supplying only its numbers (`GGTEXT_POLICY` in `ggtext/_parse.py`: sup/sub scale and shift, the default em) and matplotlib color validation. The token resolution and line layout (`ggtext/_layout.py`) are renderer-independent and are unit-tested with a fake measurer. Only the measuring and drawing code talks to matplotlib.

### 2. Exact geometry parity with `Text`

If rich text were measured even a pixel differently from plain text, swapping `element_text` for `element_markdown` would shift titles around. So ggtext reproduces matplotlib's own rules:

- The **alignment code** (`ha`, `va` including `baseline` and `center_baseline`, `rotation_mode` `default`/`anchor`/`xtick`/`ytick`) mirrors `Text._get_layout`.
- **Line heights** differ between matplotlib versions. matplotlib 3.10 uses the box of the string `"lp"` and scales the ascent of later lines by `linespacing`. matplotlib 3.11 uses the font's typographic ascent, descent, and line gap, and a numeric `linespacing` gives every line a fixed height. ggtext implements both models (`line_model="mpl310"` / `"mpl311"`) and reads the font metrics by asking throw-away `Text` objects for their layout. That way, matplotlib computes the numbers itself.
- matplotlib 3.10 places the `"baseline"` of multi-line text slightly differently from 3.11. ggtext matches that too.

The test suite checks this: `tests/test_artist.py::test_extent_matches_plain_text` compares the extents of a plain `Text` and a `RichText` with the same string across 5 rotations × 3 `ha` × 5 `va` × 2 rotation modes × several strings. A separate stress check over line spacings 0.9–1.5 and font sizes 8–20 found differences of **0.0 px** on both matplotlib 3.10 and 3.11.

### 3. Version-specific `_get_layout` formats

`_get_layout` is private, and its return value changed in matplotlib 3.11:

| matplotlib | returns |
|---|---|
| 3.10 | `(bbox, [(line, (width, height), x, y), ...], descent)` |
| 3.11 | `(bbox, [(line, (width, ascent, descent), (x, y)), ...], ((x, y), (width, height)))` |

`RichText._get_layout` returns whichever shape the installed matplotlib uses, because callers such as `TextArea.get_bbox` (legends) and `Text.update_bbox_position_size` (the `bbox=`/`backgroundcolor` patch) unpack it.

### 4. Hooking into plotnine: the `richtext` property

plotnine never needs to know about ggtext. Every text themeable applies its element in the same way:

```python
text_artist.set(**element.properties)
```

Importing ggtext registers one new property on `matplotlib.text.Text`:

```python
Text.set_richtext = ...   # and Text.get_richtext
```

`element_markdown()` is an `element_text` with one extra entry in its properties, `richtext=RichTextSpec(...)`. When plotnine applies the theme, `text.set(..., richtext=spec)` calls `set_richtext`, which turns that artist into rich text **in place**.

- This only *adds* a property; existing `Text` behavior is unchanged, and plain text is never touched.
- It works for every themeable at once, including ones plotnine adds in the future, because they all go through `.set()`.
- It survives theme merging. When `theme_bw()` already defines `plot_title`, plotnine merges the property dictionaries but keeps the *original* element object. A hook based on the element's class would be lost there; a property in the dictionary is not.
- It also works in plain matplotlib: `ax.text(..., richtext=True)`, `plt.setp(labels, richtext=True)`.

### 5. In-place class swap

"In place" means the artist's class is swapped: `text.__class__ = RichText`. plotnine (and matplotlib) keep references to their artists in many places: theme targets, axis ticks, legend boxes. Swapping the class means every one of those references now points to a rich artist, and nothing has to be replaced.

Some artists are *subclasses* of `Text`, such as plotnine's `StripText` (which positions itself inside the strip background) or matplotlib's `Annotation`. For a subclass `X`, ggtext creates `RichX(X, RichText)` once and caches it. The method resolution order is `RichX → X → RichText → Text`, so `X`'s own behavior runs first, and its `super().draw()` reaches `RichText.draw`. These dynamic classes get unique module-level names so figures stay picklable.

`Annotation` is special: its `draw()` calls `Text.draw(self, ...)` explicitly instead of using `super()`. `RichAnnotation` gets a `draw` that repeats Annotation's steps (position update, arrow) and then calls `RichText.draw`.

### 6. Two-pass layout

`element_textbox_simple()` wraps a subtitle to the width of the *panel area*. But plotnine's layout engine measures all texts **before** it moves the panels into place. On the first measurement, the panels are still at their initial positions, which are usually wider than the final ones. The subtitle would wrap into, say, two lines, plotnine would reserve space for two lines, and then it would be drawn with three.

matplotlib's own `constrained_layout` iterates for exactly this kind of reason. ggtext does the same, but only for figures that contain rich text with a *fractional* width or height. For those figures it wraps that figure's layout engine so `execute()` runs twice. The second pass measures against the settled panel positions. A subtitle's height doesn't change the panel *widths*, so two passes are enough. (The wrapper is set up when plotnine calls `figure.set_layout_engine()`, and it's a small picklable class, not a closure.)

### 7. Plot compositions

In a composition (`p1 | p2`, `p1 / p2`), a figure holds several plots, and "the panel area" has to mean *the panels of the plot this title belongs to*. The plotnine integration registers a resolver (`ggtext._artist.register_panel_resolver`, implemented in `ggtext/plotnine/layout.py`). It asks plotnine's layout engine which plot owns the text, then uses that plot's axes. Plain matplotlib figures fall back to the union of all axes.

## The private-API risk, and how it's managed

ggtext relies on private matplotlib APIs:

| Private API | Why | Guard |
|---|---|---|
| `Text._get_layout` (override and format) | the single measurement hook | version-specific formats; parity tests on 3.10 and 3.11; `TextArea`/`bbox`/annotation tests exercise the callers |
| `Text._get_layout` on proxy texts | read font metrics exactly as matplotlib computes them | line-height parity tests |
| `Text._get_multialignment`, `_get_wrap_line_width`, `_set_gc_clip` | reuse `Text` behavior | covered by alignment, wrap, and clip tests |
| `Axis._copy_tick_props` (wrapped per axis instance, in `rich_ticklabels`) | keep newly created ticks rich | tick tests |
| `LayoutEngine.execute` (wrapped per figure instance) | two-pass layout | relayout tests |

The suite runs on Python 3.10 + matplotlib 3.10 and on Python 3.11–3.13 + matplotlib 3.11 (Linux, macOS, Windows). A matplotlib release that changes `_get_layout` again will fail the parity tests immediately, and the fix belongs in one function.

## Limitations

- `usetex=True` is not supported (the text is drawn as plain TeX, with a warning).
- Images rotate only in steps of 90°.
- Wrapping breaks at whitespace only (no hyphenation or justification).
- Word-wrapped text measures each word separately, so kerning *between* words of different styles is approximate. Kerning within a run is exact.
- `align_widths`/`align_heights` (equal-width boxes for all tick labels) is not implemented yet.

The [roadmap](roadmap.md) has more.

## A path upstream

This approach could move into the core libraries in small steps:

1. **matplotlib:** make `_get_layout` (or a documented "text layout" protocol) public so third-party text artists can take part in layout without relying on private details. That would remove most of the version-specific code here.
2. **plotnine:** accept a `RichText`-like artist class per themeable, or call a documented hook when applying text elements. Then the `richtext` property and the class swap aren't needed. plotnine's layout engine could also iterate once more when text sizes depend on panel sizes, removing the need for the two-pass wrapper.
3. **plotnine:** ship `element_markdown`/`geom_richtext` built on such a hook, with ggtext as the reference implementation.

Until then, ggtext works with released versions of both libraries.
