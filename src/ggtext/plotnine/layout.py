"""
Helpers that connect rich text to plotnine's layout.

Fractional widths (``element_textbox_simple(width=1)``) are relative to
the *panel area* of the plot that a title belongs to. A figure can hold
several plots (``p1 | p2``), so we ask plotnine's layout engine which
plot owns the text.
"""

from __future__ import annotations

from typing import Any, Iterable, List

__all__ = ["plot_panels"]

# ThemeTargets fields that hold figure-level texts
_FIGURE_TEXTS = (
    "plot_title",
    "plot_subtitle",
    "plot_caption",
    "plot_tag",
    "axis_title_x",
    "axis_title_y",
)


def _plots_of(engine: Any) -> Iterable[Any]:
    """The ggplot objects laid out by a plotnine layout engine."""
    plot = getattr(engine, "plot", None)
    if plot is not None:
        yield plot
    composition = getattr(engine, "composition", None)
    if composition is not None:
        for spec in getattr(composition, "plotspecs", []):
            if getattr(spec, "plot", None) is not None:
                yield spec.plot


def plot_panels(text: Any, figure: Any) -> List[Any] | None:
    """
    The panels (axes) of the plotnine plot that owns *text*.

    Returns None when the figure is not laid out by plotnine or the text
    is not one of a plot's figure-level texts.
    """
    if figure is None:
        return None
    engine = figure.get_layout_engine()
    for plot in _plots_of(engine):
        targets = getattr(getattr(plot, "theme", None), "targets", None)
        if targets is None:
            continue
        if any(getattr(targets, name, None) is text for name in _FIGURE_TEXTS):
            axs = [ax for ax in getattr(plot, "axs", []) if ax.get_visible()]
            return axs or None
    return None
