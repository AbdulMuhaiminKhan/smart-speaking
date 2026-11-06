"""SVG charts for the PDF report (the web app draws its own with React)."""

from __future__ import annotations

import math
from html import escape

from app.schemas.metrics import TimePoint

INK = "#334155"
MUTED = "#94a3b8"
GRID = "#e2e8f0"
ACCENT = "#2756e0"
BAND = "#d1fae5"


def _mmss(t: float) -> str:
    s = max(0, int(t))
    return f"{s // 60}:{s % 60:02d}"


def line_chart(
    points: list[TimePoint],
    *,
    band: tuple[float, float] | None = None,
    y_min: float | None = None,
    y_max: float | None = None,
    fmt: str = "{:.0f}",
    width: int = 640,
    height: int = 150,
) -> str | None:
    vals = [p.value for p in points if p.value is not None]
    if len(vals) < 2:
        return None
    pl, pr, pt, pb = 40, 10, 10, 22
    t0, t1 = points[0].t, points[-1].t
    lo = y_min if y_min is not None else min(vals + ([band[0]] if band else []))
    hi = y_max if y_max is not None else max(vals + ([band[1]] if band else []))
    span = (hi - lo) or 1.0

    def x(t: float) -> float:
        return pl + (t - t0) / ((t1 - t0) or 1) * (width - pl - pr)

    def y(v: float) -> float:
        return pt + (1 - (v - lo) / span) * (height - pt - pb)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%">'
    ]
    if band:
        top, bottom = y(min(band[1], hi)), y(max(band[0], lo))
        parts.append(
            f'<rect x="{pl}" y="{top:.1f}" width="{width - pl - pr}" height="{max(0, bottom - top):.1f}" fill="{BAND}"/>'
        )
    for v in (lo, lo + span / 2, hi):
        parts.append(
            f'<line x1="{pl}" x2="{width - pr}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{GRID}"/>'
        )
        parts.append(
            f'<text x="{pl - 6}" y="{y(v) + 4:.1f}" font-size="10" fill="{MUTED}" text-anchor="end">{escape(fmt.format(v))}</text>'
        )
    d = ""
    for p in points:
        if p.value is None:
            d += " "
            continue
        cmd = "M" if not d or d.endswith(" ") else "L"
        d += f"{cmd}{x(p.t):.1f} {y(p.value):.1f}"
    paths = [s for s in d.replace(" M", "|M").split("|") if s.strip()]
    for path in paths:
        parts.append(f'<path d="{path.strip()}" fill="none" stroke="{ACCENT}" stroke-width="2"/>')
    parts.append(
        f'<text x="{pl}" y="{height - 6}" font-size="10" fill="{MUTED}">{_mmss(t0)}</text>'
    )
    parts.append(
        f'<text x="{width - pr}" y="{height - 6}" font-size="10" fill="{MUTED}" text-anchor="end">{_mmss(t1)}</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def radar(items: list[tuple[str, float | None]], size: int = 280) -> str:
    c, r = size / 2, size / 2 - 50
    n = len(items)

    def pt(i: int, rad: float) -> tuple[float, float]:
        a = -math.pi / 2 + i / n * 2 * math.pi
        return c + math.cos(a) * rad, c + math.sin(a) * rad

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}">']
    for ring in (0.25, 0.5, 0.75, 1.0):
        poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i, r * ring) for i in range(n)))
        parts.append(f'<polygon points="{poly}" fill="none" stroke="{GRID}"/>')
    for i in range(n):
        x, y = pt(i, r)
        parts.append(f'<line x1="{c}" y1="{c}" x2="{x:.1f}" y2="{y:.1f}" stroke="{GRID}"/>')
    shape = " ".join(
        f"{x:.1f},{y:.1f}" for x, y in (pt(i, r * (v or 0) / 100) for i, (_, v) in enumerate(items))
    )
    parts.append(
        f'<polygon points="{shape}" fill="{ACCENT}" fill-opacity="0.2" stroke="{ACCENT}" stroke-width="2"/>'
    )
    for i, (label, v) in enumerate(items):
        x, y = pt(i, r + 26)
        score = "–" if v is None else f"{v:.0f}"
        parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-size="10" fill="{INK}" text-anchor="middle">{escape(label)}</text>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{y + 12:.1f}" font-size="10" font-weight="bold" fill="{INK}" text-anchor="middle">{score}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)
