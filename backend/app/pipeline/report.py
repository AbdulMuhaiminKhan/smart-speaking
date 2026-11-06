"""Step 8 (basic): a coaching report built from templates and the scored metrics.

Phase 5 adds an LLM that rewrites this in a more personal voice. This template
version stays as the fallback when Ollama is unavailable, and it never says
anything that is not backed by a metric.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.pipeline.scoring import Scores
from app.schemas.metrics import (
    BodyMetrics,
    Issue,
    LanguageMetrics,
    PacingMetrics,
    PronunciationMetrics,
    VoiceMetrics,
)


class Advice(BaseModel):
    title: str
    why: str
    fix: str
    drill: str


# Coaching text per scoring rule id.
ADVICE: dict[str, Advice] = {
    "too_fast": Advice(
        title="Slow down",
        why="Listeners need time to absorb each idea. Fast speech also sounds nervous.",
        fix="Aim for 130 to 160 words per minute. Pause after every key point.",
        drill="Read one paragraph aloud while tapping a slow beat, one word per tap. Record it and compare.",
    ),
    "too_slow": Advice(
        title="Pick up the pace",
        why="A very slow pace can make listeners drift off.",
        fix="Aim for 130 to 160 words per minute and cut long gaps between sentences.",
        drill="Retell a short story in 60 seconds, then again in 45 seconds without dropping any facts.",
    ),
    "fast_stretches": Advice(
        title="Watch for rushing",
        why="Rushed sections are where listeners lose the thread.",
        fix="Find the rushed moments on the timeline. They are often the parts you know best.",
        drill="Practice the rushed section with a deliberate pause after each sentence.",
    ),
    "uneven_pace": Advice(
        title="Keep a steadier pace",
        why="Big swings in speed make a talk feel uneven.",
        fix="Vary pace on purpose for emphasis, not by accident.",
        drill="Record one minute at a steady pace, then the same minute slowing only for the key line.",
    ),
    "awkward_pauses": Advice(
        title="Fill the long silences with a plan",
        why="Silences over 2.5 seconds feel like you lost your place.",
        fix="Use short notes with one keyword per point so you can find the next idea quickly.",
        drill="Practice transitions: say only the first sentence of each section, back to back.",
    ),
    "hesitations": Advice(
        title="Pause between ideas, not inside them",
        why="Pauses mid-sentence sound like searching for words.",
        fix="Finish the sentence, then pause. Know your opening words for each point.",
        drill="Write the first five words of each point and practice starting each one cleanly.",
    ),
    "too_few_pauses": Advice(
        title="Use pauses",
        why="Pauses give weight to what you just said and time to breathe.",
        fix="Take a one second pause at the end of each important sentence.",
        drill="Mark pauses with a slash in your notes and practice honoring every slash.",
    ),
    "off_target_time": Advice(
        title="Hit your time",
        why="Running long or short in a timed pitch signals poor preparation.",
        fix="Trim or add one supporting point, then rehearse with a timer.",
        drill="Do three timed run-throughs and note where you are at the halfway mark.",
    ),
    "monotone": Advice(
        title="Add vocal variety",
        why="A flat voice makes even exciting content sound dull.",
        fix="Raise your pitch on key words and drop it at the end of statements.",
        drill="Read a sentence three times, stressing a different word each time.",
    ),
    "narrow_range": Advice(
        title="Widen your pitch range",
        why="A wider range keeps listeners engaged.",
        fix="Let your voice go higher for questions and excitement, lower for serious points.",
        drill="Read a children's story aloud with exaggerated expression, then dial it back halfway.",
    ),
    "quiet_stretches": Advice(
        title="Project through the whole talk",
        why="Quiet stretches are hard to hear and sound unsure.",
        fix="Breathe from your belly and aim your voice at the back of the room.",
        drill="Practice with the microphone two meters away and keep the level steady.",
    ),
    "volume_swings": Advice(
        title="Keep your volume steady",
        why="Big jumps in volume are tiring to listen to.",
        fix="Keep a steady base volume and use small changes for emphasis.",
        drill="Read a paragraph while watching a level meter and keep it in one band.",
    ),
    "trailing_off": Advice(
        title="Keep your energy to the end",
        why="Fading out makes the ending, often the key message, the weakest part.",
        fix="Plan a strong closing line and deliver it a little louder.",
        drill="Practice only your last minute, three times, at full energy.",
    ),
    "fillers": Advice(
        title="Cut filler words",
        why="Fillers dilute your message and can sound unprepared.",
        fix='Replace each "um" or "like" with a short silent pause.',
        drill="Talk for one minute on any topic. Each time you say a filler, stop and restart the sentence.",
    ),
    "hedging": Advice(
        title="Speak with conviction",
        why='Hedges like "I think" and "sort of" weaken your points.',
        fix="State your point directly. Keep hedges only where you really are unsure.",
        drill="Rewrite three hedged sentences from the transcript as direct statements and say them aloud.",
    ),
    "repetitions": Advice(
        title="Reduce repeated words",
        why='Stumbles like "the the" break your flow.',
        fix="Slow down slightly at the start of sentences, where repeats usually happen.",
        drill="Practice the first line of each section until it comes out cleanly three times in a row.",
    ),
    "low_variety": Advice(
        title="Vary your vocabulary",
        why="Repeating the same words makes a talk feel flat.",
        fix="Find your most-used words in the transcript and prepare alternatives.",
        drill="Explain your topic in one minute without using your top three repeated words.",
    ),
    "long_sentences": Advice(
        title="Use shorter sentences",
        why="Long sentences are hard to follow by ear.",
        fix="Aim for one idea per sentence, under 20 words.",
        drill="Split three of your longest sentences into two or three short ones and say them aloud.",
    ),
    "off_script": Advice(
        title="Stick closer to your script",
        why="Skipped passages may be the points you meant to make.",
        fix="Check the skipped passages and decide if they belong in the talk.",
        drill="Run through the script once reading, once from keywords only.",
    ),
    "unclear_words": Advice(
        title="Pronounce key words clearly",
        why="Words that are hard to make out force listeners to guess.",
        fix="Slow down on long or important words and open your mouth a little more.",
        drill="Look up the flagged words, listen to a reference, and repeat each one slowly three times, then at normal speed.",
    ),
    "low_phoneme_match": Advice(
        title="Articulate every sound",
        why="Dropped or blurred sounds make speech harder to follow, especially on video calls.",
        fix="Finish the last sound of each word, especially t, d, s and k.",
        drill="Read a paragraph while exaggerating every consonant, then read it again normally.",
    ),
    "hard_to_transcribe": Advice(
        title="Speak up and enunciate",
        why="If a speech recognizer struggles, listeners at the back of the room will too.",
        fix="Project a little more and keep your mouth unobstructed by hands or the microphone.",
        drill="Record yourself reading a news article aloud and check that every word comes through.",
    ),
    "low_eye_contact": Advice(
        title="Look at the camera",
        why="The camera is your audience's eyes. Looking away reads as unsure or distracted.",
        fix="Put a small sticker next to your webcam and talk to it. Glance at notes only between sentences.",
        drill="Record one minute while keeping your eyes on the camera lens, then watch it back.",
    ),
    "long_look_aways": Advice(
        title="Shorten your look-aways",
        why="Long glances away break the connection with your audience.",
        fix="When you need to think or check notes, keep it under two seconds and come back to the camera.",
        drill="Practice your talk with notes below the camera and return your eyes after every sentence.",
    ),
    "slouching": Advice(
        title="Sit or stand tall",
        why="Slouching makes you look tired and also squeezes your breathing and voice.",
        fix="Feet flat, back straight, shoulders down and back, as if a string pulls up the top of your head.",
        drill="Before each practice, roll your shoulders back three times and take two deep breaths.",
    ),
    "head_down": Advice(
        title="Keep your chin up",
        why="Looking down hides your face and drops your voice.",
        fix="Raise your notes or screen to eye level so you do not need to look down.",
        drill="Practice with your notes taped next to the camera.",
    ),
    "shoulder_tilt": Advice(
        title="Level your shoulders",
        why="Tilted shoulders look casual or unsure.",
        fix="Spread your weight evenly and sit square to the camera.",
        drill="Check your shoulders in a mirror before you start and once in the middle.",
    ),
    "leaning": Advice(
        title="Stay centred",
        why="Leaning to one side looks unsettled.",
        fix="Centre yourself in the frame and keep your head over your shoulders.",
        drill="Record 30 seconds and check that your nose stays above the middle of your chest.",
    ),
    "hands_out_of_frame": Advice(
        title="Let your hands be seen",
        why="Gestures help explain and emphasize, but only if people can see them.",
        fix="Move back a little from the camera so your hands are in frame at chest height.",
        drill="Frame yourself from the waist up and explain one idea using a gesture.",
    ),
    "few_gestures": Advice(
        title="Use your hands",
        why="Natural gestures make you look confident and help people follow.",
        fix='Use simple gestures for numbers, size and contrast ("on one hand… on the other").',
        drill="Explain three points while showing one, two, three fingers.",
    ),
    "too_many_gestures": Advice(
        title="Calm your hands",
        why="Constant movement pulls attention away from your words.",
        fix="Return your hands to a resting position between gestures.",
        drill="Practice with your hands resting together at waist height, gesturing only on key words.",
    ),
    "closed_gestures": Advice(
        title="Open up your gestures",
        why="Open palms look honest and welcoming; fists and hidden hands look guarded.",
        fix="Show your palms when you make a point, at about chest height.",
        drill="Say your main message three times with open palms facing the camera.",
    ),
    "arms_crossed": Advice(
        title="Uncross your arms",
        why="Crossed arms look defensive, even when you are just comfortable.",
        fix="Rest your hands loosely in front of you between gestures.",
        drill="Practice your opening with hands visible and arms apart.",
    ),
    "fidgeting": Advice(
        title="Reduce fidgeting",
        why="Fidgeting signals nerves and distracts from what you say.",
        fix="Hold a pen or rest your hands lightly together when you are not gesturing.",
        drill="Record one minute and stop every time your hands fidget; start again calmly.",
    ),
    "face_touching": Advice(
        title="Keep your hands away from your face",
        why="Touching your face often reads as nervousness.",
        fix="Notice the urge and lower your hands to a resting position instead.",
        drill="Practice with your hands resting on the desk for a full minute.",
    ),
    "swaying": Advice(
        title="Stand still",
        why="Swaying side to side is distracting and looks nervous.",
        fix="Plant your feet hip-width apart and move only with purpose.",
        drill="Practice your talk with your weight evenly on both feet, pausing to reset if you sway.",
    ),
    "tense_face": Advice(
        title="Relax your face",
        why="A tense face makes you look stressed, even if you feel fine.",
        fix="Unclench your jaw and soften your eyebrows. Smile at the start and the end.",
        drill="Before you start, take a deep breath and smile at the camera for two seconds.",
    ),
}

CATEGORY_WHY: dict[str, str] = {
    "pronunciation": "Clear pronunciation means no one has to work to understand you.",
    "eye_contact": "Eye contact builds trust and keeps people listening.",
    "posture": "Good posture looks confident and helps your voice carry.",
    "body_language": "Open, calm body language supports what you say.",
    "pacing": "Pace and pauses decide whether listeners can keep up.",
    "voice": "Pitch and volume carry emotion and keep attention.",
    "language": "Clear, direct words make your message stick.",
}


class Gap(BaseModel):
    category: str
    rule_id: str
    title: str
    message: str
    penalty: float


class Section(BaseModel):
    category: str
    score: float | None
    status: Literal["scored", "not_scored"]
    what_happened: list[str]
    why_it_matters: str
    how_to_fix: list[str]
    drill: str | None


class Fix(BaseModel):
    title: str
    how: str
    drill: str


class ClarityExample(BaseModel):
    original: str
    suggestion: str


class Clarity(BaseModel):
    feedback: str
    examples: list[ClarityExample]


class Report(BaseModel):
    generated_by: Literal["template", "llm"] = "template"
    llm_model: str | None = None
    llm_error: str | None = None  # why the AI coach was not used, if it was not
    llm_items_dropped: int = 0  # AI statements rejected for not matching the metrics
    summary: str | None = None
    clarity: Clarity | None = None
    overall: float | None
    scores: Scores
    strengths: list[str]
    gaps: list[Gap]
    top_fixes: list[Fix]
    sections: list[Section]
    issues: list[Issue]
    highlights: dict[str, str | float | int | None]


def strengths(
    pacing: PacingMetrics | None,
    voice: VoiceMetrics | None,
    language: LanguageMetrics | None,
    scores: Scores,
    body: BodyMetrics | None = None,
    pronunciation: PronunciationMetrics | None = None,
) -> list[str]:
    """Positive observations, each tied to a metric with no penalty."""
    passed = {r.id for c in scores.categories.values() for r in c.rules if r.penalty == 0}
    out: list[tuple[float, str]] = []  # (priority, text)
    if pacing:
        if {"too_fast", "too_slow"} <= passed:
            out.append((3, f"Comfortable pace of {pacing.wpm_overall:.0f} words per minute."))
        if "awkward_pauses" in passed and "hesitations" in passed:
            out.append((2, "Smooth delivery with no awkward silences."))
        if "too_few_pauses" in passed:
            out.append(
                (2.5, f"Good use of pauses ({pacing.effective_pause_count} at sentence breaks).")
            )
        if "off_target_time" in passed and pacing.target_seconds:
            out.append((3, "You finished close to your target time."))
    if voice:
        if "monotone" in passed and voice.pitch_std_semitones is not None:
            out.append(
                (
                    3,
                    f"Expressive voice with good pitch variety ({voice.pitch_std_semitones:.1f} semitones).",
                )
            )
        if "quiet_stretches" in passed and "volume_swings" in passed:
            out.append((2, "Steady, consistent volume."))
        if voice.tone == "confident":
            out.append((2.8, "You sounded confident overall."))
    if language:
        if "fillers" in passed:
            n = len(language.fillers)
            out.append(
                (
                    3.2,
                    "Almost no filler words."
                    if n <= 2
                    else f"Few filler words ({language.fillers_per_min:.1f} per minute).",
                )
            )
        if "hedging" in passed and language.word_count >= 50:
            out.append((1.5, "Direct language with little hedging."))
        if "low_variety" in passed:
            out.append((1.8, "Varied vocabulary."))
        if language.script and "off_script" in passed:
            out.append((2.5, f"You covered {language.script.coverage:.0%} of your script."))
    if (
        pronunciation
        and scores.categories["pronunciation"].status == "scored"
        and {"unclear_words", "low_phoneme_match"} <= passed
    ):
        out.append((2.6, "Clear pronunciation."))
    if body:
        scored = {k for k, c in scores.categories.items() if c.status == "scored"}
        if "eye_contact" in scored and "low_eye_contact" in passed and body.eye_contact_ratio:
            out.append((3.1, f"Strong eye contact ({body.eye_contact_ratio:.0%} of the time)."))
        if "posture" in scored and {"slouching", "head_down"} <= passed:
            out.append((2.4, "Upright, steady posture."))
        if "body_language" in scored:
            if "closed_gestures" in passed and "few_gestures" in passed:
                out.append((2.2, "Open, natural hand gestures."))
            if (body.smile_ratio or 0) >= 0.15:
                out.append(
                    (2.0, f"Friendly expression (smiling {body.smile_ratio:.0%} of the time).")
                )
            if {"fidgeting", "swaying", "face_touching"} <= passed and body.hands_visible_ratio:
                out.append((1.6, "Calm body with little fidgeting."))
    out.sort(key=lambda x: -x[0])
    return [text for _, text in out[:3]]


def build(
    *,
    scores: Scores,
    issues: list[Issue],
    pacing: PacingMetrics | None,
    voice: VoiceMetrics | None,
    language: LanguageMetrics | None,
    body: BodyMetrics | None = None,
    pronunciation: PronunciationMetrics | None = None,
) -> Report:
    penalised = sorted(
        ((cat, r) for cat, c in scores.categories.items() for r in c.rules if r.penalty > 0),
        key=lambda x: -x[1].penalty,
    )
    gaps = [
        Gap(
            category=cat,
            rule_id=r.id,
            title=ADVICE[r.id].title,
            message=r.message,
            penalty=r.penalty,
        )
        for cat, r in penalised[:3]
    ]
    top_fixes = [
        Fix(title=ADVICE[r.id].title, how=ADVICE[r.id].fix, drill=ADVICE[r.id].drill)
        for _, r in penalised[:3]
    ]

    sections: list[Section] = []
    for cat, c in scores.categories.items():
        if c.status == "not_scored":
            sections.append(
                Section(
                    category=cat,
                    score=None,
                    status="not_scored",
                    what_happened=[c.reason or "Not scored."],
                    why_it_matters="",
                    how_to_fix=[],
                    drill=None,
                )
            )
            continue
        bad = sorted((r for r in c.rules if r.penalty > 0), key=lambda r: -r.penalty)
        sections.append(
            Section(
                category=cat,
                score=c.score,
                status="scored",
                what_happened=[r.message for r in bad] or ["No problems found in this category."],
                why_it_matters=ADVICE[bad[0].id].why if bad else CATEGORY_WHY.get(cat, ""),
                how_to_fix=[ADVICE[r.id].fix for r in bad[:3]],
                drill=ADVICE[bad[0].id].drill if bad else None,
            )
        )

    highlights: dict[str, str | float | int | None] = {}
    if pacing:
        highlights.update(
            wpm=pacing.wpm_overall,
            pauses=pacing.pause_count,
            awkward_pauses=pacing.awkward_pause_count,
            speaking_time_s=pacing.speaking_time_s,
        )
    if voice:
        highlights.update(tone=voice.tone, pitch_variety_st=voice.pitch_std_semitones)
    if language:
        highlights.update(
            fillers=len(language.fillers),
            fillers_per_min=language.fillers_per_min,
            hedges=len(language.hedges),
            words=language.word_count,
        )

    return Report(
        overall=scores.overall,
        scores=scores,
        strengths=strengths(pacing, voice, language, scores, body, pronunciation),
        gaps=gaps,
        top_fixes=top_fixes,
        sections=sections,
        issues=issues,
        highlights=highlights,
    )
