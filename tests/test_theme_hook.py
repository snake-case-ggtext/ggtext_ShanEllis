"""The plotnine theme hook that ggtext installs on import."""

from __future__ import annotations

import pytest
from matplotlib.text import Text
from plotnine.themes.theme import theme as plotnine_theme

from ggtext.plotnine._theme_hook import _apply_with_rich_text, install_theme_hook

pytestmark = pytest.mark.plotnine


def test_installed_on_import():
    assert plotnine_theme.apply is _apply_with_rich_text


def test_install_is_idempotent():
    install_theme_hook()
    install_theme_hook()
    assert plotnine_theme.apply is _apply_with_rich_text


def test_matplotlib_text_is_untouched():
    assert not hasattr(Text, "set_richtext")
    assert not hasattr(Text, "get_richtext")
