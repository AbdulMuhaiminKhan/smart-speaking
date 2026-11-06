"""Step 8: coaching text written by a local LLM (Ollama), checked against the metrics.

The LLM never sees the video or audio. It gets a list of numbered facts built
from the scored metrics, plus the transcript for sentence-clarity feedback.
Every statement it returns must cite the facts it is based on, and any number
it writes must appear in those facts. Anything that fails the check is
replaced by the template text, so the report never contains invented issues.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any

from pydantic import BaseModel, ValidationError

from app.pipeline.report import ADVICE, CATEGORY_WHY, Clarity, ClarityExample, Fix, Report
from app.pipeline.scoring import RuleResult

log = logging.getLogger(__name__)

TIMEOUT_S = 240
MAX_TRANSCRIPT_WORDS = 1500
_NUMBER = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(%?)")
CATEGORY_NAMES = {
    "voice": "Voice",
    "pacing": "Pacing",
    "language": "Language",
    "pronunciation": "Pronunciation",
    "eye_contact": "Eye contact",
    "posture": "Posture",
    "body_language": "Body language",
}

SYSTEM_PROMPT = """You are a warm, direct public speaking coach.
You write feedback for one practice recording, based ONLY on the numbered facts you are given.

Rules:
- Use only the facts. Never mention a problem, strength or number that is not in a fact.
- Every item you write must list the fact ids it is based on in "fact_ids".
- Strengths must cite facts of kind "good". Gaps and fixes must cite facts of kind "problem".
- In the summary, call a category strong only if its score fact says "a strength", and name
  the categories that "need work".
- Copy numbers exactly as they appear in the facts. Do not calculate new numbers.
- Speak to the speaker as "you". Short sentences, plain words, no jargon.
- Pronunciation and body-language facts are estimates; say "may" or "seems" for them.
- In a category's section, cite only facts of that category.
- Do not repeat the same advice in several places.
- For clarity, quote transcript sentences exactly in "original" and suggest a clearer version.
- Answer with JSON only, matching the schema."""


class _Item(BaseModel):
    text: str
    fact_ids: list[str]


class _Section(BaseModel):
    category: str
    what_happened: str
    why_it_matters: str
    how_to_fix: str
    drill: str
    fact_ids: list[str]


class _Fix(BaseModel):
    title: str
    how: str
    drill: str
    fact_ids: list[str]


class _ClarityExample(BaseModel):
    original: str
    suggestion: str


class _Clarity(BaseModel):
    feedback: str
    examples: list[_ClarityExample]


class LlmOutput(BaseModel):
    summary: str
    strengths: list[_Item]
    gaps: list[_Item]
    sections: list[_Section]
    top_fixes: list[_Fix]
    clarity: _Clarity


class Fact(BaseModel):
    id: str
    category: str
    kind: str  # problem | good | info
    text: str


def build_facts(report: Report) -> list[Fact]:
    facts: list[Fact] = []
    for cat, c in report.scores.categories.items():
        if c.status != "scored":
            continue
        facts.append(
            Fact(
                id=f"{cat}.score",
                category=cat,
                kind="info",
                text=f"{CATEGORY_NAMES[cat]} score: {c.score:.0f} out of 100 ({_level(c.score)}).",
            )
        )
        for r in c.rules:
            facts.append(_rule_fact(cat, r))
    if report.overall is not None:
        facts.append(
            Fact(
                id="overall.score",
                category="overall",
                kind="info",
                text=f"Overall score: {report.overall:.0f} out of 100.",
            )
        )
    for key, value in report.highlights.items():
        if value is not None:
            facts.append(
                Fact(
                    id=f"highlight.{key}",
                    category="overall",
                    kind="info",
                    text=f"{key.replace('_', ' ')}: {value}",
                )
            )
    counts: dict[str, int] = {}
    for issue in report.issues:
        counts[issue.kind] = counts.get(issue.kind, 0) + 1
    for kind, n in counts.items():
        facts.append(
            Fact(
                id=f"issues.{kind}",
                category="overall",
                kind="info",
                text=f"Timeline moments of type {kind.replace('_', ' ')}: {n}",
            )
        )
    return facts


METRIC_LABELS = {
    "wpm_overall": "words per minute",
    "fast_ratio": "share of the talk faster than 170 words per minute",
    "wpm_variability": "variation in pace",
    "awkward_pauses_per_min": "long silences per minute",
    "hesitations_per_min": "mid-sentence hesitations per minute",
    "effective_pauses_per_min": "pauses at sentence breaks per minute",
    "target_time_error": "distance from the target length",
    "pitch_std_semitones": "pitch variety in semitones",
    "pitch_range_semitones": "pitch range in semitones",
    "quiet_ratio": "share of time much quieter than usual",
    "intensity_std_db": "second-to-second volume spread in dB",
    "energy_trend_db_per_min": "volume change per minute in dB",
    "fillers_per_min": "filler words per minute",
    "hedges_per_min": "hedging phrases per minute",
    "repetitions_per_min": "repeated words per minute",
    "vocabulary_mattr": "vocabulary variety (0 to 1)",
    "long_sentence_share": "share of sentences over 30 words",
    "script_coverage": "share of the script covered",
    "unclear_per_100_words": "possibly unclear words per 100 words (estimate)",
    "phoneme_similarity": "average match with expected pronunciation (estimate)",
    "low_confidence_ratio": "share of words the recognizer was unsure about",
    "eye_contact_ratio": "share of time looking at the camera (estimate)",
    "look_aways_per_min": "look-aways of 3 seconds or more per minute",
    "slouch_ratio": "share of time slouching",
    "head_down_ratio": "share of time with head down",
    "tilt_ratio": "share of time with tilted shoulders",
    "lean_ratio": "share of time leaning",
    "hands_visible_ratio": "share of time hands were visible",
    "gestures_per_min_visible": "gestures per minute while hands were visible",
    "open_gesture_ratio_visible": "share of open-hand gestures",
    "arms_crossed_ratio": "share of time with arms crossed",
    "fidget_ratio": "share of time fidgeting",
    "face_touches_per_min": "face touches per minute",
    "sway_ratio": "share of time swaying",
    "tense_ratio": "share of time with a tense face",
    "negative_emotion_ratio": "share of time the face looked sad, angry, fearful or disgusted",
}

_PERCENT_METRICS = {
    m for m in METRIC_LABELS if m.endswith(("_ratio", "_share", "_error", "_coverage"))
} | {"wpm_variability", "phoneme_similarity"}


def _fmt(metric: str, value: float) -> str:
    if metric in _PERCENT_METRICS and metric != "vocabulary_mattr":
        return f"{value:.0%}"
    return f"{value:.1f}" if abs(value) < 100 else f"{value:.0f}"


def _level(score: float | None) -> str:
    if score is None:
        return "not scored"
    score = round(score)  # match the number the speaker sees
    return "a strength" if score >= 80 else "okay" if score >= 60 else "needs work"


def _rule_fact(cat: str, r: RuleResult) -> Fact:
    if r.penalty > 0:
        advice = ADVICE[r.id]
        text = f"Problem: {r.message} Advice: {advice.fix} Drill: {advice.drill}"
        return Fact(id=f"{cat}.{r.id}", category=cat, kind="problem", text=text)
    label = METRIC_LABELS.get(r.metric, r.metric.replace("_", " "))
    return Fact(
        id=f"{cat}.{r.id}",
        category=cat,
        kind="good",
        text=f"Good: {label} was {_fmt(r.metric, r.value)}, inside the healthy range.",
    )


def build_prompt(report: Report, transcript_text: str, facts: list[Fact]) -> str:
    words = transcript_text.split()
    text = " ".join(words[:MAX_TRANSCRIPT_WORDS]) + (
        " …" if len(words) > MAX_TRANSCRIPT_WORDS else ""
    )
    scored = [c for c, s in report.scores.categories.items() if s.status == "scored"]
    return json.dumps(
        {
            "task": (
                "Write the coaching report. Give exactly 3 strengths (fewer only if there are "
                "not enough good facts), up to 3 gaps and up to 3 top fixes ordered by "
                "importance, one section per scored category, a 2 to 3 sentence summary, and "
                "clarity feedback with up to 3 examples from the transcript."
            ),
            "scored_categories": scored,
            "facts": [f.model_dump() for f in facts],
            "transcript": text,
        },
        ensure_ascii=False,
    )


def call_ollama(url: str, model: str, prompt: str, timeout_s: int = TIMEOUT_S) -> dict[str, Any]:
    body = {
        "model": model,
        "stream": False,
        "format": LlmOutput.model_json_schema(),
        "options": {"temperature": 0.3, "num_ctx": 8192, "num_predict": 2500},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }
    req = urllib.request.Request(
        f"{url.rstrip('/')}/api/chat",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as res:  # noqa: S310 - local Ollama URL
        data: dict[str, Any] = json.loads(res.read())
    return json.loads(data["message"]["content"])  # type: ignore[no-any-return]


# ---- checking ---------------------------------------------------------------


def _numbers(text: str) -> list[float]:
    return [float(n) for n, _ in _NUMBER.findall(text)]


def allowed_numbers(texts: list[str]) -> set[float]:
    out: set[float] = set()
    for t in texts:
        for n in _numbers(t):
            out.update({n, round(n), round(n, 1)})
    return out


def numbers_ok(text: str, allowed: set[float]) -> bool:
    """Every number in the text must come from the cited facts (1 to 3 are always fine)."""
    for n in _numbers(text):
        if n in {1, 2, 3} or n in allowed or round(n) in allowed or round(n, 1) in allowed:
            continue
        return False
    return True


def _norm(s: str) -> str:
    return re.sub(r"[^\w']+", " ", s.lower()).strip()


class Checker:
    def __init__(self, facts: list[Fact], transcript_text: str) -> None:
        self.facts = {f.id: f for f in facts}
        self.transcript = _norm(transcript_text)
        self.dropped = 0

    def cited(
        self, ids: list[str], kinds: set[str], category: str | None = None
    ) -> list[Fact] | None:
        found = [self.facts[i] for i in ids if i in self.facts]
        if not found or len(found) != len(ids):
            return None
        if not any(f.kind in kinds for f in found):
            return None
        if category and not all(f.category in {category, "overall"} for f in found):
            return None
        return found

    def ok(
        self, texts: list[str], ids: list[str], kinds: set[str], category: str | None = None
    ) -> bool:
        facts = self.cited(ids, kinds, category)
        if facts is None:
            self.dropped += 1
            return False
        allowed = allowed_numbers([f.text for f in facts])
        if not all(numbers_ok(t, allowed) for t in texts):
            self.dropped += 1
            return False
        return True

    def quoted(self, original: str) -> bool:
        return len(original.split()) >= 4 and _norm(original) in self.transcript


def merge(
    report: Report, out: LlmOutput, facts: list[Fact], transcript_text: str, model: str
) -> Report:
    """Use each LLM item that passes the checks; keep the template text for the rest."""
    check = Checker(facts, transcript_text)
    problems = {f.id: f for f in facts if f.kind == "problem"}

    strengths = [s.text for s in out.strengths if check.ok([s.text], s.fact_ids, {"good"})][:3]
    if len(strengths) < min(3, len(report.strengths)):
        strengths += [s for s in report.strengths if s not in strengths][: 3 - len(strengths)]

    # Gaps and fixes keep the template's order (biggest penalty first); the LLM only
    # rewords them. An LLM item is matched to the rule it cites first.
    def first_rule(ids: list[str]) -> str | None:
        return next((i.split(".", 1)[1] for i in ids if i in problems), None)

    llm_gaps = {
        first_rule(g.fact_ids): g.text
        for g in out.gaps
        if check.ok([g.text], g.fact_ids, {"problem"})
    }
    gaps = [
        g.model_copy(update={"message": llm_gaps.get(g.rule_id, g.message)}) for g in report.gaps
    ]

    llm_fixes = {
        first_rule(f.fact_ids): f
        for f in out.top_fixes
        if check.ok([f.title, f.how, f.drill], f.fact_ids, {"problem"})
    }
    fixes = []
    for g, tf in zip(report.gaps, report.top_fixes, strict=False):
        lf = llm_fixes.get(g.rule_id)
        fixes.append(Fix(title=lf.title, how=lf.how, drill=lf.drill) if lf else tf)

    by_cat = {s.category: s for s in out.sections}
    sections = []
    for sec in report.sections:
        llm = by_cat.get(sec.category)
        if (
            sec.status == "scored"
            and llm is not None
            and check.ok(
                [llm.what_happened, llm.why_it_matters, llm.how_to_fix, llm.drill],
                llm.fact_ids,
                {"problem", "good", "info"},
                sec.category,
            )
        ):
            sec = sec.model_copy(
                update={
                    "what_happened": [llm.what_happened],
                    "why_it_matters": llm.why_it_matters or CATEGORY_WHY.get(sec.category, ""),
                    "how_to_fix": [llm.how_to_fix] if llm.how_to_fix else sec.how_to_fix,
                    "drill": llm.drill or sec.drill,
                }
            )
        sections.append(sec)

    all_numbers = allowed_numbers([f.text for f in facts])
    summary = out.summary if numbers_ok(out.summary, all_numbers) else None
    examples = [
        ClarityExample(original=e.original.strip(), suggestion=e.suggestion.strip())
        for e in out.clarity.examples
        if check.quoted(e.original) and e.suggestion.strip()
    ][:3]
    clarity = (
        Clarity(feedback=out.clarity.feedback, examples=examples)
        if (out.clarity.feedback and numbers_ok(out.clarity.feedback, all_numbers))
        else None
    )

    log.info("LLM report merged; %d items dropped by the checker", check.dropped)
    return report.model_copy(
        update={
            "generated_by": "llm",
            "llm_model": model,
            "summary": summary,
            "strengths": strengths,
            "gaps": gaps,
            "top_fixes": fixes,
            "sections": sections,
            "clarity": clarity,
            "llm_items_dropped": check.dropped,
        }
    )


def run(report: Report, transcript_text: str, *, url: str, model: str) -> Report:
    """Return the report rewritten by the LLM, or the template report if Ollama fails."""
    facts = build_facts(report)
    try:
        raw = call_ollama(url, model, build_prompt(report, transcript_text, facts))
        out = LlmOutput.model_validate(raw)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        log.warning("Ollama unavailable at %s (%s); using the template report", url, exc)
        return report.model_copy(
            update={"llm_error": "The local AI coach (Ollama) was not reachable."}
        )
    except (ValidationError, json.JSONDecodeError, KeyError) as exc:
        log.warning("Ollama returned unusable output (%s); using the template report", exc)
        return report.model_copy(
            update={"llm_error": "The local AI coach returned an unusable answer."}
        )
    return merge(report, out, facts, transcript_text, model)
