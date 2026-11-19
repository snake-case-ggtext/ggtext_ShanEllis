"""Tests for the plotnine integration (ggtext.plotnine)."""

import io

import numpy as np
import pandas as pd
import pytest

plotnine = pytest.importorskip("plotnine")

from plotnine import (
    aes,
    element_blank,
    element_text,
    facet_grid,
    facet_wrap,
    geom_point,
    ggplot,
    labs,
    scale_x_continuous,
    theme,
    theme_bw,
    theme_gray,
)

from ggtext import (
    RichText,
    RichTextSpec,
    element_markdown,
    element_textbox,
    element_textbox_simple,
    geom_richtext,
    geom_textbox,
)

from .conftest import has_color, pixels_in_bbox, render_rgba

pytestmark = pytest.mark.plotnine

DF = pd.DataFrame(
    {
        "x": [1.0, 2.0, 3.0, 4.0],
        "y": [1.0, 3.0, 2.0, 4.0],
        "g": ["a", "b", "a", "b"],
        "f": ["p", "p", "q", "q"],
        "lab": [
            "**one**",
            "*two*",
            "<span style='color:red'>three</span>",
            "x<sup>2</sup>",
        ],
    }
)

TITLE = "**Bold** and <span style='color:#ff0000'>red</span>"


def base_plot():
    return ggplot(DF, aes("x", "y", color="g")) + geom_point()


def draw(p):
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    fig = p.draw()
    if not isinstance(fig.canvas, FigureCanvasAgg):
        FigureCanvasAgg(fig)
    fig.canvas.draw()
    return fig


# ---------------------------------------------------------------------------
# Elements
# ---------------------------------------------------------------------------
class TestElements:
    def test_element_markdown_is_element_text(self):
        el = element_markdown(size=12, color="blue")
        assert isinstance(el, element_text)
        assert el.properties["size"] == 12
        assert isinstance(el.properties["richtext"], RichTextSpec)
        assert el.spec == RichTextSpec()

    def test_box_options(self):
        el = element_markdown(
            fill="yellow", box_color="k", r=3, padding=(2, 4), linewidth=1
        )
        s = el.spec
        assert (s.fill, s.box_color, s.r, s.linewidth) == ("yellow", "k", 3, 1)
        assert s.padding == (2, 4, 2, 4)

    def test_ggplot2_spellings(self):
        el = element_markdown(colour="red", hjust=0, vjust=1, angle=45, lineheight=1.3,
                              face="bold", **{"box.colour": "blue", "linetype": "dashed"})  # fmt: skip
        p = el.properties
        assert p["color"] == "red" and p["ha"] == "left" and p["va"] == "top"
        assert p["rotation"] == 45 and p["linespacing"] == 1.3 and p["weight"] == "bold"
        assert el.spec.box_color == "blue" and el.spec.linestyle == "dashed"

    @pytest.mark.parametrize(
        "value, expected",
        [(0, "left"), (0.5, "center"), (1, "right"), ("right", "right")],
    )
    def test_numeric_halign(self, value, expected):
        assert element_markdown(halign=value).spec.halign == expected

    def test_markdown_options(self):
        s = element_markdown(markdown=False, newline="space", math=False).spec
        assert not s.markdown and s.newline == "space" and not s.math

    def test_element_textbox(self):
        el = element_textbox(
            width=0.8, height="1in", valign=0.5, orientation="left-rotated"
        )
        assert el.spec.width == 0.8 and el.spec.height == "1in"
        assert el.spec.valign == "center"
        assert el.properties["rotation"] == 90

    def test_orientation_overrides_angle(self):
        el = element_textbox(orientation="right-rotated", angle=10)
        assert el.properties["rotation"] == 270

    def test_bad_orientation(self):
        with pytest.raises(ValueError, match="orientation"):
            element_textbox(orientation="sideways")

    def test_textbox_size_limits(self):
        s = element_textbox(
            width=1.0,
            minwidth="1in",
            maxwidth="5in",
            minheight="0.5in",
            maxheight="2in",
        ).spec
        assert (s.minwidth, s.maxwidth, s.minheight, s.maxheight) == (
            "1in",
            "5in",
            "0.5in",
            "2in",
        )

    def test_textbox_simple_defaults(self):
        el = element_textbox_simple()
        assert el.spec.width == 1.0 and el.spec.halign == "left"
        assert el.properties["linespacing"] == 1.2
        assert element_textbox_simple(width=0.5, lineheight=2).spec.width == 0.5
        assert element_textbox_simple(lineheight=2).properties["linespacing"] == 2

    def test_bad_width(self):
        with pytest.raises(ValueError, match="fractions"):
            element_textbox(width=3)


# ---------------------------------------------------------------------------
# Theming every kind of text
# ---------------------------------------------------------------------------
RED = "<span style='color:#ff0000'>**r**</span>"
_LABEL_FOR = {
    "plot_title": "title", "plot_subtitle": "subtitle", "plot_caption": "caption",
    "plot_tag": "tag", "axis_title_x": "x", "axis_title_y": "y", "legend_title": "color",
}  # fmt: skip


def find_text(fig, s):
    """The text artist in *fig* whose string is *s*."""
    from matplotlib.text import Text

    found = [t for t in fig.findobj(Text) if t.get_text() == s]
    assert found, f"no text {s!r} in figure"
    return found[0]


@pytest.mark.parametrize("themeable", list(_LABEL_FOR))
def test_single_text_themeables(themeable):
    labels = {k: k for k in _LABEL_FOR.values()}  # short plain labels
    labels[_LABEL_FOR[themeable]] = f"**{themeable}** {RED}"
    p = base_plot() + labs(**labels) + theme(**{themeable: element_markdown()})
    fig = draw(p)
    artist = find_text(fig, labels[_LABEL_FOR[themeable]])
    assert isinstance(artist, RichText)
    # the other labels stay plain text
    for name, value in labels.items():
        if name != _LABEL_FOR[themeable]:
            assert not isinstance(find_text(fig, value), RichText)
    # the layout engine positions it (not at the origin) and
    # the red part is drawn where the artist is
    ext = artist.get_window_extent()
    assert ext.x0 > 0 or ext.y0 > 0
    assert has_color(pixels_in_bbox(render_rgba(fig), ext), (255, 0, 0))


@pytest.mark.parametrize("themeable", ["legend_text", "strip_text_x", "strip_text"])
def test_sequence_themeables(themeable):
    p = base_plot() + facet_wrap("f") + theme(**{themeable: element_markdown()})
    fig = draw(p)
    names = ["a", "b"] if themeable == "legend_text" else ["p", "q"]
    assert all(isinstance(find_text(fig, n), RichText) for n in names)


def test_strip_text_y_on_facet_grid():
    p = (
        base_plot()
        + facet_grid("f", "g")
        + theme(strip_text_y=element_markdown(rotation=-90))
    )
    draw(p)
    assert all(isinstance(x, RichText) for x in p.theme.targets.strip_text_y)
    assert not any(isinstance(x, RichText) for x in p.theme.targets.strip_text_x)


@pytest.mark.parametrize(
    "themeable, axis",
    [("axis_text_x", "x"), ("axis_text_y", "y"), ("axis_text", "both")],
)
def test_tick_labels(themeable, axis):
    p = (
        base_plot()
        + scale_x_continuous(breaks=[1, 2, 3, 4], labels=["**a**", "*b*", "c", "d"])
        + theme(**{themeable: element_markdown()})
    )
    fig = draw(p)
    ax = fig.axes[0]
    xr = all(isinstance(t.label1, RichText) for t in ax.xaxis.get_major_ticks())
    yr = all(isinstance(t.label1, RichText) for t in ax.yaxis.get_major_ticks())
    assert (xr, yr) == {"x": (True, False), "y": (False, True), "both": (True, True)}[
        axis
    ]


def test_text_themeable_applies_everywhere():
    p = base_plot() + labs(title=TITLE, x="x", y="y") + theme(text=element_markdown())
    fig = draw(p)
    t = p.theme.targets
    assert isinstance(t.plot_title, RichText)
    assert isinstance(t.axis_title_x, RichText)
    assert isinstance(find_text(fig, "a"), RichText)  # legend label
    assert isinstance(fig.axes[0].xaxis.get_major_ticks()[0].label1, RichText)


def test_works_with_complete_themes_and_merging():
    # theme_bw defines plot_title; adding element_markdown merges into it
    p = (
        base_plot()
        + labs(title=TITLE)
        + theme_bw()
        + theme(plot_title=element_markdown(size=20))
    )
    draw(p)
    title = p.theme.targets.plot_title
    assert isinstance(title, RichText) and title.get_fontsize() == 20


def test_specific_element_text_after_markdown_keeps_markdown():
    p = (
        base_plot() + labs(title=TITLE)
        + theme(plot_title=element_markdown())
        + theme(plot_title=element_text(color="blue"))
    )  # fmt: skip
    draw(p)
    title = p.theme.targets.plot_title
    assert isinstance(title, RichText)


def test_element_blank_after_markdown():
    p = (
        base_plot()
        + labs(title=TITLE)
        + theme(plot_title=element_markdown())
        + theme(plot_title=element_blank())
    )
    draw(p)
    assert not p.theme.targets.plot_title.get_visible()


def test_plain_plots_are_unchanged():
    p = base_plot() + labs(title="**not markdown**")
    draw(p)
    assert type(p.theme.targets.plot_title).__name__ == "Text"


# ---------------------------------------------------------------------------
# Layout: plotnine must reserve the right space
# ---------------------------------------------------------------------------
def _panel_area(fig):
    from matplotlib.transforms import Bbox

    return Bbox.union([ax.get_window_extent() for ax in fig.axes])


def test_tall_title_gets_space():
    big = "<span style='font-size:30pt'>Big</span><br>second line<br>third line"
    p = base_plot() + labs(title=big) + theme(plot_title=element_markdown())
    fig = draw(p)
    title = p.theme.targets.plot_title.get_window_extent()
    assert title.y0 >= _panel_area(fig).y1 - 1
    assert title.y1 <= fig.bbox.y1 + 1


def test_textbox_simple_spans_panel_width_and_does_not_overlap():
    long = " ".join(["Lorem ipsum dolor sit amet."] * 12)
    p = (
        base_plot()
        + labs(title="T", subtitle=long)
        + theme(plot_subtitle=element_textbox_simple(fill="#eeeeee", padding=4))
    )
    fig = draw(p)
    sub = p.theme.targets.plot_subtitle
    ext = sub.get_window_extent()
    panels = _panel_area(fig)
    assert ext.width == pytest.approx(panels.width, abs=1.0)
    assert ext.x0 == pytest.approx(panels.x0, abs=1.0)
    assert len(sub._rich_layout(fig.canvas.get_renderer()).lines) > 2
    assert ext.y0 >= panels.y1 - 1  # no overlap with the panels
    title = p.theme.targets.plot_title.get_window_extent()
    assert title.y0 >= ext.y1 - 1  # nor with the title


def test_rotated_textbox_axis_title():
    p = (
        base_plot()
        + labs(y="**y** " * 30)
        + theme(
            axis_title_y=element_textbox(
                orientation="left-rotated", width=1.0, fill="#ddd"
            )
        )
    )
    fig = draw(p)
    ext = p.theme.targets.axis_title_y.get_window_extent()
    panels = _panel_area(fig)
    assert ext.height == pytest.approx(panels.height, abs=1.0)
    assert ext.x1 <= panels.x0 + 1


def test_rotated_tick_labels_get_space():
    labels = ["**a long label**", "*another long label*", "c", "d"]
    p = (
        base_plot()
        + scale_x_continuous(breaks=[1, 2, 3, 4], labels=labels)
        + theme(axis_text_x=element_markdown(rotation=90))
    )
    fig = draw(p)
    ax = fig.axes[0]
    lowest = min(t.label1.get_window_extent().y0 for t in ax.xaxis.get_major_ticks())
    assert lowest >= 0
    xtitle = p.theme.targets.axis_title_x.get_window_extent()
    assert xtitle.y1 <= lowest + 1


def test_legend_with_rich_text_fits():
    p = (
        base_plot()
        + labs(color="<span style='font-size:16pt'>**Grp**</span><br>sub")
        + theme(legend_title=element_markdown(), legend_text=element_markdown())
    )
    fig = draw(p)
    title = find_text(fig, "<span style='font-size:16pt'>**Grp**</span><br>sub")
    assert isinstance(title, RichText)
    title = title.get_window_extent()
    assert title.x0 >= _panel_area(fig).x1
    assert title.x1 <= fig.bbox.x1 + 1


@pytest.mark.parametrize("fmt", ["png", "pdf", "svg"])
def test_save_formats(fmt, tmp_path):
    p = base_plot() + labs(title=TITLE) + theme(plot_title=element_markdown())
    out = tmp_path / f"plot.{fmt}"
    p.save(out, verbose=False, width=4, height=3)
    assert out.stat().st_size > 1000


# ---------------------------------------------------------------------------
# Geoms
# ---------------------------------------------------------------------------
def _rich_artists(fig):
    return [a for a in fig.axes[0].get_children() if isinstance(a, RichText)]


class TestGeomRichtext:
    def test_creates_rich_artists(self):
        fig = draw(ggplot(DF, aes("x", "y", label="lab")) + geom_richtext())
        arts = _rich_artists(fig)
        assert len(arts) == 4
        spec = arts[0].get_richtext()
        assert spec.fill is not None and spec.box_color is not None
        assert {a.get_text() for a in arts} == set(DF["lab"])

    def test_no_box(self):
        fig = draw(
            ggplot(DF, aes("x", "y", label="lab"))
            + geom_richtext(fill=None, label_size=0)
        )
        spec = _rich_artists(fig)[0].get_richtext()
        assert spec.fill is None and spec.box_color is None and not spec.has_box

    def test_aesthetics(self):
        fig = draw(
            ggplot(DF, aes("x", "y", label="lab"))
            + geom_richtext(
                angle=30, size=14, color="#0000ff", label_color="red", label_r=4
            )
        )
        a = _rich_artists(fig)[0]
        assert a.get_rotation() == 30 and a.get_fontsize() == 14
        spec = a.get_richtext()
        assert spec.r == 4
        from matplotlib.colors import to_rgba

        assert to_rgba(spec.box_color) == pytest.approx((1, 0, 0, 1))

    def test_fill_mapping(self):
        fig = draw(ggplot(DF, aes("x", "y", label="lab", fill="g")) + geom_richtext())
        fills = {a.get_richtext().fill for a in _rich_artists(fig)}
        assert len(fills) == 2

    def test_format_string_and_missing_labels(self):
        df = DF.assign(v=[1.234, np.nan, 3.0, 4.5])
        fig = draw(
            ggplot(df, aes("x", "y", label="v"))
            + geom_richtext(format_string="**{:.1f}**")
        )
        texts = sorted(a.get_text() for a in _rich_artists(fig))
        assert texts == ["**1.2**", "**3.0**", "**4.5**"]

    def test_nudge(self):
        fig = draw(ggplot(DF, aes("x", "y", label="lab")) + geom_richtext(nudge_y=1))
        assert min(a.get_position()[1] for a in _rich_artists(fig)) == pytest.approx(
            2.0
        )

    def test_drawn_pixels(self):
        df = pd.DataFrame(
            {"x": [0], "y": [0], "lab": ["<span style='color:#ff0000'>**RED**</span>"]}
        )
        fig = draw(ggplot(df, aes("x", "y", label="lab")) + geom_richtext(size=30))
        art = _rich_artists(fig)[0]
        assert has_color(
            pixels_in_bbox(render_rgba(fig), art.get_window_extent()), (255, 0, 0)
        )

    def test_legend_key(self):
        draw(ggplot(DF, aes("x", "y", label="lab", color="g")) + geom_richtext())

    def test_markdown_off(self):
        fig = draw(
            ggplot(DF, aes("x", "y", label="lab")) + geom_richtext(markdown=False)
        )
        assert not _rich_artists(fig)[0].get_richtext().markdown


class TestGeomTextbox:
    def test_width_and_wrapping(self):
        df = pd.DataFrame({"x": [0], "y": [0], "lab": ["word " * 40]})
        fig = draw(ggplot(df, aes("x", "y", label="lab")) + geom_textbox(width="2in"))
        a = _rich_artists(fig)[0]
        assert a.get_window_extent().width == pytest.approx(2 * fig.dpi, abs=1)
        assert len(a._rich_layout(fig.canvas.get_renderer()).lines) > 2

    def test_relative_width_is_fraction_of_panel(self):
        df = pd.DataFrame({"x": [0], "y": [0], "lab": ["word " * 40]})
        fig = draw(ggplot(df, aes("x", "y", label="lab")) + geom_textbox(width=0.5))
        a = _rich_artists(fig)[0]
        assert a.get_window_extent().width == pytest.approx(
            fig.axes[0].bbox.width / 2, abs=1
        )

    def test_maxwidth_shrink_to_fit(self):
        df = pd.DataFrame({"x": [0, 1], "y": [0, 1], "lab": ["short", "word " * 40]})
        fig = draw(
            ggplot(df, aes("x", "y", label="lab"))
            + geom_textbox(width=None, maxwidth="2in")
        )
        widths = sorted(a.get_window_extent().width for a in _rich_artists(fig))
        assert widths[0] < 100 and widths[1] <= 2 * fig.dpi + 1

    def test_alignment_aesthetics(self):
        df = pd.DataFrame(
            {"x": [0], "y": [0], "lab": ["x"], "h": [0.5], "v": ["bottom"]}
        )
        fig = draw(
            ggplot(df, aes("x", "y", label="lab", halign="h", valign="v"))
            + geom_textbox(height="1in")
        )
        spec = _rich_artists(fig)[0].get_richtext()
        assert spec.halign == "center" and spec.valign == "bottom"

    @pytest.mark.parametrize(
        "orientation, angle",
        [("left-rotated", 90), ("right-rotated", 270), ("inverted", 180)],
    )
    def test_orientation(self, orientation, angle):
        df = pd.DataFrame({"x": [0], "y": [0], "lab": ["x"], "o": [orientation]})
        fig = draw(
            ggplot(df, aes("x", "y", label="lab", orientation="o")) + geom_textbox()
        )
        assert _rich_artists(fig)[0].get_rotation() == angle

    def test_box_styling(self):
        df = pd.DataFrame({"x": [0], "y": [0], "lab": ["x"]})
        fig = draw(
            ggplot(df, aes("x", "y", label="lab"))
            + geom_textbox(
                fill="lightyellow", box_color="gray", box_r=2, box_padding=8, box_size=0
            )
        )
        spec = _rich_artists(fig)[0].get_richtext()
        assert spec.r == 2 and spec.padding == (8,) * 4
        assert spec.box_color is None  # box_size=0 means no outline


def test_full_example_renders_without_warnings():
    import warnings

    p = (
        ggplot(DF, aes("x", "y", color="g", label="lab"))
        + geom_point()
        + geom_richtext(nudge_y=0.3)
        + facet_wrap("f")
        + labs(
            title=TITLE,
            subtitle="long " * 40,
            caption="*caption*",
            x="x<sub>i</sub>",
            y="y<sup>2</sup>",
        )
        + theme_gray()
        + theme(
            plot_title=element_markdown(),
            plot_subtitle=element_textbox_simple(),
            plot_caption=element_markdown(),
            axis_title=element_markdown(),
            strip_text=element_markdown(),
            legend_text=element_markdown(),
        )
    )
    buf = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        p.save(buf, format="png", verbose=False)
    assert buf.getbuffer().nbytes > 1000


def test_relative_width_in_composition_uses_own_plot():
    """In ``p1 | p2`` each subtitle wraps to its own plot's panels."""
    subs = ["word " * 40, "other " * 40]
    p1 = (
        base_plot()
        + labs(subtitle=subs[0])
        + theme(plot_subtitle=element_textbox_simple())
    )
    p2 = (
        base_plot()
        + labs(subtitle=subs[1])
        + theme(plot_subtitle=element_textbox_simple())
    )
    buf = io.BytesIO()
    comp = p1 | p2
    comp.save(buf, format="png", width=9, height=4, verbose=False)
    fig = comp.figure
    for sub in subs:
        text = next(t for t in fig.texts if t.get_text() == sub)
        assert isinstance(text, RichText)
        own = [ax for ax in fig.axes if ax in text._ggtext_panels]
        assert len(own) == 1
        assert text.get_window_extent().width == pytest.approx(
            own[0].bbox.width, abs=1.0
        )


# ---------------------------------------------------------------------------
# ggtext conventions in the geoms: anchor rotation, justification,
# mappable outline/text colors, margins and size limits
# ---------------------------------------------------------------------------
from ggtext.plotnine.geoms import resolve_just


class TestResolveJust:
    @pytest.mark.parametrize(
        "value, axis, expected",
        [
            ("left", "x", "left"), ("right", "x", "right"), ("center", "x", "center"),
            ("middle", "x", "center"), (0, "x", "left"), (1, "x", "right"),
            (0.5, "x", "center"), (0.25, "x", 0.25), ("bottom", "y", "bottom"),
            ("top", "y", "top"), (0, "y", "bottom"), (1, "y", "top"),
            ("baseline", "y", "baseline"), ("center_baseline", "y", "center_baseline"),
        ],
    )  # fmt: skip
    def test_values(self, value, axis, expected):
        assert resolve_just(value, 0.3, axis) == expected

    @pytest.mark.parametrize(
        "value, npc, axis, expected",
        [
            ("inward", 0.1, "x", "left"), ("inward", 0.9, "x", "right"),
            ("inward", 0.5, "x", "center"), ("outward", 0.1, "x", "right"),
            ("outward", 0.9, "x", "left"), ("inward", 0.1, "y", "bottom"),
            ("outward", 0.9, "y", "bottom"),
        ],
    )  # fmt: skip
    def test_inward_outward(self, value, npc, axis, expected):
        assert resolve_just(value, npc, axis) == expected

    def test_unknown(self):
        from plotnine.exceptions import PlotnineError

        with pytest.raises(PlotnineError, match="Unknown justification"):
            resolve_just("sideways", 0.5, "x")


ONE = pd.DataFrame({"x": [0.5], "y": [0.5], "lab": ["The **quick** *brown* fox."]})


def _one_label(fig):
    (a,) = _rich_artists(fig)
    return a, fig.axes[0].transData.transform((0.5, 0.5))


class TestRotation:
    def test_anchor_rotation_is_default(self):
        fig = draw(
            ggplot(ONE, aes("x", "y", label="lab")) + geom_richtext(angle=90, ha="left")
        )
        a, (ax_, ay_) = _one_label(fig)
        assert a.get_rotation_mode() == "anchor"
        ext = a.get_window_extent()
        # ggtext: rotated 90 degrees around the anchor, the text starts at
        # the anchor and runs upwards, centered on it horizontally
        assert ext.y0 == pytest.approx(ay_, abs=1)
        assert (ext.x0 + ext.x1) / 2 == pytest.approx(ax_, abs=1)

    def test_rotation_135_points_up_left(self):
        fig = draw(
            ggplot(ONE, aes("x", "y", label="lab"))
            + geom_richtext(angle=135, ha="left")
        )
        a, (ax_, ay_) = _one_label(fig)
        ext = a.get_window_extent()
        assert ext.x1 < ax_ + 15 and ext.y0 > ay_ - 15  # up and to the left

    def test_plotnine_rotation_mode_available(self):
        fig = draw(
            ggplot(ONE, aes("x", "y", label="lab"))
            + geom_richtext(angle=90, rotation_mode="default")
        )
        a, _ = _one_label(fig)
        assert a.get_rotation_mode() == "default"

    def test_textbox_orientation_rotates_around_anchor(self):
        fig = draw(
            ggplot(ONE, aes("x", "y", label="lab"))
            + geom_textbox(orientation="left-rotated", ha="left", va="bottom")
        )
        a, (ax_, ay_) = _one_label(fig)
        ext = a.get_window_extent()
        # box rotated 90 degrees about its bottom-left corner
        assert ext.x1 == pytest.approx(ax_, abs=1) and ext.y0 == pytest.approx(
            ay_, abs=1
        )


class TestJustification:
    @pytest.mark.parametrize("kw", [{"hjust": 0.25}, {"ha": 0.25}])
    def test_numeric_hjust(self, kw):
        fig = draw(ggplot(ONE, aes("x", "y", label="lab")) + geom_richtext(**kw))
        a, (ax_, _) = _one_label(fig)
        ext = a.get_window_extent()
        assert ax_ - ext.x0 == pytest.approx(0.25 * ext.width, abs=1)

    def test_vjust_alias_and_mapping(self):
        df = ONE.assign(h=[1.0], v=["top"])
        fig = draw(
            ggplot(df, aes("x", "y", label="lab", hjust="h", vjust="v"))
            + geom_richtext()
        )
        a, (ax_, ay_) = _one_label(fig)
        ext = a.get_window_extent()
        assert ext.x1 == pytest.approx(ax_, abs=1) and ext.y1 == pytest.approx(
            ay_, abs=1
        )

    def test_inward(self):
        df = pd.DataFrame(
            {"x": [0.0, 1.0], "y": [0.5, 0.5], "lab": ["left side", "right side"]}
        )
        fig = draw(
            ggplot(df, aes("x", "y", label="lab")) + geom_richtext(hjust="inward")
        )
        arts = sorted(_rich_artists(fig), key=lambda t: t.get_position()[0])
        assert [t.get_ha() for t in arts] == ["left", "right"]

    def test_lines_follow_hjust_like_gridtext(self):
        df = ONE.assign(lab=["a<br>longer line"])
        fig = draw(ggplot(df, aes("x", "y", label="lab")) + geom_richtext(hjust=1))
        assert _rich_artists(fig)[0].get_richtext().halign == "right"
        fig = draw(
            ggplot(df, aes("x", "y", label="lab"))
            + geom_richtext(hjust=1, halign="left")
        )
        assert _rich_artists(fig)[0].get_richtext().halign == "left"


class TestMappableColors:
    def test_label_color_and_size_are_aesthetics(self):
        from matplotlib.colors import to_hex

        df = pd.DataFrame({"x": [0, 1], "y": [0, 1], "lab": ["a", "b"],
                           "lc": ["#ff0000", "#0000ff"], "ls": [0.5, 2.0]})  # fmt: skip
        fig = draw(
            ggplot(df, aes("x", "y", label="lab", label_colour="lc", label_size="ls"))
            + geom_richtext()
        )
        specs = {t.get_text(): t.get_richtext() for t in _rich_artists(fig)}
        assert to_hex(specs["a"].box_color) == "#ff0000" and specs["a"].linewidth == 0.5
        assert to_hex(specs["b"].box_color) == "#0000ff" and specs["b"].linewidth == 2.0

    def test_text_color_separate_from_outline(self):
        from matplotlib.colors import to_hex

        fig = draw(
            ggplot(ONE, aes("x", "y", label="lab"))
            + geom_richtext(color="#00ff00", text_color="#ff0000")
        )
        a, _ = _one_label(fig)
        assert to_hex(a.get_color()) == "#ff0000"
        fig = draw(
            ggplot(ONE, aes("x", "y", label="lab"))
            + geom_richtext(text_color="#ff0000", label_color="#0000ff")
        )
        a, _ = _one_label(fig)
        assert to_hex(a.get_richtext().box_color) == "#0000ff"

    def test_label_color_none_means_no_outline(self):
        fig = draw(
            ggplot(ONE, aes("x", "y", label="lab")) + geom_richtext(label_color="none")
        )
        assert _one_label(fig)[0].get_richtext().box_color is None

    def test_textbox_box_color_mapping(self):
        df = pd.DataFrame(
            {
                "x": [0, 1],
                "y": [0, 1],
                "lab": ["a", "b"],
                "bc": ["red", "blue"],
                "bs": [1.0, 0.0],
            }
        )
        fig = draw(
            ggplot(df, aes("x", "y", label="lab", box_colour="bc", box_size="bs"))
            + geom_textbox()
        )
        specs = {t.get_text(): t.get_richtext() for t in _rich_artists(fig)}
        assert specs["a"].box_color is not None and specs["a"].linewidth == 1.0
        assert specs["b"].box_color is None  # size 0: no outline


class TestMarginsAndLimits:
    def test_label_margin_moves_box_from_anchor(self):
        fig = draw(
            ggplot(ONE, aes("x", "y", label="lab"))
            + geom_richtext(ha="left", label_margin=10)
        )
        a, (ax_, _) = _one_label(fig)
        L = a._rich_layout(fig.canvas.get_renderer())
        assert a.get_richtext().margin == (10.0,) * 4
        assert L.box[0] == pytest.approx(10 * fig.dpi / 72, abs=0.5)
        assert a.get_window_extent().x0 == pytest.approx(ax_, abs=1)

    def test_textbox_width_clamped(self):
        df = pd.DataFrame({"x": [0], "y": [0], "lab": ["word " * 40]})
        fig = draw(
            ggplot(df, aes("x", "y", label="lab"))
            + geom_textbox(width="4in", maxwidth="2in")
        )
        assert _rich_artists(fig)[0].get_window_extent().width == pytest.approx(
            2 * fig.dpi, abs=1
        )
        fig = draw(
            ggplot(df, aes("x", "y", label="lab"))
            + geom_textbox(width="1in", minwidth="3in")
        )
        assert _rich_artists(fig)[0].get_window_extent().width == pytest.approx(
            3 * fig.dpi, abs=1
        )

    def test_textbox_minwidth_widens_short_text(self):
        df = pd.DataFrame({"x": [0], "y": [0], "lab": ["hi"]})
        fig = draw(
            ggplot(df, aes("x", "y", label="lab"))
            + geom_textbox(width=None, minwidth="2in")
        )
        assert _rich_artists(fig)[0].get_window_extent().width == pytest.approx(
            2 * fig.dpi, abs=1
        )

    def test_textbox_height_limits(self):
        df = pd.DataFrame({"x": [0], "y": [0], "lab": ["word " * 60]})
        fig = draw(
            ggplot(df, aes("x", "y", label="lab")) + geom_textbox(maxheight="0.5in")
        )
        assert _rich_artists(fig)[0].get_window_extent().height == pytest.approx(
            0.5 * fig.dpi, abs=1
        )
        df = pd.DataFrame({"x": [0], "y": [0], "lab": ["hi"]})
        fig = draw(
            ggplot(df, aes("x", "y", label="lab")) + geom_textbox(minheight="1in")
        )
        assert _rich_artists(fig)[0].get_window_extent().height == pytest.approx(
            fig.dpi, abs=1
        )

    def test_textbox_box_margin(self):
        df = pd.DataFrame({"x": [0], "y": [0], "lab": ["hi"]})
        fig = draw(
            ggplot(df, aes("x", "y", label="lab"))
            + geom_textbox(width="1in", box_margin=9)
        )
        a = _rich_artists(fig)[0]
        assert a.get_window_extent().width == pytest.approx(
            fig.dpi + 2 * 9 * fig.dpi / 72, abs=1
        )
