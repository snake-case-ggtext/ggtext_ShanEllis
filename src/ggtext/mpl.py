"""
Rich text helpers for plain matplotlib.

Every helper accepts the usual matplotlib text keyword arguments.
They set the default style of the text. You can also pass any
:class:`~ggtext.RichTextSpec` option (``width``, ``fill``,
``box_color``, ``padding``, ``r``, ``halign``, ...).

>>> import matplotlib.pyplot as plt
>>> import ggtext
>>> fig, ax = plt.subplots()
>>> _ = ggtext.set_title(ax, "**Penguins** of the <span style='color:#C06'>Palmer</span> archipelago")
>>> _ = ggtext.text(ax, 0.5, 0.5, "x<sup>2</sup> + y<sup>2</sup>", ha="center")
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal

from matplotlib.axes import Axes
from matplotlib.figure import Figure, SubFigure
from matplotlib.text import Annotation, Text

from ._artist import RichText, make_rich
from ._spec import _FIELD_NAMES, RichTextSpec, _normalize_kwargs

__all__ = [
    "annotate",
    "rich_ticklabels",
    "richify",
    "set_suptitle",
    "set_title",
    "set_xlabel",
    "set_ylabel",
    "split_kwargs",
    "text",
    "textbox",
]

# ggplot2-style aliases that are unambiguous for matplotlib text
_SPEC_ALIASES = {"box_colour", "linetype", "label_r", "radius"}


_ALIGN_KEYS = {"ha", "va", "horizontalalignment", "verticalalignment"}


def split_kwargs(kwargs: dict) -> tuple[dict, dict]:
    """
    Split keyword arguments into rich text options and Text properties.

    Returns
    -------
    spec_kwargs, text_kwargs
    """
    spec_kw = {}
    text_kw = {}
    for key, value in kwargs.items():
        if key in _FIELD_NAMES or key in _SPEC_ALIASES:
            spec_kw[key] = value
        else:
            text_kw[key] = value
    return _normalize_kwargs(spec_kw), text_kw


def _pop_fractional_alignment(text_kw: dict) -> dict:
    """
    Remove numeric ``ha``/``va`` values (ggplot2-style justification).

    matplotlib's ``Text`` only accepts names, so ggtext applies these after
    the artist becomes a :class:`RichText`.
    """
    late = {}
    for key in list(text_kw):
        if key in _ALIGN_KEYS and isinstance(text_kw[key], (int, float)):
            late[key] = text_kw.pop(key)
    return late


def _create(factory, args, text_kw: dict, spec: RichTextSpec):
    late = _pop_fractional_alignment(text_kw)
    t = make_rich(factory(*args, **text_kw), spec)
    if late:
        t.set(**late)
    return t


def _spec_from(richtext: Any, spec_kw: dict) -> RichTextSpec:
    spec = RichTextSpec.coerce(richtext) or RichTextSpec()
    return spec.replace(**spec_kw) if spec_kw else spec


def text(
    target: Axes | Figure | SubFigure,
    x: float,
    y: float,
    s: str,
    *,
    richtext: Any = True,
    **kwargs: Any,
) -> RichText:
    """
    Add rich text to an axes or a figure.

    This is :meth:`matplotlib.axes.Axes.text` (or
    :meth:`matplotlib.figure.Figure.text`) with Markdown/HTML support.

    Parameters
    ----------
    target :
        An Axes (coordinates are data coordinates by default) or a
        Figure/SubFigure (figure coordinates).
    x, y :
        Position of the text.
    s :
        The text, with Markdown and/or HTML markup.
    richtext :
        Base :class:`RichTextSpec` (or dict of options). You can also pass
        individual options as keyword arguments.
    **kwargs :
        :class:`RichTextSpec` options and
        :class:`matplotlib.text.Text` properties.

    Returns
    -------
    RichText

    Examples
    --------
    >>> import matplotlib.pyplot as plt
    >>> fig, ax = plt.subplots()
    >>> t = text(ax, 0.5, 0.5, "**Bold**, *italic* and `code`",
    ...          transform=ax.transAxes, ha="center", fontsize=14)
    """
    spec_kw, text_kw = split_kwargs(kwargs)
    spec = _spec_from(richtext, spec_kw)
    return _create(target.text, (x, y, s), text_kw, spec)  # type: ignore[return-value]


def textbox(
    target: Axes | Figure | SubFigure,
    x: float,
    y: float,
    s: str,
    *,
    width: float | str | None = "2in",
    fill: Any = "white",
    box_color: Any = "black",
    padding: Any = 5.5,
    r: float = 5.5,
    linewidth: float = 0.5,
    richtext: Any = True,
    **kwargs: Any,
) -> RichText:
    """
    Add a word-wrapped text box (like ggtext's ``geom_textbox``).

    Parameters
    ----------
    target :
        Axes or Figure.
    x, y :
        Position of the box. ``ha``/``va`` say which point of the box
        sits there (default: its center).
    s :
        The text.
    width :
        Width of the box. A string with units (``"2in"``, ``"150pt"``)
        or a fraction of the axes (or figure) width. ``None`` sizes the
        box to the text.
    fill, box_color, padding, r, linewidth :
        Box styling, see :class:`RichTextSpec`.
    **kwargs :
        More :class:`RichTextSpec` options and
        :class:`matplotlib.text.Text` properties.

    Returns
    -------
    RichText
    """
    kwargs.setdefault("ha", "center")
    kwargs.setdefault("va", "center")
    return text(
        target,
        x,
        y,
        s,
        richtext=richtext,
        width=width,
        fill=fill,
        box_color=box_color,
        padding=padding,
        r=r,
        linewidth=linewidth,
        **kwargs,
    )


def annotate(
    ax: Axes,
    s: str,
    xy: tuple[float, float],
    xytext: tuple[float, float] | None = None,
    *,
    richtext: Any = True,
    **kwargs: Any,
) -> Annotation:
    """
    :meth:`matplotlib.axes.Axes.annotate` with rich text.

    Arrows (``arrowprops``) attach to the edge of the rich text box.

    Returns
    -------
    matplotlib.text.Annotation
        The annotation, which is also a :class:`RichText`.
    """
    spec_kw, text_kw = split_kwargs(kwargs)
    spec = _spec_from(richtext, spec_kw)
    return _create(ax.annotate, (s, xy, xytext), text_kw, spec)  # type: ignore[return-value]


def richify(
    texts: Text | Iterable[Text],
    richtext: Any = True,
    **kwargs: Any,
) -> Text | list:
    """
    Turn existing matplotlib text artists into rich text, in place.

    Parameters
    ----------
    texts :
        A Text artist (e.g. ``ax.title``, ``ax.xaxis.label``,
        ``fig.legends[0].get_texts()[0]``) or an iterable of them.
    richtext, **kwargs :
        Rich text options.

    Returns
    -------
    The same artist(s).

    Examples
    --------
    >>> import matplotlib.pyplot as plt
    >>> fig, ax = plt.subplots()
    >>> _ = ax.set_xlabel("Bill length (mm) <span style='color:gray'>*n = 344*</span>")
    >>> _ = richify(ax.xaxis.label)
    """
    spec = _spec_from(richtext, _normalize_kwargs(kwargs))
    if isinstance(texts, Text):
        return make_rich(texts, spec)
    return [make_rich(t, spec) for t in texts]


def rich_ticklabels(
    ax: Axes,
    axis: Literal["x", "y", "both"] = "x",
    which: Literal["major", "minor", "both"] = "major",
    richtext: Any = True,
    **kwargs: Any,
) -> None:
    """
    Render tick labels of *ax* as rich text.

    matplotlib creates tick objects lazily (e.g. when the view changes),
    so this also makes sure that ticks created later are rich.

    Parameters
    ----------
    ax :
        The axes.
    axis :
        Which axis: ``"x"``, ``"y"`` or ``"both"``.
    which :
        ``"major"``, ``"minor"`` or ``"both"`` ticks.
    richtext, **kwargs :
        Rich text options.

    Examples
    --------
    >>> import matplotlib.pyplot as plt
    >>> fig, ax = plt.subplots()
    >>> ax.set_xticks([0, 1], ["**Control**", "*Treatment*"])  # doctest: +ELLIPSIS
    [...]
    >>> rich_ticklabels(ax, "x")
    """
    spec = _spec_from(richtext, _normalize_kwargs(kwargs))
    axes = {"x": [ax.xaxis], "y": [ax.yaxis], "both": [ax.xaxis, ax.yaxis]}[axis]
    for a in axes:
        ticks = []
        if which in ("major", "both"):
            ticks += a.get_major_ticks()
        if which in ("minor", "both"):
            ticks += a.get_minor_ticks()
        for t in ticks:
            make_rich(t.label1, spec)
            make_rich(t.label2, spec)
        _keep_new_ticks_rich(a)


def _keep_new_ticks_rich(axis_obj) -> None:
    """
    Make ticks that matplotlib creates later inherit rich text.

    Later ticks copy their properties from the first tick through
    ``Axis._copy_tick_props``; we wrap it on this axis instance only.
    """
    if getattr(axis_obj, "_ggtext_copy_wrapped", False):
        return
    original = axis_obj._copy_tick_props

    def _copy_tick_props(src, dest):
        original(src, dest)
        if src is None or dest is None:
            return
        for name in ("label1", "label2"):
            s, d = getattr(src, name), getattr(dest, name)
            if isinstance(s, RichText):
                make_rich(d, s.get_richtext())

    axis_obj._copy_tick_props = _copy_tick_props
    axis_obj._ggtext_copy_wrapped = True


def _set_label(setter, s: str, richtext: Any, kwargs: dict) -> Text:
    spec_kw, text_kw = split_kwargs(kwargs)
    spec = _spec_from(richtext, spec_kw)
    return _create(setter, (s,), text_kw, spec)


def set_title(ax: Axes, label: str, *, richtext: Any = True, **kwargs: Any) -> Text:
    """:meth:`matplotlib.axes.Axes.set_title` with rich text."""
    return _set_label(ax.set_title, label, richtext, kwargs)


def set_xlabel(ax: Axes, label: str, *, richtext: Any = True, **kwargs: Any) -> Text:
    """:meth:`matplotlib.axes.Axes.set_xlabel` with rich text."""
    _set_label(ax.set_xlabel, label, richtext, kwargs)
    return ax.xaxis.label


def set_ylabel(ax: Axes, label: str, *, richtext: Any = True, **kwargs: Any) -> Text:
    """:meth:`matplotlib.axes.Axes.set_ylabel` with rich text."""
    _set_label(ax.set_ylabel, label, richtext, kwargs)
    return ax.yaxis.label


def set_suptitle(
    fig: Figure | SubFigure, t: str, *, richtext: Any = True, **kwargs: Any
) -> Text:
    """:meth:`matplotlib.figure.Figure.suptitle` with rich text."""
    return _set_label(fig.suptitle, t, richtext, kwargs)
