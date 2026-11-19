# Contributing to ggtext

Thanks for helping! Bug reports, docs fixes, examples, and features are all welcome. If you're planning something big, please open an issue first so we can talk it through.

## Development setup

We use [uv](https://docs.astral.sh/uv/), but plain `pip` + `venv` works too.

ggtext supports two version matrices, because **matplotlib 3.11 requires Python ≥ 3.11**:

| Environment | Python | matplotlib | plotnine |
|---|---|---|---|
| `.venv310` | 3.10 | 3.10.x | 0.15.x |
| `.venv311` | 3.11+ | 3.11.x | 0.15.x |

Set up both:

```bash
# Python 3.10 + matplotlib 3.10
uv venv -p 3.10 .venv310
source .venv310/bin/activate
uv pip install -e ".[dev]" "matplotlib>=3.10,<3.11"
deactivate

# Python 3.11 + matplotlib 3.11
uv venv -p 3.11 .venv311
source .venv311/bin/activate
uv pip install -e ".[dev]" "matplotlib>=3.11,<3.12"
```

With pip:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Make targets

```bash
make test         # pytest in random order (pytest-randomly) with coverage
make lint         # ruff check + ruff format --check + pyrefly (strict)
make pre-commit   # install the prek git hooks and run them on every file
```

Run `make pre-commit` once after cloning: the hooks then run ruff and pyrefly on every commit.

pyrefly runs in strict mode. Existing errors are recorded in `pyrefly-baseline.json`, so only new ones fail. After fixing typed code, shrink the baseline with `uv run pyrefly check --update-baseline`.

## Running the tests

Tests run in a random order (pytest-randomly). To reproduce a failure, rerun with the seed printed in the header: `pytest -p randomly --randomly-seed=<seed>`.

```bash
pytest                       # whole suite
pytest tests/test_parse.py   # one file
pytest -k tick               # by name
pytest --cov=ggtext          # with coverage
pytest --doctest-modules src/ggtext   # docstring examples
pytest -m image              # image comparisons only
pytest --update-baselines -m image   # rewrite image baselines (Linux + matplotlib 3.11 only)
```

`pip install -e ".[dev]"` includes the `notebook` extra, so the tour notebook is executed too; without it that test is skipped.

**Run the suite in both environments** before opening a pull request. The geometry code follows matplotlib's private `Text._get_layout`, which changed between 3.10 and 3.11. The parity tests in `tests/test_artist.py` (`test_extent_matches_plain_text`) catch any drift.

How the tests are organized:

| File | Covers |
|---|---|
| `test_style.py` | lengths, colors, CSS properties |
| `test_parse.py` | Markdown/HTML parsing through `ggtext.parse()` (ggIR) |
| `test_ir_adapter.py` | golden test: ggIR gives the tokens of the original parser |
| `test_spec.py` | `RichTextSpec` options and validation |
| `test_layout.py` | line layout with a fake measurer (no matplotlib rendering) |
| `test_artist.py` | `RichText`: parity with `Text`, drawing (pixel checks), backends, pickling, layout engines |
| `test_mpl_api.py` | the matplotlib helper functions |
| `test_plotnine.py` | elements, geoms, every themeable, layout space, compositions |
| `test_geom_richtext_images.py`, `test_geom_textbox_images.py` | geoms against ggtext's image tests (ported from plotnine-ggtext) |
| `test_theme_images.py` | theme text (titles, axes, strips, legends, tags) against baselines |
| `test_examples.py` | every `examples/NN_*.py` runs and writes its images |
| `test_notebook.py` | the tour notebook runs (needs the `notebook` extra) |

New features need tests. For anything visual, check geometry (`get_window_extent`) or pixel colors first (see the helpers in `tests/conftest.py`); they don't depend on fonts. Add an image comparison (`assert p == "name"` in a test marked `image`) when the overall look matters. Image baselines are made in one reference environment, Linux with matplotlib 3.11, and the comparisons are skipped elsewhere (see `tests/image_compare.py`). Generate a new baseline there with `pytest --update-baselines -m image` and look at it before committing.

## Continuous integration

`.github/workflows/tests.yml` runs on every push and pull request:

- Tests on Python 3.10 + matplotlib 3.10, and Python 3.11 / 3.12 / 3.13 + matplotlib 3.11, on Ubuntu, plus macOS and Windows (Python 3.13).
- The examples and the tour notebook (installed with the `notebook` extra).
- Image comparisons, in the Linux + matplotlib 3.11 jobs.
- Doctests (`pytest --doctest-modules src/ggtext`).
- Lint: `ruff check` and `ruff format --check`.

## Code style

```bash
make lint                     # ruff + pyrefly
uv run ruff check --fix .     # autofix
uv run ruff format .          # format
```

Ruff uses its default rules; don't add per-project rule selections.

- Code must run on Python 3.10, so don't use 3.11+ syntax or stdlib features.
- Public functions get NumPy-style docstrings with an example where it helps.
- Use Python names (`box_color`, `linestyle`) in the API. ggplot2 spellings belong only in the alias tables.

## Docs and gallery

The docs are Markdown files in `docs/`. The gallery images are generated by the scripts in `examples/`:

```bash
python examples/run_all.py        # runs every example, writes docs/images/*.png, rebuilds docs/gallery.md
python examples/make_gallery.py   # only rebuild docs/gallery.md
```

To add an example, create `examples/NN_short_name.py` following the existing ones: a docstring whose first line is the title, saving into `OUT` (which is `docs/images/` unless the tests set `GGTEXT_EXAMPLES_OUT`) under `if __name__ == "__main__":`. `tests/test_examples.py` picks it up automatically. Run `run_all.py` and **look at the image** before committing.

To re-execute the notebook tour:

```bash
jupyter nbconvert --to notebook --execute --inplace examples/ggtext_tour.ipynb
```

## Where things live

```
src/ggtext/
  _style.py      Style (ggir.Style + matplotlib FontProperties), color validation
  _parse.py      re-exports ggIR's token classes; parse() = ggir.parse + ggir.resolve
  _layout.py     line breaking, line heights, alignment (renderer independent)
  _spec.py       RichTextSpec (the rich text options)
  _artist.py     RichText, measuring/drawing, make_rich, the `richtext` Text property
  _images.py     <img> loading, register_image, options
  mpl.py         matplotlib helper functions
  plotnine/      element_*, geom_*, plot-composition support
docs/            user documentation (see docs/design.md for the internals)
examples/        runnable examples and the notebook tour
tests/           pytest suite
```

## Releasing (maintainers)

1. Update the version in `pyproject.toml` and `src/ggtext/__init__.py`.
2. Move the "unreleased" entries in `CHANGELOG.md` under the new version.
3. Tag the release and build with `uv build`.
