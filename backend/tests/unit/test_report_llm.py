import json
import urllib.error

import pytest

from app.pipeline import issues as issues_mod
from app.pipeline import language, pacing, report, report_llm, scoring
from tests.helpers import transcript_from, words_from

TEXT = " ".join(["Um, I think maybe it is, like, sort of fine to start this way today."] * 12)


def base_report() -> report.Report:
    t = transcript_from(words_from(TEXT))
    p = pacing.run(t)
    lang = language.run(t, speaking_time_s=p.speaking_time_s)
    s = scoring.score(pacing=p, voice=None, language=lang)
    return report.build(
        scores=s, issues=issues_mod.build(p, None, lang), pacing=p, voice=None, language=lang
    )


def llm_output(**overrides: object) -> dict[str, object]:
    out: dict[str, object] = {
        "summary": "You kept a steady pace but used many fillers.",
        "strengths": [{"text": "Your pace felt steady.", "fact_ids": ["pacing.too_fast"]}],
        "gaps": [{"text": "You used a lot of filler words.", "fact_ids": ["language.fillers"]}],
        "sections": [],
        "top_fixes": [
            {
                "title": "Pause instead of um",
                "how": "Swap each um for a breath.",
                "drill": "One minute talk, restart on every filler.",
                "fact_ids": ["language.fillers"],
            }
        ],
        "clarity": {
            "feedback": "Some sentences ramble.",
            "examples": [
                {
                    "original": "I think maybe it is, like, sort of fine",
                    "suggestion": "It is fine.",
                },
                {"original": "This sentence was never said by anyone", "suggestion": "x"},
            ],
        },
    }
    out.update(overrides)
    return out


def merged(raw: dict[str, object]) -> report.Report:
    r = base_report()
    facts = report_llm.build_facts(r)
    return report_llm.merge(r, report_llm.LlmOutput.model_validate(raw), facts, TEXT, "test")


def test_facts_mark_problems_and_good_rules() -> None:
    facts = {f.id: f for f in report_llm.build_facts(base_report())}
    assert facts["language.fillers"].kind == "problem"
    assert "Drill:" in facts["language.fillers"].text
    assert facts["pacing.too_fast"].kind == "good"


def test_valid_items_are_used_and_gaps_keep_penalty_order() -> None:
    r = merged(llm_output())
    assert r.generated_by == "llm"
    assert r.summary == "You kept a steady pace but used many fillers."
    assert r.gaps[0].rule_id == "fillers"
    assert r.gaps[0].message == "You used a lot of filler words."
    assert r.top_fixes[0].title == "Pause instead of um"
    assert "Your pace felt steady." in r.strengths


def test_uncited_or_wrongly_cited_items_are_dropped() -> None:
    r = merged(
        llm_output(
            gaps=[
                {"text": "Your posture was bad.", "fact_ids": ["posture.slouching"]},  # not a fact
                {"text": "Great pace!", "fact_ids": ["pacing.too_fast"]},
            ],  # good fact as a gap
            strengths=[{"text": "No fillers at all.", "fact_ids": ["language.fillers"]}],  # problem
        )
    )
    template = base_report()
    assert [g.message for g in r.gaps] == [g.message for g in template.gaps]
    assert "No fillers at all." not in r.strengths
    assert r.llm_items_dropped == 3


def test_invented_numbers_are_dropped() -> None:
    r = merged(
        llm_output(
            gaps=[{"text": "You said 47 fillers per minute.", "fact_ids": ["language.fillers"]}],
            summary="Your score was 12 points lower than last week.",
        )
    )
    assert r.gaps[0].message == base_report().gaps[0].message
    assert r.summary is None


def test_numbers_from_cited_facts_are_allowed() -> None:
    r0 = base_report()
    fillers = next(x for x in r0.scores.categories["language"].rules if x.id == "fillers")
    text = f"You used {fillers.value:.1f} filler words per minute."
    r = merged(llm_output(gaps=[{"text": text, "fact_ids": ["language.fillers"]}]))
    assert r.gaps[0].message == text


def test_clarity_examples_must_quote_the_transcript() -> None:
    r = merged(llm_output())
    assert r.clarity is not None
    assert [e.original for e in r.clarity.examples] == ["I think maybe it is, like, sort of fine"]


def test_section_citing_another_category_is_rejected() -> None:
    section = {
        "category": "language",
        "what_happened": "Too many fillers.",
        "why_it_matters": "It distracts.",
        "how_to_fix": "Pause.",
        "drill": "Drill.",
        "fact_ids": ["pacing.too_fast"],
    }
    r = merged(llm_output(sections=[section]))
    lang = next(s for s in r.sections if s.category == "language")
    assert lang.what_happened != ["Too many fillers."]


def test_falls_back_when_ollama_is_down(monkeypatch: pytest.MonkeyPatch) -> None:
    def down(*a: object, **k: object) -> dict[str, object]:
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(report_llm, "call_ollama", down)
    r = report_llm.run(base_report(), TEXT, url="http://x", model="m")
    assert r.generated_by == "template" and r.llm_error


def test_falls_back_on_bad_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(report_llm, "call_ollama", lambda *a, **k: json.loads('{"summary": 1}'))
    r = report_llm.run(base_report(), TEXT, url="http://x", model="m")
    assert r.generated_by == "template" and r.llm_error


@pytest.mark.parametrize(
    "text,ok",
    [("You did 3 things", True), ("about 12.5 per minute", True), ("about 99 per minute", False)],
)
def test_numbers_ok(text: str, ok: bool) -> None:
    assert report_llm.numbers_ok(text, report_llm.allowed_numbers(["12.5 per minute"])) is ok
