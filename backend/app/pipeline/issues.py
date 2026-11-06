"""Build the mistakes timeline: every issue with a start and end time."""

from __future__ import annotations

import math

from app.pipeline import pacing as pacing_mod
from app.schemas.metrics import Issue, LanguageMetrics, PacingMetrics, TimePoint, VoiceMetrics

MONOTONE_WINDOW_S = 10
MONOTONE_STRETCH_ST = 1.2  # pitch spread inside a 10 s window that sounds flat
QUIET_MIN_SECONDS = 3


def _merge_windows(
    points: list[TimePoint], test: float, above: bool, half_window: float
) -> list[tuple[float, float, float]]:
    """Merge consecutive series points past a threshold into (start, end, peak) runs."""
    runs: list[tuple[float, float, float]] = []
    current: list[TimePoint] = []
    for p in [*points, TimePoint(t=float("inf"), value=None)]:
        hit = p.value is not None and (p.value > test if above else p.value < test)
        if hit:
            current.append(p)
            continue
        if current:
            vals = [c.value for c in current if c.value is not None]
            peak = max(vals) if above else min(vals)
            runs.append((current[0].t - half_window, current[-1].t + half_window, peak))
            current = []
    return runs


def pacing_issues(p: PacingMetrics) -> list[Issue]:
    out: list[Issue] = []
    for i, pause in enumerate(x for x in p.pauses if x.kind != "effective"):
        out.append(
            Issue(
                id=f"pause-{i}",
                category="pacing",
                kind="awkward_pause" if pause.kind == "awkward" else "hesitation",
                start=pause.start,
                end=pause.end,
                severity="major" if pause.kind == "awkward" else "minor",
                message=(
                    f"{pause.duration:.1f} s silence"
                    if pause.kind == "awkward"
                    else f"{pause.duration:.1f} s hesitation mid-sentence"
                ),
            )
        )
    half = pacing_mod.WINDOW_S / 2
    for i, (s, e, peak) in enumerate(_merge_windows(p.wpm_series, pacing_mod.FAST_WPM, True, half)):
        out.append(
            Issue(
                id=f"fast-{i}",
                category="pacing",
                kind="too_fast",
                start=max(0.0, s),
                end=e,
                severity="major" if peak > 190 else "minor",
                message=f"Speaking fast, up to {peak:.0f} words per minute",
            )
        )
    for i, (s, e, low) in enumerate(_merge_windows(p.wpm_series, pacing_mod.SLOW_WPM, False, half)):
        out.append(
            Issue(
                id=f"slow-{i}",
                category="pacing",
                kind="too_slow",
                start=max(0.0, s),
                end=e,
                severity="minor",
                message=f"Speaking slowly, down to {low:.0f} words per minute",
            )
        )
    return out


def voice_issues(v: VoiceMetrics) -> list[Issue]:
    out: list[Issue] = []
    # Flat pitch stretches: 10 s windows with very little movement.
    for k in range(0, len(v.pitch_series), MONOTONE_WINDOW_S):
        window = [p.value for p in v.pitch_series[k : k + MONOTONE_WINDOW_S] if p.value]
        if len(window) < MONOTONE_WINDOW_S * 0.6:
            continue
        ref = sorted(window)[len(window) // 2]
        st = [12 * math.log2(x / ref) for x in window]
        mean = sum(st) / len(st)
        spread = (sum((x - mean) ** 2 for x in st) / len(st)) ** 0.5
        if spread < MONOTONE_STRETCH_ST:
            start = v.pitch_series[k].t - 0.5
            out.append(
                Issue(
                    id=f"flat-{len(out)}",
                    category="voice",
                    kind="monotone",
                    start=start,
                    end=start + MONOTONE_WINDOW_S,
                    severity="minor",
                    message="Flat, monotone stretch",
                )
            )

    secs = [p for p in v.volume_series if p.value is not None]
    if secs:
        med = sorted(p.value for p in secs if p.value is not None)[len(secs) // 2]
        run: list[TimePoint] = []
        for p in [*v.volume_series, TimePoint(t=float("inf"), value=None)]:
            if p.value is not None and p.value < med - 10:
                run.append(p)
                continue
            if len(run) >= QUIET_MIN_SECONDS:
                out.append(
                    Issue(
                        id=f"quiet-{len(out)}",
                        category="voice",
                        kind="too_quiet",
                        start=run[0].t - 0.5,
                        end=run[-1].t + 0.5,
                        severity="minor",
                        message="Much quieter than the rest of your talk",
                    )
                )
            run = []
    return out


def language_issues(lang: LanguageMetrics) -> list[Issue]:
    out: list[Issue] = []
    for i, o in enumerate(lang.fillers):
        out.append(
            Issue(
                id=f"filler-{i}",
                category="language",
                kind="filler",
                start=o.start,
                end=o.end,
                severity="minor",
                message=f'Filler word "{o.phrase}"',
                text=o.phrase,
            )
        )
    for i, o in enumerate(lang.hedges):
        out.append(
            Issue(
                id=f"hedge-{i}",
                category="language",
                kind="hedge",
                start=o.start,
                end=o.end,
                severity="minor",
                message=f'Hedging phrase "{o.phrase}"',
                text=o.phrase,
            )
        )
    for i, o in enumerate(lang.repetitions):
        out.append(
            Issue(
                id=f"repeat-{i}",
                category="language",
                kind="repetition",
                start=o.start,
                end=o.end,
                severity="minor",
                message=f'Repeated "{o.phrase}"',
                text=o.phrase,
            )
        )
    for i, o in enumerate(lang.long_sentences):
        out.append(
            Issue(
                id=f"long-{i}",
                category="language",
                kind="long_sentence",
                start=o.start,
                end=o.end,
                severity="info",
                message="Very long sentence (over 30 words)",
                text=o.phrase,
            )
        )
    return out


def build(
    pacing: PacingMetrics | None, voice: VoiceMetrics | None, language: LanguageMetrics | None
) -> list[Issue]:
    issues: list[Issue] = []
    if pacing:
        issues += pacing_issues(pacing)
    if voice:
        issues += voice_issues(voice)
    if language:
        issues += language_issues(language)
    return sorted(issues, key=lambda i: (i.start, i.id))
