"""Tests for image loading and <img> sizing (ggtext._images)."""

import base64
import io

import matplotlib.pyplot as plt
import numpy as np
import pytest

import ggtext
from ggtext._images import load_image, options

from .conftest import rich_text


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------
def _png_bytes(color=(1.0, 0.0, 0.0)):
    buf = io.BytesIO()
    plt.imsave(buf, np.array([[color]] * 2, dtype=float), format="png")
    return buf.getvalue()


def test_load_local_file(tmp_path):
    path = tmp_path / "red.png"
    path.write_bytes(_png_bytes())
    for src in (str(path), f"file://{path}"):
        load_image.cache_clear()
        arr = load_image(src)
        assert arr.shape[-1] == 4 and arr.dtype == np.uint8
        assert arr[0, 0, 0] == 255


def test_load_data_uri():
    uri = "data:image/png;base64," + base64.b64encode(_png_bytes((0, 0, 1))).decode()
    arr = load_image(uri)
    assert arr[0, 0, 2] == 255


def test_load_percent_encoded_data_uri():
    from urllib.parse import quote_from_bytes

    uri = "data:image/png," + quote_from_bytes(_png_bytes())
    assert load_image(uri) is not None


def test_remote_images_can_be_disabled(monkeypatch):
    monkeypatch.setattr(options, "allow_remote_images", False)
    load_image.cache_clear()
    with pytest.warns(UserWarning, match="remote images are disabled"):
        assert load_image("https://example.org/x.png") is None


@pytest.mark.parametrize(
    "img",
    [
        np.zeros((3, 3)),
        np.zeros((3, 3, 3), dtype=np.uint8),
        np.zeros((3, 3, 4)),
        np.zeros((3, 3, 3), dtype=np.int64),
    ],
)
def test_register_image_formats(img):
    ggtext.register_image("fmt_test", img)
    arr = load_image("fmt_test")
    assert arr.shape == (3, 3, 4) and arr.dtype == np.uint8


def test_image_size_from_one_dimension(fig, renderer):
    ggtext.register_image("wide", np.zeros((10, 40, 3)))
    t = rich_text(fig, 0.1, 0.5, "<img src='wide' height='18pt'>")
    # 18pt tall, 4:1 aspect -> 72pt wide = 100px at 100 dpi
    assert t.get_window_extent(renderer).width == pytest.approx(100, abs=1)
    t2 = rich_text(fig, 0.1, 0.5, "<img src='wide' width='36pt'>")
    assert t2.get_window_extent(renderer).width == pytest.approx(50, abs=1)


def test_image_default_height_is_font_size(fig, renderer):
    ggtext.register_image("square", np.zeros((5, 5, 3)))
    t = rich_text(fig, 0.1, 0.5, "<img src='square'>", fontsize=36)
    assert t.get_window_extent(renderer).width == pytest.approx(50, abs=1)
