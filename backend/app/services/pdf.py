"""Render the report as a PDF with WeasyPrint. Everything happens locally."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.pipeline.report import Report
from app.schemas.metrics import TimePoint
from app.services import charts

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
LABELS = {
    "voice": "Voice",
    "pacing": "Pacing",
    "language": "Language",
    "pronunciation": "Pronunciation",
    "eye_contact": "Eye contact",
    "posture": "Posture",
    "body_language": "Body language",
}
ORDER = list(LABELS)
MAX_ISSUES = 120


@lru_cache
def _env() -> Environment:
    return Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html"]))


def _cls(score: float | None) -> str:
    if score is None:
        return "muted"
    return "good" if score >= 80 else "ok" if score >= 60 else "bad"


def _mmss(t: float) -> str:
    s = max(0, int(t))
    return f"{s // 60}:{s % 60:02d}"


def _series(data: dict[str, Any] | None, key: str, scale: float = 1.0) -> list[TimePoint]:
    if not data:
        return []
    return [
        TimePoint(t=p["t"], value=None if p["value"] is None else p["value"] * scale)
        for p in data.get(key, [])
    ]


def render_html(
    report: Report,
    *,
    title: str,
    created: str,
    duration_s: float | None,
    transcript_text: str,
    pacing: dict[str, Any] | None = None,
    voice: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
) -> str:
    cats = report.scores.categories
    sections = []
    for s in sorted(report.sections, key=lambda x: ORDER.index(x.category)):
        note = None
        if s.category == "pronunciation" and s.status == "scored":
            note = "Estimate: compared with a standard US English reference, so accents can be flagged."
        elif s.category in {"eye_contact", "posture", "body_language"} and s.status == "scored":
            note = "Estimated from camera tracking."
        sections.append(
            {
                "label": LABELS[s.category],
                "score": None if s.score is None else round(s.score),
                "cls": _cls(s.score),
                "note": note,
                "what_happened": s.what_happened,
                "why_it_matters": s.why_it_matters,
                "how_to_fix": s.how_to_fix,
                "drill": s.drill,
            }
        )

    chart_list = []
    for title_, pts, kwargs, caption in (
        (
            "Pace",
            _series(pacing, "wpm_series"),
            {"band": (110, 170), "y_min": 0},
            "Words per minute. Green band: comfortable pace.",
        ),
        (
            "Pitch",
            _series(voice, "pitch_series"),
            {},
            "Pitch in Hz. More movement sounds more expressive.",
        ),
        ("Volume", _series(voice, "volume_series"), {}, "Loudness in dB."),
        (
            "Eye contact",
            _series(body, "eye_contact_series", 100.0),
            {"band": (75, 100), "y_min": 0, "y_max": 100, "fmt": "{:.0f}%"},
            "Percent of time looking at the camera (estimate).",
        ),
    ):
        svg = charts.line_chart(pts, **kwargs)  # type: ignore[arg-type]
        if svg:
            chart_list.append({"title": title_, "svg": svg, "caption": caption})

    if report.generated_by == "llm":
        coach_note = (
            f"Coaching written by a local AI ({report.llm_model}) from your measured metrics only."
        )
    else:
        coach_note = "Coaching from built-in templates."

    return (
        _env()
        .get_template("report.html")
        .render(
            title=title,
            created=created,
            duration=_mmss(duration_s or 0),
            radar=charts.radar(scored)
            if len(
                scored := [
                    (LABELS[c], cats[c].score)
                    for c in ORDER
                    if c in cats and cats[c].score is not None
                ]
            )
            >= 3
            else "",
            overall="–" if report.overall is None else round(report.overall),
            overall_class=_cls(report.overall),
            summary=report.summary,
            coach_note=coach_note,
            strengths=report.strengths,
            gaps=report.gaps,
            fixes=report.top_fixes,
            sections=sections,
            clarity=report.clarity,
            charts=chart_list,
            issues=[
                {"time": _mmss(i.start), "message": i.message, "category": LABELS[i.category]}
                for i in report.issues[:MAX_ISSUES]
            ],
            transcript=transcript_text,
        )
    )


def render_pdf(html: str) -> bytes:
    from weasyprint import HTML

    pdf: bytes = HTML(string=html, base_url=str(TEMPLATES)).write_pdf()
    return pdf
