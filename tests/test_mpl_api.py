"""Tests for the public matplotlib helpers (ggtext.mpl)."""

import pytest
from matplotlib.text import Annotation

import ggtext
from ggtext import RichText, RichTextSpec
from ggtext.mpl import rich_ticklabels, split_kwargs

from .conftest import has_color, pixels_in_bbox, render_rgba


def test_split_kwargs():
    spec, text = split_kwargs(
        {"fill": "red", "color": "blue", "box_colour": "k", "size": 3}
    )
    assert spec == {"fill": "red", "box_color": "k"}
    assert text == {"color": "blue", "size": 3}  # size stays a font size


def test_text_on_axes_uses_data_coords(fig_ax):
    _f, ax = fig_ax
    ax.set_xlim(0, 10)
    t = ggtext.text(ax, 5, 0.5, "**x**", fill="red", color="blue")
    assert isinstance(t, RichText) and t in ax.texts
    assert t.get_transform() == ax.transData
    assert t.get_richtext().fill == "red" and t.get_color() == "blue"


def test_text_on_figure(fig):
    t = ggtext.text(fig, 0.5, 0.5, "*x*")
    assert t in fig.texts


def test_text_with_base_spec(fig):
    base = RichTextSpec(fill="yellow", padding=2)
    t = ggtext.text(fig, 0.5, 0.5, "x", richtext=base, r=3)
    assert t.get_richtext() == base.replace(r=3)


def test_textbox_defaults(fig):
    t = ggtext.textbox(fig, 0.5, 0.5, "word " * 30)
    spec = t.get_richtext()
    assert spec.width == "2in" and spec.fill == "white" and spec.box_color == "black"
    assert t.get_ha() == "center" and t.get_va() == "center"
    assert t.get_window_extent(fig.canvas.get_renderer()).width == pytest.approx(
        200, abs=0.5
    )


def test_annotate(fig_ax):
    f, ax = fig_ax
    ann = ggtext.annotate(ax, "**hi** there", xy=(0.5, 0.5), xytext=(0.1, 0.1),
                          arrowprops={"arrowstyle": "->"}, fill="lightyellow")  # fmt: skip
    assert isinstance(ann, Annotation) and isinstance(ann, RichText)
    f.canvas.draw()
    assert ann.arrow_patch is not None
    assert ann.get_window_extent().width > 0


def test_annotate_text_is_drawn(fig_ax):
    f, ax = fig_ax
    ann = ggtext.annotate(ax, "<span style='color:#ff0000'>REDRED</span>", xy=(0.5, 0.5),
                          xytext=(0.2, 0.2), fontsize=24)  # fmt: skip
    img = render_rgba(f)
    assert has_color(pixels_in_bbox(img, ann.get_window_extent()), (255, 0, 0))


def test_richify_single_and_many(fig_ax):
    _f, ax = fig_ax
    ax.set_xlabel("**x**")
    assert ggtext.richify(ax.xaxis.label) is ax.xaxis.label
    assert isinstance(ax.xaxis.label, RichText)
    texts = [ax.text(0, 0, "a"), ax.text(0, 0, "b")]
    out = ggtext.richify(texts, fill="red")
    assert all(isinstance(t, RichText) and t.get_richtext().fill == "red" for t in out)


@pytest.mark.parametrize("func, getter", [
    (ggtext.set_title, lambda f, ax: ax.title),
    (ggtext.set_xlabel, lambda f, ax: ax.xaxis.label),
    (ggtext.set_ylabel, lambda f, ax: ax.yaxis.label),
])  # fmt: skip
def test_label_setters(fig_ax, func, getter):
    f, ax = fig_ax
    out = func(ax, "**label**", fontsize=15, fill="#eee")
    target = getter(f, ax)
    assert out is target and isinstance(target, RichText)
    assert target.get_fontsize() == 15 and target.get_richtext().fill == "#eee"
    f.canvas.draw()


def test_suptitle(fig_ax):
    f, _ax = fig_ax
    t = ggtext.set_suptitle(f, "**Super**")
    assert t is f._suptitle and isinstance(t, RichText)


def test_rich_ticklabels_survive_new_ticks(fig_ax):
    f, ax = fig_ax
    ax.set_xticks([0, 1], ["**a**", "*b*"])
    rich_ticklabels(ax, "x")
    assert all(isinstance(t.label1, RichText) for t in ax.xaxis.get_major_ticks())
    # ticks created later must be rich too
    ax.set_xticks([0, 1, 2, 3], ["**a**", "*b*", "c", "d"])
    f.canvas.draw()
    ticks = ax.xaxis.get_major_ticks()
    assert len(ticks) == 4 and all(isinstance(t.label1, RichText) for t in ticks)
    # calling twice is harmless
    rich_ticklabels(ax, "x")


@pytest.mark.parametrize(
    "axis, which", [("y", "major"), ("both", "both"), ("x", "minor")]
)
def test_rich_ticklabels_axes(fig_ax, axis, which):
    f, ax = fig_ax
    ax.minorticks_on()
    rich_ticklabels(ax, axis, which, fill="yellow")
    f.canvas.draw()
