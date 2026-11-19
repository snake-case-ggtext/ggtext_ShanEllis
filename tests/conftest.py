"""Shared fixtures for the ggtext test suite."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402

import ggtext  # noqa: E402,F401  (registers the richtext property)


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
