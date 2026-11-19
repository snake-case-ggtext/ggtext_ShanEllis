"""
Line layout for rich text.

This module is independent of matplotlib's rendering machinery: it takes
the tokens produced by :mod:`ggtext._parse` and a *measurer* object that
reports the size of text and images, and computes where every fragment
goes. That makes the layout algorithm easy to unit-test with a fake
measurer (see ``tests/test_layout.py``).

Coordinate system
-----------------
All values are in display units (pixels). The origin is the top-left
corner of the (padded) box, x grows to the right and y grows *upwards*,
so baselines have negative y values. This matches the convention used by
:meth:`matplotlib.text.Text._get_layout`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Protocol, Sequence, Tuple, Union

from ._parse import LINE_BREAK, ImageRun, TextRun, Token
from ._style import Style

__all__ = ["Measurer", "Fragment", "Line", "Layout", "layout_tokens"]

# Break only at ordinary whitespace: \s would also match the non-breaking
# space (&nbsp;, U+00A0), which must keep words together.
_WS_RE = re.compile(r"([ \t\n\r\f\v]+)")


class Measurer(Protocol):
    """What the layout algorithm needs to know about the renderer."""

    def text(self, s: str, style: Style, math: bool) -> Tuple[float, float, float]:
        """Return ``(width, ascent, descent)`` of *s* in pixels."""
        ...

    def font_metrics(self, style: Style) -> Tuple[float, float, float]:
        """
        Return ``(ascent, descent, line_gap)`` of the font of *style*.

        These are the font's own vertical metrics (not those of any
        particular glyphs), used for the minimum height of a line and for
        the space between lines, exactly as matplotlib does for plain text.
        """
        ...

    def image(self, run: ImageRun) -> Tuple[float, float]:
        """Return the ``(width, height)`` of an image in pixels."""
        ...

    def points_to_pixels(self, points: float) -> float:
        """Convert points to pixels."""
        ...


@dataclass
class Fragment:
    """A positioned piece of a line: some text or an image."""

    run: Union[TextRun, ImageRun]
    width: float
    ascent: float  # above the baseline, including any shift
    descent: float  # below the baseline, including any shift
    shift: float = 0.0  # baseline shift in pixels (positive is up)
    x: float = 0.0  # left edge, relative to the line start

    @property
    def is_space(self) -> bool:
        return (
            isinstance(self.run, TextRun)
            and not self.run.math
            and (self.run.text.strip() == "")
        )


@dataclass
class Line:
    """A laid out line of fragments."""

    fragments: List[Fragment] = field(default_factory=list)
    width: float = 0.0
    ascent: float = 0.0
    descent: float = 0.0
    x: float = 0.0  # left edge of the line within the box
    baseline: float = 0.0  # y of the baseline within the box (negative)

    @property
    def text(self) -> str:
        parts = []
        for f in self.fragments:
            if isinstance(f.run, TextRun):
                parts.append(f.run.text)
            else:
                parts.append(f.run.alt)
        return "".join(parts)


@dataclass
class Layout:
    """The result of laying out rich text."""

    lines: List[Line]
    width: float  # outer width: box + margins
    height: float  # outer height: box + margins
    content_width: float
    padding: Tuple[float, float, float, float]  # t, r, b, l in pixels
    margin: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)

    @property
    def box(self) -> Tuple[float, float, float, float]:
        """``(x, y, width, height)`` of the box (margins excluded); y is its bottom."""
        mt, mr, mb, ml = self.margin
        return (ml, -self.height + mb, self.width - ml - mr, self.height - mt - mb)

    @property
    def descent(self) -> float:
        """Distance from the last baseline to the bottom of the box."""
        if not self.lines:
            return 0.0
        return self.lines[-1].baseline + self.height


def _numeric(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _split_logical_lines(tokens: Sequence[Token]) -> List[List[Token]]:
    lines: List[List[Token]] = [[]]
    for tok in tokens:
        if tok is LINE_BREAK:
            lines.append([])
        else:
            lines[-1].append(tok)
    return lines


def _measure(tok: Union[TextRun, ImageRun], m: Measurer) -> Fragment:
    if isinstance(tok, ImageRun):
        w, h = m.image(tok)
        shift = m.points_to_pixels(tok.style.shift)
        return Fragment(tok, w, h + shift, -shift, shift)
    w, a, d = m.text(tok.text, tok.style, tok.math)
    shift = m.points_to_pixels(tok.style.shift)
    return Fragment(tok, w, a + shift, d - shift, shift)


def _pieces(tokens: Sequence[Token], wrap: bool) -> List[Union[TextRun, ImageRun]]:
    """
    Break tokens into the units that layout works with.

    Without wrapping, runs are kept whole (fewer draw calls and correct
    kerning). With wrapping, text runs are split into words and runs of
    whitespace so that lines can be broken at the spaces.
    """
    out: List[Union[TextRun, ImageRun]] = []
    for tok in tokens:
        if isinstance(tok, TextRun) and wrap and not tok.math:
            for part in _WS_RE.split(tok.text):
                if part:
                    out.append(TextRun(part, tok.style))
        else:
            out.append(tok)  # type: ignore[arg-type]
    return out


def _wrap(frags: List[Fragment], width: float | None) -> List[List[Fragment]]:
    """Greedy line breaking at whitespace fragments."""
    if width is None:
        return [frags]

    lines: List[List[Fragment]] = [[]]
    current = 0.0
    for f in frags:
        line = lines[-1]
        if f.is_space:
            if line:  # never start a wrapped line with a space
                line.append(f)
                current += f.width
            continue
        # width of the line if we add this word (excluding trailing spaces)
        if line and current + f.width > width + 1e-6:
            # strip trailing spaces and start a new line
            while line and line[-1].is_space:
                line.pop()
            lines.append([f])
            current = f.width
        else:
            line.append(f)
            current += f.width
    for line in lines:
        while line and line[-1].is_space:
            line.pop()
    return lines


def _merge(frags: List[Fragment], m: Measurer) -> List[Fragment]:
    """Merge adjacent text fragments that share a style (after wrapping)."""
    merged: List[Fragment] = []
    for f in frags:
        prev = merged[-1] if merged else None
        if (
            prev is not None
            and isinstance(prev.run, TextRun)
            and isinstance(f.run, TextRun)
            and not prev.run.math
            and not f.run.math
            and prev.run.style == f.run.style
        ):
            merged[-1] = _measure(TextRun(prev.run.text + f.run.text, f.run.style), m)
        else:
            merged.append(f)
    return merged


def layout_tokens(
    tokens: Sequence[Token],
    measurer: Measurer,
    base: Style,
    *,
    halign: str = "left",
    wrap_width: float | None = None,
    box_width: float | None = None,
    box_height: float | None = None,
    valign: str = "top",
    padding: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0),
    margin: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0),
    linespacing: Union[float, str, None] = None,
    line_model: str = "mpl311",
) -> Layout:
    """
    Lay out *tokens*.

    Parameters
    ----------
    tokens :
        Output of :func:`ggtext._parse.parse`.
    measurer :
        Reports sizes of text and images.
    base :
        Style of unstyled text; used for the height of empty lines.
    halign :
        Alignment of lines within the box: ``"left"``, ``"center"``
        or ``"right"``.
    wrap_width :
        Maximum width of a line of text in pixels (excluding padding).
        ``None`` disables wrapping.
    box_width :
        Fixed width of the box in pixels (including padding). If None,
        the box shrinks to fit the content.
    box_height :
        Height of the box in pixels (including padding). Text that does
        not fit overflows the box, as in ggtext. None fits the content.
    valign :
        Vertical alignment of the content in a box of *box_height*:
        ``"top"``, ``"center"`` or ``"bottom"``.
    padding :
        ``(top, right, bottom, left)`` padding in pixels.
    margin :
        ``(top, right, bottom, left)`` margin outside the box, in pixels.
    linespacing :
        matplotlib's ``linespacing``: a number, ``"normal"`` or None
        (same as ``"normal"``).
    line_model :
        How line heights are computed, mirroring matplotlib so that rich
        text is spaced exactly like plain text:

        ``"mpl311"`` (matplotlib >= 3.11)
            With ``"normal"`` spacing, a line is at least as tall as the
            font's ascent + descent, plus the font's line gap when there
            is more than one line. With a numeric spacing every line is
            ``linespacing * (ascent + descent)`` tall.
        ``"mpl310"`` (matplotlib < 3.11)
            A line is at least as tall as the font's "lp" box and the
            ascent of every line after the first is multiplied by
            ``linespacing``.

        For lines that mix font sizes the metrics of the largest font in
        the line are used.
    """
    pt, pr, pb, pl = padding
    wrap = wrap_width is not None

    # 1. Horizontal layout: break into lines and place fragments
    rows: List[List[Fragment]] = []
    for logical in _split_logical_lines(tokens):
        frags = [_measure(p, measurer) for p in _pieces(logical, wrap)]
        for row in _wrap(frags, wrap_width):
            rows.append(_merge(row, measurer) if wrap else row)

    # 2. Vertical metrics of every line
    multiline = len(rows) > 1
    numeric_ls = _numeric(linespacing)
    lines: List[Line] = []
    for row in rows:
        line = Line(row)
        x = 0.0
        a_c = d_c = 0.0  # content ascent / descent
        font = base  # the largest unshifted font in the line
        for f in row:
            f.x = x
            x += f.width
            a_c = max(a_c, f.ascent)
            d_c = max(d_c, f.descent)
            if (
                isinstance(f.run, TextRun)
                and f.shift == 0
                and (f.run.style.size or 0) > (font.size or 0)
            ):
                font = f.run.style
        fa, fd, gap = measurer.font_metrics(font)
        if line_model == "mpl310":
            # matplotlib < 3.11: h = max(h, lp_h), d = max(d, lp_d)
            h = max(a_c + d_c, fa + fd)
            d = max(d_c, fd)
            a = h - d
        elif numeric_ls is None:
            g = gap / 2 if multiline else 0.0
            a = max(a_c, fa) + g
            d = max(d_c, fd) + g
        else:
            leading = numeric_ls * (fa + fd) - (a_c + d_c)
            a = a_c + leading / 2
            d = d_c + leading / 2
        line.width = x
        line.ascent = a
        line.descent = d
        lines.append(line)

    # vertical positions (y grows upwards, origin at the top)
    y = 0.0
    scale = numeric_ls if (line_model == "mpl310" and numeric_ls is not None) else None
    for i, line in enumerate(lines):
        a = line.ascent
        if i and scale is not None:
            a *= scale
        y -= a
        line.baseline = y
        y -= line.descent
    content_height = -y

    content_width = max((ln.width for ln in lines), default=0.0)
    if box_width is not None:
        inner = max(box_width - pl - pr, 0.0)
    else:
        inner = content_width

    for line in lines:
        if halign == "center":
            line.x = pl + (inner - line.width) / 2
        elif halign == "right":
            line.x = pl + inner - line.width
        else:
            line.x = pl

    height = content_height + pt + pb
    yoffset = pt
    if box_height is not None:
        extra = box_height - height  # negative: the text overflows
        if valign == "center":
            yoffset += extra / 2
        elif valign == "bottom":
            yoffset += extra
        height = box_height
    width = inner + pl + pr

    # margins sit outside the box
    mt, mr, mb, ml = margin
    for line in lines:
        line.baseline -= yoffset + mt
        line.x += ml
    return Layout(
        lines, width + ml + mr, height + mt + mb, content_width, padding, margin
    )
