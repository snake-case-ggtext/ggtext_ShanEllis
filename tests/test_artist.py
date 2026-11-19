"""Tests for the RichText artist (ggtext._artist)."""

import io
import pickle
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.text import Annotation, Text

import ggtext
from ggtext import RichText, RichTextSpec, is_rich, make_plain, make_rich
from ggtext._artist import MPL_311, _rich_class_for

from .conftest import has_color, pixels_in_bbox, render_rgba

PLAIN = {"markdown": False, "html": False}


# ---------------------------------------------------------------------------
# Geometry: measure rich text exactly like plain text
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("s", ["Hello world", "gyp", "two\nlines", "a\nb\nc"])
@pytest.mark.parametrize("rotation", [0, 33, 90, 180, 270])
@pytest.mark.parametrize("ha", ["left", "center", "right"])
@pytest.mark.parametrize(
    "va", ["top", "center", "bottom", "baseline", "center_baseline"]
)
@pytest.mark.parametrize("rotation_mode", ["default", "anchor"])
def test_extent_matches_plain_text(fig, renderer, s, rotation, ha, va, rotation_mode):
    kw = {"rotation": rotation, "ha": ha, "va": va, "rotation_mode": rotation_mode,
              "fontsize": 12, "ma": "center"}  # fmt: skip
    plain = fig.text(0.4, 0.5, s, **kw)
    rich = fig.add_artist(RichText(0.4, 0.5, s, richtext=PLAIN, **kw))
    a = plain.get_window_extent(renderer).extents
    b = rich.get_window_extent(renderer).extents
    np.testing.assert_allclose(a, b, atol=0.6)


def test_markdown_does_not_change_plain_extent(fig, renderer):
    plain = fig.text(0.1, 0.5, "Hello world", fontsize=14)
    rich = ggtext.text(fig, 0.1, 0.5, "Hello world", fontsize=14)
    np.testing.assert_allclose(
        plain.get_window_extent(renderer).extents,
        rich.get_window_extent(renderer).extents,
        atol=0.6,
    )


def test_metric_caches_follow_font_rcparams():
    # The same FontProperties ("sans-serif", 12pt) resolves to different
    # fonts under different rcParams. Measuring under one font must not leak
    # cached metrics into figures that use another.
    s = "two\nlines"
    extents = {}
    for family in (["DejaVu Sans"], ["DejaVu Sans Mono"]):
        with plt.rc_context({"font.family": "sans-serif", "font.sans-serif": family}):
            f = plt.figure(figsize=(6, 4), dpi=100)
            r = f.canvas.get_renderer()
            plain = f.text(0.4, 0.5, s, fontsize=12)
            rich = f.add_artist(RichText(0.4, 0.5, s, fontsize=12, richtext=PLAIN))
            a = plain.get_window_extent(r).extents
            b = rich.get_window_extent(r).extents
            np.testing.assert_allclose(a, b, atol=0.6)
            extents[family[0]] = b
    # Sanity check: the two fonts really do measure differently
    assert not np.allclose(extents["DejaVu Sans"], extents["DejaVu Sans Mono"])


def test_bold_is_wider_than_plain(fig, renderer):
    plain = ggtext.text(fig, 0.1, 0.5, "Hello world")
    bold = ggtext.text(fig, 0.1, 0.3, "**Hello world**")
    assert (
        bold.get_window_extent(renderer).width > plain.get_window_extent(renderer).width
    )


def test_bigger_span_increases_height(fig, renderer):
    a = ggtext.text(fig, 0.1, 0.5, "abc")
    b = ggtext.text(fig, 0.1, 0.5, "abc <span style='font-size:30pt'>X</span>")
    assert (
        b.get_window_extent(renderer).height
        > 1.8 * a.get_window_extent(renderer).height
    )


def test_rotation_90_swaps_extent(fig, renderer):
    h = ggtext.text(fig, 0.5, 0.5, "**some text**")
    v = ggtext.text(fig, 0.5, 0.5, "**some text**", rotation=90)
    eh, ev = h.get_window_extent(renderer), v.get_window_extent(renderer)
    assert ev.width == pytest.approx(eh.height, abs=0.5)
    assert ev.height == pytest.approx(eh.width, abs=0.5)


def test_padding_grows_extent(fig, renderer):
    a = ggtext.text(fig, 0.5, 0.5, "abc")
    b = ggtext.text(fig, 0.5, 0.5, "abc", padding=10)  # 10pt = ~13.9px at 100dpi
    ea, eb = a.get_window_extent(renderer), b.get_window_extent(renderer)
    assert eb.width == pytest.approx(ea.width + 2 * 10 * 100 / 72, abs=0.5)
    assert eb.height == pytest.approx(ea.height + 2 * 10 * 100 / 72, abs=0.5)


def test_fixed_width_box(fig, renderer):
    t = ggtext.text(fig, 0.1, 0.5, "word " * 40, width="2in")
    e = t.get_window_extent(renderer)
    assert e.width == pytest.approx(200, abs=0.5)  # 2in at 100 dpi
    assert len(t._rich_layout(renderer).lines) > 3


def test_maxwidth_shrinks_to_fit(fig, renderer):
    short = ggtext.text(fig, 0.1, 0.5, "short", maxwidth="3in")
    long = ggtext.text(fig, 0.1, 0.5, "word " * 50, maxwidth="3in")
    assert short.get_window_extent(renderer).width < 100
    assert long.get_window_extent(renderer).width <= 300 + 0.5


def test_relative_width_uses_axes(fig_ax):
    f, ax = fig_ax
    r = f.canvas.get_renderer()
    t = ggtext.text(ax, 0.5, 0.5, "word " * 50, width=0.5, transform=ax.transAxes)
    assert t.get_window_extent(r).width == pytest.approx(ax.bbox.width / 2, abs=0.5)


def test_relative_width_figure_text_uses_panel_area(fig_ax):
    f, ax = fig_ax
    r = f.canvas.get_renderer()
    t = ggtext.text(f, 0.5, 0.95, "word " * 50, width=1.0, ha="center")
    assert t.get_window_extent(r).width == pytest.approx(ax.bbox.width, abs=0.5)


def test_relative_width_figure_without_axes(fig, renderer):
    t = ggtext.text(fig, 0.5, 0.5, "word " * 50, width=0.5)
    assert t.get_window_extent(renderer).width == pytest.approx(
        fig.bbox.width / 2, abs=0.5
    )


def test_relative_width_along_rotated_text(fig_ax):
    f, ax = fig_ax
    r = f.canvas.get_renderer()
    t = ggtext.text(ax, 0.1, 0.5, "word " * 50, width=1.0, rotation=90,
                    transform=ax.transAxes)  # fmt: skip
    assert t.get_window_extent(r).height == pytest.approx(ax.bbox.height, abs=0.5)


def test_custom_reference(fig, renderer):
    t = ggtext.text(fig, 0.1, 0.5, "word " * 50, width=1.0)
    t._ggtext_reference = lambda renderer: (123.0, 50.0)
    t._rich_cache = None
    assert t.get_window_extent(renderer).width == pytest.approx(123.0, abs=0.5)


def test_matplotlib_wrap_is_honored(fig, renderer):
    t = ggtext.text(fig, 0.5, 0.5, "**word** " * 60, wrap=True, ha="center")
    fig.canvas.draw()
    assert len(t._rich_layout(renderer).lines) > 1
    assert t.get_window_extent(renderer).width <= fig.bbox.width


def test_empty_text(fig, renderer):
    t = ggtext.text(fig, 0.5, 0.5, "")
    e = t.get_window_extent(renderer)
    assert e.width == 0 and e.height == 0
    fig.canvas.draw()  # does not fail


def test_invisible_text(fig, renderer):
    t = ggtext.text(fig, 0.5, 0.5, "**x**")
    t.set_visible(False)
    fig.canvas.draw()


def test_nan_position_is_skipped(fig_ax):
    f, ax = fig_ax
    ggtext.text(ax, np.nan, 0.5, "**x**")
    f.canvas.draw()


def test_layout_cache_invalidates_on_property_change(fig, renderer):
    t = ggtext.text(fig, 0.1, 0.5, "**abc**")
    w1 = t.get_window_extent(renderer).width
    t.set_fontsize(30)
    w2 = t.get_window_extent(renderer).width
    t.set_text("**abcdef**")
    w3 = t.get_window_extent(renderer).width
    assert w1 < w2 < w3


@pytest.mark.skipif(not MPL_311, reason="format of matplotlib >= 3.11")
def test_get_layout_format_311(fig, renderer):
    t = ggtext.text(fig, 0.5, 0.5, "a\n**b**")
    _bbox, info, (_corner, _size) = t._get_layout(renderer)
    assert len(info) == 2
    line, (_w, _a, _d), xy = info[0]
    assert line == "a" and len(xy) == 2


@pytest.mark.skipif(MPL_311, reason="format of matplotlib < 3.11")
def test_get_layout_format_310(fig, renderer):
    t = ggtext.text(fig, 0.5, 0.5, "a\n**b**")
    _bbox, info, descent = t._get_layout(renderer)
    line, (_w, _h), _x, _y = info[0]
    assert line == "a" and descent > 0


# ---------------------------------------------------------------------------
# Converting artists in place
# ---------------------------------------------------------------------------
def test_set_richtext_property_on_any_text(fig):
    t = fig.text(0.5, 0.5, "**x**")
    assert type(t) is Text and t.get_richtext() is None
    t.set(richtext=True)
    assert isinstance(t, RichText)
    assert t.get_richtext() == RichTextSpec()


def test_text_constructor_accepts_richtext(fig):
    t = Text(0, 0, "**x**", richtext={"fill": "red"})
    assert isinstance(t, RichText) and t.get_richtext().fill == "red"


def test_set_richtext_false_is_noop_on_plain_text(fig):
    t = fig.text(0.5, 0.5, "x")
    t.set(richtext=False)
    assert type(t) is Text


def test_make_rich_and_plain_roundtrip(fig, renderer):
    t = fig.text(0.5, 0.5, "**x**")
    make_rich(t)
    assert is_rich(t)
    make_plain(t)
    assert type(t) is Text and not is_rich(t)
    t.get_window_extent(renderer)


def test_set_richtext_none_turns_plain(fig):
    t = ggtext.text(fig, 0.5, 0.5, "**x**")
    t.set_richtext(None)
    assert type(t) is Text


def test_make_plain_of_constructed_richtext(fig):
    t = fig.add_artist(RichText(0, 0, "x"))
    make_plain(t)
    assert type(t) is Text


def test_subclass_keeps_behaviour(fig):
    class MyText(Text):
        def custom(self):
            return "kept"

    t = MyText(0, 0, "**x**")
    make_rich(t)
    assert isinstance(t, MyText) and isinstance(t, RichText)
    assert t.custom() == "kept"
    assert _rich_class_for(MyText) is type(t)
    make_plain(t)
    assert type(t) is MyText


def test_rich_class_is_cached():
    assert _rich_class_for(Annotation) is _rich_class_for(Annotation)
    assert _rich_class_for(RichText) is RichText


def test_update_from_copies_spec(fig):
    a = ggtext.text(fig, 0, 0, "x", fill="red")
    b = RichText(0, 0, "y")
    b.update_from(a)
    assert b.get_richtext().fill == "red"


def test_get_plain_text():
    t = RichText(0, 0, "**Bold** and <span style='color:red'>red</span>\nnext")
    assert t.get_plain_text() == "Bold and red\nnext"


def test_repr():
    assert repr(RichText(1, 2, "x")) == "RichText(1, 2, 'x')"


def test_pickle(fig):
    ggtext.text(fig, 0.5, 0.5, "**x**", fill="yellow", width=0.5)
    f2 = pickle.loads(pickle.dumps(fig))
    f2.canvas.draw()


def test_pickle_dynamic_subclass(fig_ax):
    f, ax = fig_ax
    ggtext.annotate(ax, "**hi**", (0.5, 0.5), (0.1, 0.1), arrowprops={})
    pickle.loads(pickle.dumps(f)).canvas.draw()


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("fmt", ["png", "pdf", "svg", "ps", "eps"])
def test_all_backends(fig_ax, fmt):
    f, ax = fig_ax
    ggtext.set_title(ax, "**Bold** <span style='color:red'>red</span> $x^2$ <u>u</u>")
    ggtext.text(ax, 0.5, 0.5, "<mark>m</mark> ~~s~~ H<sub>2</sub>O", rotation=30,
                fill="lightblue", box_color="k", r=3, padding=2)  # fmt: skip
    buf = io.BytesIO()
    f.savefig(buf, format=fmt)
    assert buf.getbuffer().nbytes > 1000


def test_svg_contains_text_and_link(fig):
    ggtext.text(fig, 0.5, 0.5, "[**link**](https://example.org) here")
    buf = io.StringIO()
    plt.rcParams["svg.fonttype"] = "none"
    try:
        fig.savefig(buf, format="svg")
    finally:
        plt.rcParams["svg.fonttype"] = "path"
    svg = buf.getvalue()
    assert "link" in svg and "here" in svg
    assert "https://example.org" in svg


def test_colors_are_drawn(fig):
    t = ggtext.text(
        fig, 0.1, 0.5, "<span style='color:#ff0000'>REDREDRED</span>", fontsize=30
    )
    img = render_rgba(fig)
    region = pixels_in_bbox(img, t.get_window_extent())
    assert has_color(region, (255, 0, 0))
    assert not has_color(region, (0, 0, 255))


def test_base_color_applies_to_unstyled_text(fig):
    t = ggtext.text(fig, 0.1, 0.5, "**BLUE**", color="#0000ff", fontsize=30)
    region = pixels_in_bbox(render_rgba(fig), t.get_window_extent())
    assert has_color(region, (0, 0, 255))


def test_box_fill_is_drawn(fig):
    t = ggtext.text(fig, 0.1, 0.5, "box", fill="#00ff00", padding=5, fontsize=20)
    region = pixels_in_bbox(render_rgba(fig), t.get_window_extent(), pad=-3)
    assert has_color(region, (0, 255, 0), tol=5)


def test_background_highlight_is_drawn(fig):
    t = ggtext.text(
        fig, 0.1, 0.5, "<span style='background-color:#00ffff'>hi</span>", fontsize=30
    )
    region = pixels_in_bbox(render_rgba(fig), t.get_window_extent())
    assert has_color(region, (0, 255, 255), tol=5)


def test_underline_draws_below_baseline(fig):
    plain = ggtext.text(fig, 0.1, 0.6, "ooo", fontsize=30, color="#ff0000")
    under = ggtext.text(fig, 0.1, 0.3, "<u>ooo</u>", fontsize=30, color="#ff0000")
    img = render_rgba(fig)

    def red_rows(t):
        region = pixels_in_bbox(img, t.get_window_extent(), pad=0)
        red = (region[..., 0] > 200) & (region[..., 1] < 80)
        return np.nonzero(red.any(axis=1))[0]

    # the underline adds red pixels further down than the letters alone
    assert red_rows(under).max() > red_rows(plain).max()


def test_alpha_is_applied(fig):
    t = ggtext.text(
        fig, 0.1, 0.5, "<span style='color:#000000'>MMMM</span>", fontsize=40, alpha=0.3
    )
    region = pixels_in_bbox(render_rgba(fig), t.get_window_extent())
    assert region[..., :3].min() > 100  # never fully black


def test_path_effects(fig):
    import matplotlib.patheffects as pe

    t = ggtext.text(
        fig,
        0.1,
        0.5,
        "**x**",
        path_effects=[pe.withStroke(linewidth=3, foreground="w")],
    )
    assert t.get_path_effects()
    render_rgba(fig)


def test_registered_image_is_drawn(fig):
    red = np.zeros((4, 4, 3))
    red[..., 0] = 1
    ggtext.register_image("test_red_square", red)
    t = ggtext.text(
        fig, 0.1, 0.5, "img: <img src='test_red_square' width='30' height='30'>"
    )
    region = pixels_in_bbox(render_rgba(fig), t.get_window_extent())
    assert has_color(region, (255, 0, 0), tol=10)


@pytest.mark.parametrize("rotation", [90, 180, 270])
def test_rotated_images(fig, rotation):
    ggtext.register_image("test_blue", np.array([[[0, 0, 255]]], dtype=np.uint8))
    t = ggtext.text(
        fig, 0.5, 0.5, "<img src='test_blue' width='20'>", rotation=rotation
    )
    region = pixels_in_bbox(render_rgba(fig), t.get_window_extent())
    assert has_color(region, (0, 0, 255), tol=10)


def test_image_at_odd_angle_warns(fig):
    ggtext.register_image("test_g", np.ones((2, 2, 3)))
    ggtext.text(fig, 0.5, 0.5, "<img src='test_g'>", rotation=33)
    with pytest.warns(UserWarning, match="multiples of 90"):
        fig.canvas.draw()


def test_missing_image_warns_and_skips(fig):
    t = ggtext.text(fig, 0.5, 0.5, "a <img src='/no/such/file.png'> b")
    with pytest.warns(UserWarning, match="could not load image"):
        fig.canvas.draw()
    assert t.get_window_extent().width > 0


def test_usetex_falls_back_to_plain(fig, monkeypatch):
    t = ggtext.text(fig, 0.5, 0.5, "**x**")
    monkeypatch.setattr(t, "get_usetex", lambda: True)
    monkeypatch.setattr(Text, "draw", lambda self, renderer: None)
    with pytest.warns(UserWarning, match="usetex"):
        t.draw(fig.canvas.get_renderer())


def test_mpl_backgroundcolor_still_works(fig):
    t = ggtext.text(fig, 0.1, 0.5, "**x**", backgroundcolor="#ff00ff", fontsize=30)
    region = pixels_in_bbox(render_rgba(fig), t.get_window_extent(), pad=3)
    assert has_color(region, (255, 0, 255), tol=5)


def test_tight_bbox_includes_rich_text(fig_ax):
    f, ax = fig_ax
    t = ggtext.text(ax, 1.5, 0.5, "**far outside the axes**", transform=ax.transAxes)
    buf = io.BytesIO()
    f.savefig(buf, format="png", bbox_inches="tight")
    tight = f.get_tightbbox(f.canvas.get_renderer())
    assert tight.x1 * f.dpi >= t.get_window_extent().x1 - 1


@pytest.mark.parametrize("layout", ["constrained", "tight"])
def test_layout_engines_make_room(layout):
    f, ax = plt.subplots(figsize=(4, 3), dpi=100, layout=layout)
    long = "<span style='font-size:20pt'>**Big**</span><br>second<br>third"
    ggtext.set_title(ax, long)
    f.canvas.draw()
    title = ax.title.get_window_extent()
    assert title.y0 >= ax.bbox.y1 - 1  # title does not overlap the axes
    assert title.y1 <= f.bbox.y1 + 1  # and fits in the figure


def test_relayout_runs_twice_for_relative_widths():
    f, ax = plt.subplots(figsize=(4, 3), dpi=100, layout="tight")
    calls = []
    engine = f.get_layout_engine()
    original = engine.execute
    engine.execute = lambda fig: (calls.append(1), original(fig))
    ggtext.set_title(ax, "word " * 30, width=1.0)
    f.canvas.draw()
    assert len(calls) == 2


def test_no_warnings_for_plain_usage(fig):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        ggtext.text(fig, 0.5, 0.5, "**fine** <span style='color:red'>ok</span>")
        fig.canvas.draw()


# ---------------------------------------------------------------------------
# Fractional alignment, margins, size limits
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("mode", ["default", "anchor"])
def test_fractional_alignment(fig, renderer, mode):
    t = ggtext.text(
        fig, 0.5, 0.5, "**some text**", ha=0.25, va=0.75, rotation_mode=mode
    )
    assert t.get_ha() == 0.25 and t.get_va() == 0.75
    e = t.get_window_extent(renderer)
    x, y = fig.transFigure.transform((0.5, 0.5))
    assert x - e.x0 == pytest.approx(0.25 * e.width, abs=0.5)
    assert y - e.y0 == pytest.approx(0.75 * e.height, abs=0.5)


def test_fractional_alignment_matches_names(fig, renderer):
    a = ggtext.text(fig, 0.5, 0.5, "abc", ha=1.0, va=0.0)
    b = ggtext.text(fig, 0.5, 0.5, "abc", ha="right", va="bottom")
    np.testing.assert_allclose(
        a.get_window_extent(renderer).extents, b.get_window_extent(renderer).extents
    )


def test_plain_text_rejects_fractional_alignment(fig):
    with pytest.raises(ValueError):
        fig.text(0.5, 0.5, "x", ha=0.3)


def test_margin_adds_space_but_box_stays_inside(fig, renderer):
    a = ggtext.text(fig, 0.5, 0.5, "abc", fill="red")
    b = ggtext.text(fig, 0.5, 0.5, "abc", fill="red", margin=(10, 0, 0, 20))
    ea, eb = a.get_window_extent(renderer), b.get_window_extent(renderer)
    px = 100 / 72
    assert eb.width == pytest.approx(ea.width + 20 * px, abs=0.5)
    assert eb.height == pytest.approx(ea.height + 10 * px, abs=0.5)
    assert b._rich_layout(renderer).box[2] == pytest.approx(ea.width, abs=0.5)


def test_fixed_height_overflows_like_ggtext(fig, renderer):
    t = ggtext.text(fig, 0.5, 0.5, "word " * 80, width="1in", height="0.3in")
    assert t.get_window_extent(renderer).height == pytest.approx(30, abs=0.5)


@pytest.mark.parametrize(
    "kw, which, value",
    [
        ({"width": "3in", "maxwidth": "1in"}, "w", 100),
        ({"width": "1in", "minwidth": "2in"}, "w", 200),
        ({"minwidth": "2in"}, "w", 200),
        ({"width": "1in", "minheight": "1in"}, "h", 100),
        ({"width": "1in", "maxheight": "0.2in"}, "h", 20),
    ],
)
def test_size_limits(fig, renderer, kw, which, value):
    t = ggtext.text(fig, 0.5, 0.5, "word " * 30 if "maxheight" in kw else "hi", **kw)
    e = t.get_window_extent(renderer)
    assert (e.width if which == "w" else e.height) == pytest.approx(value, abs=0.5)
