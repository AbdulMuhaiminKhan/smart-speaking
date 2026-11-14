"""Render the report as a PDF with WeasyPrint. Everything happens locally."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.pipeline.report import Report
from app.schemas.metrics import TimePoint
from app.services import charts
from app.services import pdf_text as tx

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
ORDER = list(tx.CATEGORIES)
MAX_ISSUES = 120


_RTL = re.compile("[\u0590-\u08ff\ufb1d-\ufdff\ufe70-\ufeff]")


def textdir(value: Any) -> str:
    """'rtl' for text in Arabic script (Urdu), else 'ltr'. WeasyPrint has no dir="auto"."""
    text = " ".join(value) if isinstance(value, list) else str(value or "")
    letters = re.findall(r"[^\W\d_]", text)
    rtl = sum(1 for c in letters if _RTL.match(c))
    return "rtl" if letters and rtl * 2 >= len(letters) else "ltr"


@lru_cache
def _env() -> Environment:
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html"]))
    env.filters["textdir"] = textdir
    return env


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
    voice_emotion: dict[str, Any] | None = None,
    lang: str = "en",
    mode: str | None = None,
    target_seconds: int | None = None,
    prompts: list[dict[str, Any]] | None = None,
    notes: list[dict[str, Any]] | None = None,
    language_result: dict[str, Any] | None = None,
    summary: dict[str, Any] | None = None,
) -> str:
    lang = lang if lang in tx.LANGS else "en"
    t = tx.strings(lang)

    def cat(c: str) -> str:
        return tx.table(lang, tx.CATEGORIES, c)

    cats = report.scores.categories
    sections = []
    for s in sorted(report.sections, key=lambda x: ORDER.index(x.category)):
        note = None
        if s.category == "pronunciation" and s.status == "scored":
            note = t["pron_note"]
        elif s.category in {"eye_contact", "posture", "body_language"} and s.status == "scored":
            note = t["camera_note"]
        sections.append(
            {
                "label": cat(s.category),
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
        (t["pace"], _series(pacing, "wpm_series"), {"band": (110, 170), "y_min": 0}, t["pace_cap"]),
        (t["pitch"], _series(voice, "pitch_series"), {}, t["pitch_cap"]),
        (
            t["variation"],
            _series(voice, "pitch_variation_series"),
            {"band": (2.5, 8), "y_min": 0, "fmt": "{:.1f}"},
            t["variation_cap"],
        ),
        (t["volume"], _series(voice, "volume_series"), {}, t["volume_cap"]),
        (
            t["eye"],
            _series(body, "eye_contact_series", 100.0),
            {"band": (75, 100), "y_min": 0, "y_max": 100, "fmt": "{:.0f}%"},
            t["eye_cap"],
        ),
    ):
        svg = charts.line_chart(pts, **kwargs)  # type: ignore[arg-type]
        if svg:
            chart_list.append({"title": title_, "svg": svg, "caption": caption})

    coach_note = (
        tx.text(lang, "coach_llm", model=report.llm_model)
        if report.generated_by == "llm"
        else t["coach_template"]
    )

    def mix(values: dict[str, float] | None) -> list[dict[str, Any]]:
        items = sorted((values or {}).items(), key=lambda kv: -kv[1])
        return [
            {"label": tx.table(lang, tx.EMOTIONS, k), "pct": round(v * 100)}
            for k, v in items
            if v >= 0.02
        ][:5]

    metrics: list[dict[str, str]] = []
    if summary:
        if summary.get("wpm") is not None:
            metrics.append({"label": t["m_wpm"], "value": f"{summary['wpm']:.0f} wpm"})
        if summary.get("fillers_per_min") is not None:
            metrics.append({"label": t["m_fillers"], "value": f"{summary['fillers_per_min']:.1f}"})
        if summary.get("clarity_pct") is not None:
            metrics.append({"label": t["m_clarity"], "value": f"{summary['clarity_pct']:.0f}%"})
        if summary.get("pitch_variation_st") is not None:
            mono = f" ({t['monotone']})" if summary.get("monotone") else ""
            metrics.append(
                {
                    "label": t["m_pitch_var"],
                    "value": f"{summary['pitch_variation_st']:.1f} st{mono}",
                }
            )
        if summary.get("eye_contact_pct") is not None:
            metrics.append({"label": t["m_eye"], "value": f"{summary['eye_contact_pct']:.0f}%"})
        if summary.get("gestures_per_min") is not None:
            metrics.append(
                {"label": t["m_gestures"], "value": f"{summary['gestures_per_min']:.1f}"}
            )
    if pacing:
        metrics.append(
            {
                "label": t["m_pauses"],
                "value": f"{pacing.get('pause_count', 0)} ({pacing.get('awkward_pause_count', 0)})",
            }
        )

    script = None
    sc = (language_result or {}).get("script")
    if sc:
        script = {
            "summary": tx.text(
                lang,
                "script_sum",
                coverage=round(sc["coverage"] * 100),
                extra=round(sc["extra_ratio"] * 100),
            ),
            "gaps": [
                {"time": _mmss(p["start"]), "script": p["script"], "spoken": p["spoken"]}
                for p in sc.get("parts", [])
                if p["kind"] != "said" and len((p["script"] + " " + p["spoken"]).split()) >= 3
            ][:40],
        }

    scored = [(cat(c), cats[c].score) for c in ORDER if c in cats and cats[c].score is not None]
    return (
        _env()
        .get_template("report.html")
        .render(
            t=t,
            lang=lang,
            dir="rtl" if lang == "ur" else "ltr",
            title=title,
            created=created,
            duration=_mmss(duration_s or 0),
            mode_label=tx.table(lang, tx.MODES, mode) if mode and mode != "free_talk" else None,
            target=tx.text(lang, "target", time=_mmss(target_seconds)) if target_seconds else None,
            radar=charts.radar(scored) if len(scored) >= 3 else "",
            overall="–" if report.overall is None else round(report.overall),
            overall_class=_cls(report.overall),
            summary=report.summary,
            coach_note=coach_note,
            strengths=report.strengths,
            gaps=report.gaps,
            fixes=report.top_fixes,
            fixes_title=tx.text(lang, "fixes", n=len(report.top_fixes)),
            sections=sections,
            clarity=report.clarity,
            charts=chart_list,
            metrics=metrics,
            prompts=[{"time": _mmss(p["t"]), "text": p["text"]} for p in prompts or []],
            notes=[{"time": _mmss(n["t"]), "text": n["text"]} for n in notes or []],
            script=script,
            emotions={
                "face": mix((body or {}).get("emotions")),
                "voice": mix((voice_emotion or {}).get("emotions")),
            },
            issues=[
                {
                    "time": _mmss(i.start),
                    "message": tx.issue(lang, i.kind, i.message, i.value, i.text),
                    "category": cat(i.category),
                }
                for i in report.issues[:MAX_ISSUES]
            ],
            transcript=transcript_text,
        )
    )


def render_pdf(html: str) -> bytes:
    from weasyprint import HTML

    pdf: bytes = HTML(string=html, base_url=str(TEMPLATES)).write_pdf()
    return pdf
