"""Step 7: turn metrics into 0-100 scores with rules from scoring_rules.yaml.

The rules are data, not code, so docs/scoring.md and the YAML stay in sync and
anyone can see exactly why a score is what it is.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel

from app.schemas.metrics import Category, LanguageMetrics, PacingMetrics, VoiceMetrics

RULES_PATH = Path(__file__).parent / "scoring_rules.yaml"
ALL_CATEGORIES: tuple[Category, ...] = (
    "voice",
    "pacing",
    "language",
    "pronunciation",
    "eye_contact",
    "posture",
    "body_language",
)


class Rule(BaseModel):
    id: str
    metric: str
    max_penalty: float
    full: float
    above: float | None = None
    below: float | None = None
    message: str

    def penalty(self, value: float) -> float:
        if self.above is not None:
            start, rising = self.above, True
        elif self.below is not None:
            start, rising = self.below, False
        else:  # pragma: no cover - rejected by load_rules
            return 0.0
        span = (self.full - start) if rising else (start - self.full)
        excess = (value - start) if rising else (start - value)
        if excess <= 0 or span <= 0:
            return 0.0
        return round(self.max_penalty * min(1.0, excess / span), 2)


class RuleResult(BaseModel):
    id: str
    metric: str
    value: float
    penalty: float
    max_penalty: float
    message: str


class CategoryScore(BaseModel):
    category: Category
    status: Literal["scored", "not_scored"]
    score: float | None
    reason: str | None = None  # why it was not scored
    rules: list[RuleResult] = []


class Scores(BaseModel):
    overall: float | None
    categories: dict[str, CategoryScore]


class RuleSet(BaseModel):
    weights: dict[str, float]
    categories: dict[str, list[Rule]]


@lru_cache
def load_rules(path: Path = RULES_PATH) -> RuleSet:
    data: dict[str, Any] = yaml.safe_load(path.read_text())
    rules = RuleSet.model_validate(data)
    for cat_rules in rules.categories.values():
        for r in cat_rules:
            if (r.above is None) == (r.below is None):
                raise ValueError(f"rule {r.id} needs exactly one of 'above' or 'below'")
    return rules


def derived_metrics(
    pacing: PacingMetrics | None,
    voice: VoiceMetrics | None,
    language: LanguageMetrics | None,
) -> dict[str, float | None]:
    """Flat metric values the rules refer to by name."""
    m: dict[str, float | None] = {}
    if pacing is not None:
        minutes = max(pacing.speaking_time_s / 60, 1e-6)
        m.update(
            wpm_overall=pacing.wpm_overall,
            fast_ratio=pacing.fast_ratio,
            wpm_variability=pacing.wpm_variability if len(pacing.wpm_series) >= 3 else None,
            awkward_pauses_per_min=pacing.awkward_pause_count / minutes,
            hesitations_per_min=sum(p.kind == "hesitation" for p in pacing.pauses) / minutes,
            # Under 30 s there are too few sentences to judge pausing habits.
            effective_pauses_per_min=(
                pacing.effective_pause_count / minutes if pacing.speaking_time_s >= 30 else None
            ),
            target_time_error=(
                abs(pacing.duration_delta_s) / pacing.target_seconds
                if pacing.target_seconds and pacing.duration_delta_s is not None
                else None
            ),
        )
    if voice is not None:
        m.update(
            pitch_std_semitones=voice.pitch_std_semitones,
            pitch_range_semitones=voice.pitch_range_semitones,
            quiet_ratio=voice.quiet_ratio,
            intensity_std_db=voice.intensity_std_db,
            energy_trend_db_per_min=voice.energy_trend_db_per_min,
        )
    if language is not None and pacing is not None:
        minutes = max(pacing.speaking_time_s / 60, 1e-6)
        m.update(
            fillers_per_min=language.fillers_per_min,
            hedges_per_min=len(language.hedges) / minutes,
            repetitions_per_min=len(language.repetitions) / minutes,
            # MATTR is unreliable on very short talks.
            vocabulary_mattr=language.vocabulary_mattr if language.word_count >= 100 else None,
            long_sentence_share=(
                len(language.long_sentences) / language.sentence_count
                if language.sentence_count >= 3
                else None
            ),
            script_coverage=language.script.coverage if language.script else None,
        )
    return m


def score_category(
    category: Category, rules: list[Rule], metrics: dict[str, float | None]
) -> CategoryScore:
    results: list[RuleResult] = []
    for rule in rules:
        value = metrics.get(rule.metric)
        if value is None:
            continue
        results.append(
            RuleResult(
                id=rule.id,
                metric=rule.metric,
                value=round(value, 3),
                penalty=rule.penalty(value),
                max_penalty=rule.max_penalty,
                message=rule.message.format(value=value),
            )
        )
    total = sum(r.penalty for r in results)
    return CategoryScore(
        category=category, status="scored", score=round(max(0.0, 100.0 - total), 1), rules=results
    )


def score(
    *,
    pacing: PacingMetrics | None,
    voice: VoiceMetrics | None,
    language: LanguageMetrics | None,
    not_scored: dict[str, str] | None = None,
    rules: RuleSet | None = None,
) -> Scores:
    """Score every category. Categories without data are marked not_scored with a reason."""
    rules = rules or load_rules()
    metrics = derived_metrics(pacing, voice, language)
    available = {"pacing": pacing, "voice": voice, "language": language}
    reasons = dict(not_scored or {})

    out: dict[str, CategoryScore] = {}
    for cat in ALL_CATEGORIES:
        if cat in available and available[cat] is not None and cat not in reasons:
            out[cat] = score_category(cat, rules.categories.get(cat, []), metrics)
        else:
            out[cat] = CategoryScore(
                category=cat,
                status="not_scored",
                score=None,
                reason=reasons.get(cat, "Coming in a later version."),
            )

    scored = [(c.score, rules.weights.get(k, 1.0)) for k, c in out.items() if c.score is not None]
    weight = sum(w for _, w in scored)
    overall = round(sum(s * w for s, w in scored) / weight, 1) if weight else None
    return Scores(overall=overall, categories=out)
