import pytest

from app.pipeline import issues as issues_mod
from app.pipeline import language, pacing, report, scoring
from app.pipeline.scoring import Rule
from tests.helpers import transcript_from, words_from


def rule(**kw: object) -> Rule:
    base: dict[str, object] = {
        "id": "r",
        "metric": "m",
        "max_penalty": 20,
        "full": 10,
        "message": "{value}",
    }
    base.update(kw)
    return Rule.model_validate(base)


def test_rising_penalty_is_linear_and_capped() -> None:
    r = rule(above=5, full=10)
    assert r.penalty(4) == 0
    assert r.penalty(7.5) == 10
    assert r.penalty(50) == 20


def test_falling_penalty() -> None:
    r = rule(below=2.5, full=1.0)
    assert r.penalty(3) == 0
    assert r.penalty(1.75) == 10
    assert r.penalty(0) == 20


def test_rules_file_is_valid_and_has_advice_for_every_rule() -> None:
    rules = scoring.load_rules()
    ids = [r.id for rs in rules.categories.values() for r in rs]
    assert len(ids) == len(set(ids))
    assert set(ids) <= set(report.ADVICE)


def metrics_for(text: str, **gaps: float):  # type: ignore[no-untyped-def]
    t = transcript_from(words_from(text))
    p = pacing.run(t)
    lang = language.run(t, speaking_time_s=p.speaking_time_s)
    return p, lang


def test_clean_talk_scores_high_and_missing_categories_are_not_scored() -> None:
    p, lang = metrics_for(
        " ".join(f"Idea{i} supports topic{i} with example{i}." for i in range(40))
    )
    s = scoring.score(pacing=p, voice=None, language=lang)
    assert s.categories["language"].score == 100
    assert s.categories["voice"].status == "not_scored"
    assert s.categories["eye_contact"].score is None
    assert s.overall is not None and s.overall >= 90


def test_fillers_lower_language_score() -> None:
    p, lang = metrics_for(" ".join(["Um, so, like, you know, it is good."] * 20))
    s = scoring.score(pacing=p, voice=None, language=lang)
    lang_score = s.categories["language"]
    assert lang_score.score is not None and lang_score.score <= 60
    fillers = next(r for r in lang_score.rules if r.id == "fillers")
    assert fillers.penalty == 40


def test_overall_uses_weights() -> None:
    p, lang = metrics_for("Hello there. " * 50)
    s = scoring.score(pacing=p, voice=None, language=lang, not_scored={"pacing": "test"})
    assert s.categories["pacing"].status == "not_scored"
    assert s.overall == s.categories["language"].score


def test_report_lists_gaps_fixes_and_strengths() -> None:
    p, lang = metrics_for(" ".join(["Um, I think maybe it is, like, sort of fine."] * 15))
    s = scoring.score(pacing=p, voice=None, language=lang)
    rep = report.build(
        scores=s, issues=issues_mod.build(p, None, lang), pacing=p, voice=None, language=lang
    )
    assert rep.gaps[0].rule_id == "fillers"
    assert rep.top_fixes[0].title == "Cut filler words"
    assert len(rep.gaps) <= 3 and len(rep.strengths) <= 3
    kinds = {i.kind for i in rep.issues}
    assert {"filler", "hedge"} <= kinds
    assert rep.issues == sorted(rep.issues, key=lambda i: (i.start, i.id))
    lang_section = next(x for x in rep.sections if x.category == "language")
    assert lang_section.drill


def test_issues_merge_fast_windows() -> None:
    words = words_from(" ".join(["b"] * 200), word_s=0.2, gap_s=0.05)  # 240 wpm
    p = pacing.run(transcript_from(words))
    fast = [i for i in issues_mod.pacing_issues(p) if i.kind == "too_fast"]
    assert len(fast) == 1
    assert fast[0].severity == "major"
    assert fast[0].start == pytest.approx(0, abs=0.5)


def test_body_not_scored_reasons() -> None:
    from app.pipeline import body

    assert set(scoring.body_not_scored(None, has_video=False)) == {
        "eye_contact",
        "posture",
        "body_language",
    }
    empty = body.aggregate([], body.SAMPLE_FPS, 10)
    reasons = scoring.body_not_scored(empty, has_video=True)
    assert "visible in only 0%" in reasons["eye_contact"]
