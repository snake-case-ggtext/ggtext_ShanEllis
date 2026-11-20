"""Shared fixtures for the ggtext test suite."""

from __future__ import annotations

from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.axes import Axes
from matplotlib.figure import Figure, SubFigure

import ggtext  # noqa: F401  (installs the plotnine theme hook)
from ggtext._artist import RichText, make_rich
from ggtext._spec import _FIELD_NAMES, RichTextSpec, _normalize_kwargs


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


@pytest.fixture
def fig():
    return plt.figure(figsize=(6, 4), dpi=100)


@pytest.fixture
def fig_ax():
    f, ax = plt.subplots(figsize=(6, 4), dpi=100)
    return f, ax


@pytest.fixture
def renderer(fig):
    return fig.canvas.get_renderer()


def rich_text(
    target: Axes | Figure | SubFigure,
    x: float,
    y: float,
    s: str,
    *,
    richtext: Any = True,
    **kwargs: Any,
) -> RichText:
    """
    Add a :class:`RichText` to an axes or figure (test helper).

    Keyword arguments that are :class:`RichTextSpec` options go into the
    spec; the rest are ``Text`` properties. Numeric ``ha``/``va`` are set
    after the artist is rich, since plain ``Text`` only accepts names.
    """
    spec_kw = {k: kwargs.pop(k) for k in list(kwargs) if k in _FIELD_NAMES}
    late = {
        k: kwargs.pop(k)
        for k in list(kwargs)
        if k in ("ha", "va") and isinstance(kwargs[k], (int, float))
    }
    spec = RichTextSpec.coerce(richtext) or RichTextSpec()
    if spec_kw:
        spec = spec.replace(**_normalize_kwargs(spec_kw))
    t = make_rich(target.text(x, y, s, **kwargs), spec)
    if late:
        t.set(**late)
    return t  # type: ignore[return-value]


def render_rgba(fig) -> np.ndarray:
    """Draw *fig* with Agg and return the RGBA pixels."""
    fig.canvas.draw()
    return np.asarray(fig.canvas.buffer_rgba()).copy()


def pixels_in_bbox(img: np.ndarray, bbox, pad: int = 2) -> np.ndarray:
    """The pixels of *img* inside a display-space *bbox* (y up)."""
    h = img.shape[0]
    x0 = max(int(bbox.x0) - pad, 0)
    x1 = min(int(np.ceil(bbox.x1)) + pad, img.shape[1])
    y0 = max(int(h - np.ceil(bbox.y1)) - pad, 0)
    y1 = min(int(h - bbox.y0) + pad, h)
    return img[y0:y1, x0:x1]


def has_color(region: np.ndarray, rgb, tol: int = 60) -> bool:
    """Whether any pixel in *region* is close to *rgb* (0-255 ints)."""
    diff = np.abs(region[..., :3].astype(int) - np.asarray(rgb)[None, None, :])
    return bool((diff.max(axis=-1) < tol).any())


# --- image comparison hooks (see tests/image_compare.py) ---------------------


def pytest_addoption(parser):
    parser.addoption(
        "--update-baselines",
        action="store_true",
        default=False,
        help="Write result images as the new baselines (image tests)",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "image: image-comparison tests (assert plot == 'name')"
    )
    from . import image_compare

    image_compare.set_update(config.getoption("--update-baselines"))


def pytest_assertrepr_compare(op, left, right):
    from .image_compare import assertrepr_compare

    return assertrepr_compare(op, left, right)


@pytest.fixture(autouse=True)
def _image_env(request):
    """For ``image`` tests only: enable ``assert plot == "name"``."""
    if request.node.get_closest_marker("image") is None:
        yield
        return
    from plotnine import ggplot

    from . import image_compare

    mp = pytest.MonkeyPatch()
    mp.setattr(ggplot, "__eq__", image_compare.ggplot_equals, raising=False)
    mp.setattr(ggplot, "draw_test", image_compare.draw_test, raising=False)
    try:
        yield
    finally:
        mp.undo()
