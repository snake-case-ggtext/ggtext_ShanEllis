"""
The plotnine theme hook that turns themed text into rich text.

plotnine styles its text with ``text.set(**element.properties)``. The
ggtext theme elements add a ``richtext`` property, which only
:class:`~ggtext._artist.RichText` understands. The hook wraps
``plotnine.themes.theme.theme.apply``: before plotnine styles anything,
it turns every text that a themeable with ``richtext`` targets into rich
text. plotnine's ``text.set(richtext=spec)`` then reaches
:meth:`~ggtext._artist.RichText.set_richtext`.

``import ggtext`` installs the hook. It cannot be switched off: without
it, every theme that uses a ggtext element fails to draw.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

from plotnine.themes import themeable as th
from plotnine.themes.theme import theme as _theme

from .._artist import RichText, make_rich

if TYPE_CHECKING:
    from matplotlib.text import Text
    from plotnine.themes.theme import theme

__all__ = ["install_theme_hook"]


def _one(text: Text | None) -> list[Text]:
    return [] if text is None else [text]


def _tick_labels(theme: theme, axis: str) -> list[Text]:
    return [t.label1 for ax in theme.axs for t in getattr(ax, axis).get_major_ticks()]


# The texts that each (leaf) text themeable styles, as plotnine finds
# them in its apply_figure/apply_ax methods. A themeable such as
# ``title`` or ``text`` inherits from the leaves it covers.
_THEMED_TEXTS: tuple[tuple[type, Callable[[theme], Iterable[Text]]], ...] = (
    (th.axis_title_x, lambda t: _one(t.targets.axis_title_x)),
    (th.axis_title_y, lambda t: _one(t.targets.axis_title_y)),
    (th.legend_title, lambda t: _one(t.targets.legend_title)),
    (th.legend_text_legend, lambda t: t.targets.legend_text_legend),
    (th.legend_text_colorbar, lambda t: t.targets.legend_text_colorbar),
    (th.plot_title, lambda t: _one(t.targets.plot_title)),
    (th.plot_subtitle, lambda t: _one(t.targets.plot_subtitle)),
    (th.plot_caption, lambda t: _one(t.targets.plot_caption)),
    (th.plot_tag, lambda t: _one(t.targets.plot_tag)),
    (th.strip_text_x, lambda t: t.targets.strip_text_x),
    (th.strip_text_y, lambda t: t.targets.strip_text_y),
    (th.axis_text_x, lambda t: _tick_labels(t, "xaxis")),
    (th.axis_text_y, lambda t: _tick_labels(t, "yaxis")),
)


def _make_themed_texts_rich(theme: theme) -> None:
    """
    Turn every text that a themeable with ``richtext`` styles into rich text.

    plotnine then applies the theme as usual. Its
    ``text.set(richtext=spec)`` calls land on
    :meth:`~ggtext._artist.RichText.set_richtext`, in plotnine's own order (general
    themeables first), so the most specific spec wins.
    """
    for themeable in theme.T.values():
        if themeable.is_blank() or "richtext" not in themeable.properties:
            continue
        spec = themeable.properties["richtext"]
        for kind, find in _THEMED_TEXTS:
            if not isinstance(themeable, kind):
                continue
            for text in find(theme):
                if not isinstance(text, RichText):
                    make_rich(text, spec)


def _apply_with_rich_text(self: theme) -> None:
    """``theme.apply`` that first turns the themed texts into rich text."""
    _make_themed_texts_rich(self)
    _original_theme_apply(self)


_original_theme_apply = _theme.apply


def install_theme_hook() -> None:
    """
    Wrap plotnine's ``theme.apply`` so ggtext's theme elements work.

    ``import ggtext`` runs this. Repeated calls do nothing.
    """
    if _theme.__dict__.get("apply") is not _apply_with_rich_text:
        _theme.apply = _apply_with_rich_text  # type: ignore[method-assign]
