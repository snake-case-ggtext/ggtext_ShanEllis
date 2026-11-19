"""
Loading images for ``<img>`` tags.

Sources can be

- a path to a local file (``"logo.png"``, ``"~/img/flag.jpg"``,
  ``"file:///tmp/x.png"``),
- a ``data:`` URI (``"data:image/png;base64,..."``),
- an ``http(s)://`` URL (downloaded once and cached; can be disabled
  with ``ggtext.options.allow_remote_images = False``),
- the name of an image registered with :func:`register_image`, which
  lets you use numpy arrays or PIL images directly.
"""

from __future__ import annotations

import base64
import io
import os
import warnings
from functools import lru_cache
from typing import Any, Dict

import numpy as np

__all__ = ["register_image", "load_image", "options"]


class _Options:
    """Package-wide options."""

    #: Whether ``<img src="https://...">`` may download images.
    allow_remote_images: bool = True
    #: Seconds to wait for a remote image.
    remote_timeout: float = 10.0


options = _Options()

_REGISTRY: Dict[str, np.ndarray] = {}


def _to_rgba_array(img: Any) -> np.ndarray:
    arr = np.asarray(img)
    if arr.ndim == 2:  # grayscale
        arr = np.stack([arr] * 3, axis=-1)
    if arr.dtype.kind == "f":
        arr = (np.clip(arr, 0, 1) * 255).astype(np.uint8)
    elif arr.dtype != np.uint8:
        arr = arr.astype(np.uint8)
    if arr.shape[-1] == 3:
        alpha = np.full(arr.shape[:2] + (1,), 255, dtype=np.uint8)
        arr = np.concatenate([arr, alpha], axis=-1)
    return arr


def register_image(name: str, image: Any) -> None:
    """
    Make an in-memory image available to ``<img src="name">``.

    Parameters
    ----------
    name :
        The name used in the ``src`` attribute.
    image :
        A numpy array (``(H, W)``, ``(H, W, 3)`` or ``(H, W, 4)``,
        floats in [0, 1] or uint8) or a PIL image.

    Examples
    --------
    >>> import numpy as np
    >>> register_image("red_square", np.array([[[1.0, 0, 0]]]))
    >>> # then use: "<img src='red_square' width='12'> is red"
    """
    _REGISTRY[name] = _to_rgba_array(image)
    load_image.cache_clear()


def _read_bytes(data: bytes) -> np.ndarray:
    import matplotlib.image as mimage

    return _to_rgba_array(mimage.imread(io.BytesIO(data)))


@lru_cache(maxsize=128)
def load_image(src: str) -> np.ndarray | None:
    """
    Load the image *src* as an ``(H, W, 4)`` uint8 array.

    Returns None (with a warning) if the image cannot be loaded.
    """
    if src in _REGISTRY:
        return _REGISTRY[src]
    try:
        if src.startswith("data:"):
            header, _, payload = src.partition(",")
            if ";base64" in header:
                return _read_bytes(base64.b64decode(payload))
            from urllib.parse import unquote_to_bytes

            return _read_bytes(unquote_to_bytes(payload))

        if src.startswith(("http://", "https://")):
            if not options.allow_remote_images:
                raise RuntimeError(
                    "remote images are disabled "
                    "(ggtext.options.allow_remote_images = False)"
                )
            from urllib.request import urlopen

            with urlopen(src, timeout=options.remote_timeout) as resp:  # noqa: S310
                return _read_bytes(resp.read())

        path = src[len("file://") :] if src.startswith("file://") else src
        path = os.path.expanduser(path)
        with open(path, "rb") as f:
            return _read_bytes(f.read())
    except Exception as err:  # noqa: BLE001 - any failure means "no image"
        warnings.warn(
            f"ggtext: could not load image {src[:80]!r}: {err}",
            UserWarning,
            stacklevel=2,
        )
        return None
