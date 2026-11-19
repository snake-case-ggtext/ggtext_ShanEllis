"""ggtext.enable / disable / enabled: switching the ``richtext`` property."""

from __future__ import annotations

import io
import pickle

import pytest
from matplotlib.figure import Figure
from matplotlib.text import Text

import ggtext
from ggtext import RichText, is_rich


def _has_property() -> bool:
    return hasattr(Text, "set_richtext") and hasattr(Text, "get_richtext")


@pytest.fixture(autouse=True)
def _restore_property():
    # Tests run in random order; never leak a disabled property.
    yield
    ggtext.enable()


def test_enabled_on_import():
    assert _has_property()


def test_disable_and_enable(fig: Figure):
    ggtext.disable()
    assert not _has_property()
    with pytest.raises(AttributeError, match="richtext"):
        fig.text(0.5, 0.5, "**x**", richtext=True)
    ggtext.enable()
    assert is_rich(fig.text(0.5, 0.5, "**x**", richtext=True))


def test_disable_and_enable_are_idempotent():
    ggtext.disable()
    ggtext.disable()
    assert not _has_property()
    ggtext.enable()
    ggtext.enable()
    assert _has_property()


def test_enabled_scopes_the_property(fig: Figure):
    ggtext.disable()
    with ggtext.enabled():
        t = fig.text(0.5, 0.5, "**x**", richtext=True)
        assert _has_property()
    assert not _has_property()
    assert is_rich(t)  # converted text stays rich after the block
    fig.savefig(io.BytesIO())


def test_enabled_keeps_property_when_already_enabled():
    with ggtext.enabled():
        pass
    assert _has_property()


def test_enabled_nests():
    ggtext.disable()
    with ggtext.enabled():
        with ggtext.enabled():
            pass
        assert _has_property()
    assert not _has_property()


def test_enabled_restores_state_on_error():
    ggtext.disable()
    with pytest.raises(RuntimeError), ggtext.enabled():
        raise RuntimeError
    assert not _has_property()


def test_enabled_as_decorator(fig: Figure):
    ggtext.disable()

    @ggtext.enabled()
    def make():
        return fig.text(0.5, 0.5, "**x**", richtext=True)

    assert is_rich(make())
    assert not _has_property()


def test_helpers_work_while_disabled(fig: Figure):
    # Only the Text property is removed; ggtext's own API does not need it.
    ggtext.disable()
    assert is_rich(ggtext.text(fig, 0.5, 0.5, "**x**"))
    assert is_rich(ggtext.textbox(fig, 0.5, 0.5, "**x**"))
    t = RichText(0, 0, "**x**", richtext={"fill": "red"})
    spec = t.get_richtext()
    assert spec is not None and spec.fill == "red"
    fig.savefig(io.BytesIO())


def test_rich_figure_pickles_while_disabled(fig: Figure):
    ggtext.text(fig, 0.5, 0.5, "**x**")
    ggtext.disable()
    restored = pickle.loads(pickle.dumps(fig))
    assert any(is_rich(t) for t in restored.texts)


@pytest.mark.plotnine
def test_plotnine_must_draw_inside_block():
    pd = pytest.importorskip("pandas")
    p9 = pytest.importorskip("plotnine")
    from ggtext import element_markdown

    df = pd.DataFrame({"x": [1, 2], "y": [1, 2]})
    plot = (
        p9.ggplot(df, p9.aes("x", "y"))
        + p9.geom_point()
        + p9.labs(title="**bold**")
        + p9.theme(plot_title=element_markdown())
    )
    ggtext.disable()

    # Built inside, drawn outside: the theme is applied too late.
    with ggtext.enabled():
        built = plot + p9.theme()
    with pytest.raises(AttributeError, match="richtext"):
        built.draw()

    # Drawn inside: works, and the figure can be saved afterwards.
    with ggtext.enabled():
        fig = plot.draw()
    fig.savefig(io.BytesIO())
    assert any(is_rich(t) for t in fig.texts)
