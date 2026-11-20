# Contributing to ggtext

Thanks for helping! Bug reports, docs fixes, examples, and features are all welcome. If you're planning something big, please open an issue first so we can talk it through.

## Development setup

Development dependencies live in [dependency groups](https://packaging.python.org/en/latest/specifications/dependency-groups/) in `pyproject.toml`:

| Group | Contents |
|---|---|
| `test` | pytest, pytest-cov, pytest-randomly |
| `docs` | jupyter, nbconvert |
| `dev` | `test` + `docs` + ruff, prek, pyrefly |

We use [uv](https://docs.astral.sh/uv/), but plain `pip` + `venv` works too (pip ≥ 25.1 is needed for `--group`).

### With uv

uv creates the environment, installs ggtext (editable) and the group from `uv.lock`, and runs the command:

```bash
uv run --group dev pytest tests
```

### With pip

`--group` installs only the group, so also install ggtext itself with `-e .`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade "pip>=25.1"
pip install -e . --group dev
```

pip ignores `uv.lock`, so it installs the newest versions `pyproject.toml` allows.

## Make targets

```bash
make install      # uv sync (package + dev tools) and install the prek git hooks
make test         # pytest in random order (pytest-randomly) with coverage
make tox          # the tests on matplotlib 3.10, 3.11 and the newest pre-release (tox-uv)
make lint         # ruff check + ruff format --check + pyrefly (strict)
make pre-commit   # install the prek git hooks and run them on every file
```

Run `make install` once after cloning: the hooks then run ruff and pyrefly on every commit. There is no CI, so run `make test` and `make lint` before pushing, and `make tox` when a change touches text layout or drawing: ggtext overrides private matplotlib internals that changed in 3.11, so each version has its own code path.

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

With uv, prefix any of these with `uv run --group dev`, e.g. `uv run --group dev pytest -k tick`.

**Run the suite** before opening a pull request. The geometry code follows matplotlib's private `Text._get_layout`, which can change between matplotlib releases. The parity tests in `tests/test_artist.py` (`test_extent_matches_plain_text`) catch any drift.

The test files and what they cover:

| File | Covers |
|---|---|
| `test_style.py` | lengths, colors, CSS properties |
| `test_parse.py` | Markdown/HTML parsing through `ggtext.parse()` (ggIR) |
| `test_spec.py` | `RichTextSpec` options and validation |
| `test_layout.py` | line layout with a fake measurer (no matplotlib rendering) |
| `test_artist.py` | `RichText`: parity with `Text`, drawing (pixel checks), backends, pickling, layout engines |
| `test_images.py` | image loading and `<img>` sizing |
| `test_plotnine.py` | elements, geoms, every themeable, layout space, compositions |
| `test_geom_richtext_images.py`, `test_geom_textbox_images.py` | geoms against ggtext's image tests (ported from plotnine-ggtext) |
| `test_theme_images.py` | theme text (titles, axes, strips, legends, tags) against baselines |
| `test_examples.py` | every `examples/NN_*.py` runs and writes its images |
| `test_notebook.py` | the tour notebook runs (needs the `notebook` extra) |

New features need tests. For anything visual, check geometry (`get_window_extent`) or pixel colors first (see the helpers in `tests/conftest.py`); they don't depend on fonts. Add an image comparison (`assert p == "name"` in a test marked `image`) when the overall look matters. Image baselines are made in one reference environment, Linux with matplotlib 3.11, and the comparisons are skipped elsewhere (see `tests/image_compare.py`). Generate a new baseline there with `pytest --update-baselines -m image` and look at it before committing.

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

The docs are Markdown files in `docs/`. The scripts in `examples/` generate the gallery images:

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
  _artist.py     RichText, measuring/drawing, make_rich/make_plain
  _images.py     <img> loading, register_image, options
  plotnine/      element_*, geom_*, plot-composition support
docs/            user documentation (see docs/design.md for the internals)
examples/        runnable examples and the notebook tour
tests/           pytest suite
```

## Releasing (maintainers)

1. Update the version in `pyproject.toml` and `src/ggtext/__init__.py`.
2. Move the "unreleased" entries in `CHANGELOG.md` under the release version.
3. Tag the release and build with `uv build`.
