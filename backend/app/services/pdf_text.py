# ruff: noqa: E501  (translated sentences read better unbroken)
"""PDF report wording in English, German and Urdu (Urdu is laid out right to left)."""

from __future__ import annotations

from typing import Any

LANGS = ("en", "de", "ur")

# key: (en, de, ur)
_T: dict[str, tuple[str, str, str]] = {
    "report": (
        "SmartSpeaking practice report",
        "SmartSpeaking Übungsbericht",
        "SmartSpeaking مشق رپورٹ",
    ),
    "overall": ("Overall score", "Gesamtbewertung", "مجموعی اسکور"),
    "coach_llm": (
        "Coaching written by a local AI ({model}) from your measured metrics only.",
        "Coaching von einer lokalen KI ({model}), nur auf Basis deiner gemessenen Werte.",
        "یہ رائے ایک مقامی AI ({model}) نے صرف آپ کے ناپے گئے اعداد و شمار سے لکھی ہے۔",
    ),
    "coach_template": (
        "Coaching from built-in templates.",
        "Coaching aus eingebauten (englischen) Vorlagen.",
        "رائے پہلے سے بنے (انگریزی) سانچوں سے۔",
    ),
    "well": ("What you did well", "Das lief gut", "آپ نے کیا اچھا کیا"),
    "well_empty": (
        "Keep practicing to build strengths.",
        "Übe weiter, um Stärken aufzubauen.",
        "خوبیاں پیدا کرنے کے لیے مشق جاری رکھیں۔",
    ),
    "gaps": ("Biggest gaps", "Größte Lücken", "سب سے بڑی کمزوریاں"),
    "gaps_empty": ("No major gaps.", "Keine größeren Lücken.", "کوئی بڑی کمزوری نہیں۔"),
    "fixes": (
        "Your top {n} fixes for next time",
        "Deine {n} wichtigsten Punkte für das nächste Mal",
        "اگلی بار کے لیے آپ کی {n} اہم اصلاحات",
    ),
    "drill": ("Drill", "Übung", "مشق"),
    "by_category": ("By category", "Nach Kategorie", "زمرے کے لحاظ سے"),
    "not_scored": ("not scored", "nicht bewertet", "اسکور نہیں"),
    "pron_note": (
        "Estimate: compared with a standard reference pronunciation, so accents can be flagged.",
        "Schätzung: Vergleich mit einer Standardaussprache, daher kann ein Akzent markiert werden.",
        "اندازہ: معیاری تلفظ سے موازنہ، اس لیے لہجہ نشان زد ہو سکتا ہے۔",
    ),
    "camera_note": (
        "Estimated from camera tracking.",
        "Aus der Kameraerkennung geschätzt.",
        "کیمرا ٹریکنگ سے اندازہ۔",
    ),
    "clarity": ("Sentence clarity", "Satzklarheit", "جملوں کی وضاحت"),
    "you_said": ("You said", "Du sagtest", "آپ نے کہا"),
    "try": ("Try", "Besser", "یوں کہیں"),
    "over_time": ("Over time", "Im Verlauf", "وقت کے ساتھ"),
    "pace": ("Pace", "Tempo", "رفتار"),
    "pace_cap": (
        "Words per minute. Green band: comfortable pace.",
        "Wörter pro Minute. Grüner Bereich: angenehmes Tempo.",
        "الفاظ فی منٹ۔ سبز پٹی: آرام دہ رفتار۔",
    ),
    "pitch": ("Pitch", "Tonhöhe", "سُر"),
    "pitch_cap": (
        "Pitch in Hz. More movement sounds more expressive.",
        "Tonhöhe in Hz. Mehr Bewegung klingt ausdrucksstärker.",
        "سُر ہرٹز میں۔ زیادہ اتار چڑھاؤ زیادہ پُراثر لگتا ہے۔",
    ),
    "variation": ("Pitch variation", "Tonhöhenvariation", "سُر کا اتار چڑھاؤ"),
    "variation_cap": (
        "Semitones of spread in a 5 s window. Dips are flat stretches.",
        "Halbtöne Streuung im 5-s-Fenster. Täler sind flache Passagen.",
        "5 سیکنڈ میں سیمی ٹون کا پھیلاؤ۔ گراوٹ سپاٹ حصے ہیں۔",
    ),
    "volume": ("Volume", "Lautstärke", "آواز کی بلندی"),
    "volume_cap": ("Loudness in dB.", "Lautheit in dB.", "بلندی ڈیسی بل میں۔"),
    "eye": ("Eye contact", "Blickkontakt", "نظریں ملانا"),
    "eye_cap": (
        "Percent of time looking at the camera (estimate).",
        "Anteil der Zeit mit Blick in die Kamera (Schätzung).",
        "کیمرے کی طرف دیکھنے کا فیصد (اندازہ)۔",
    ),
    "delivery": ("Delivery in numbers", "Vortrag in Zahlen", "ادائیگی اعداد میں"),
    "emotions": ("Emotions", "Emotionen", "جذبات"),
    "estimates": ("estimates", "Schätzungen", "اندازے"),
    "face": ("Face", "Gesicht", "چہرہ"),
    "voice": ("Voice", "Stimme", "آواز"),
    "mistakes": ("Mistakes timeline", "Fehler-Zeitleiste", "غلطیوں کی ٹائم لائن"),
    "no_issues": ("No issues found.", "Keine Auffälligkeiten gefunden.", "کوئی مسئلہ نہیں ملا۔"),
    "notes": ("Your notes", "Deine Notizen", "آپ کے نوٹس"),
    "prompts": ("Topic and questions", "Thema und Fragen", "موضوع اور سوالات"),
    "mode": ("Practice mode", "Übungsmodus", "مشق کا طریقہ"),
    "target": ("target {time}", "Ziel {time}", "ہدف {time}"),
    "script": ("Script rehearsal", "Skriptprobe", "اسکرپٹ کی مشق"),
    "script_sum": (
        "{coverage}% of the script said; {extra}% of your words were your own.",
        "{coverage} % des Skripts gesagt; {extra} % eigene Worte.",
        "اسکرپٹ کا {coverage}% بولا؛ {extra}% الفاظ آپ کے اپنے۔",
    ),
    "skipped": ("Skipped", "Ausgelassen", "چھوڑا گیا"),
    "added": ("Added", "Hinzugefügt", "شامل کیا"),
    "transcript": ("Transcript", "Transkript", "تحریر"),
    "footer": (
        "Scores come from transparent rules (docs/scoring.md). Pronunciation and camera-based scores are estimates. This report was created on your own computer; nothing was sent to a cloud service.",
        "Die Bewertungen folgen transparenten Regeln (docs/scoring.md). Aussprache und kamerabasierte Werte sind Schätzungen. Dieser Bericht wurde auf deinem Computer erstellt; nichts wurde an einen Cloud-Dienst gesendet.",
        "اسکور واضح اصولوں (docs/scoring.md) پر مبنی ہیں۔ تلفظ اور کیمرا پر مبنی اسکور اندازے ہیں۔ یہ رپورٹ آپ کے اپنے کمپیوٹر پر بنی؛ کچھ بھی کلاؤڈ پر نہیں بھیجا گیا۔",
    ),
    "page": ("Page", "Seite", "صفحہ"),
    "of": ("of", "von", "از"),
    # Delivery metric labels
    "m_wpm": ("Pace", "Tempo", "رفتار"),
    "m_fillers": ("Filler words per minute", "Füllwörter pro Minute", "فالتو الفاظ فی منٹ"),
    "m_clarity": ("Words heard clearly", "Deutlich verstandene Wörter", "واضح سنے گئے الفاظ"),
    "m_pitch_var": ("Pitch variation", "Tonhöhenvariation", "سُر کا اتار چڑھاؤ"),
    "m_pauses": ("Pauses (long)", "Pausen (lang)", "وقفے (لمبے)"),
    "m_eye": ("Eye contact", "Blickkontakt", "نظریں ملانا"),
    "m_gestures": ("Gestures per minute", "Gesten pro Minute", "فی منٹ اشارے"),
    "monotone": ("monotone", "monoton", "یکساں لہجہ"),
}

CATEGORIES: dict[str, tuple[str, str, str]] = {
    "voice": ("Voice", "Stimme", "آواز"),
    "pacing": ("Pacing", "Tempo", "رفتار"),
    "language": ("Language", "Sprache", "زبان و بیان"),
    "pronunciation": ("Pronunciation", "Aussprache", "تلفظ"),
    "eye_contact": ("Eye contact", "Blickkontakt", "نظریں ملانا"),
    "posture": ("Posture", "Haltung", "جسمانی انداز"),
    "body_language": ("Body language", "Körpersprache", "باڈی لینگویج"),
}

MODES: dict[str, tuple[str, str, str]] = {
    "free_talk": ("Free talk", "Freie Rede", "آزاد گفتگو"),
    "timed_pitch": ("Timed pitch", "Pitch mit Zeitlimit", "وقت کی حد والی پِچ"),
    "script": ("Script rehearsal", "Skriptprobe", "اسکرپٹ کی مشق"),
    "impromptu": ("Impromptu", "Stegreifrede", "فی البدیہہ تقریر"),
    "elevator_pitch": ("Elevator pitch", "Elevator Pitch", "ایلیویٹر پِچ"),
    "interview": ("Interview Q&A", "Bewerbungsgespräch", "انٹرویو سوال و جواب"),
    "table_topics": ("Table Topics", "Table Topics", "ٹیبل ٹاپکس"),
}

EMOTIONS: dict[str, tuple[str, str, str]] = {
    "neutral": ("Neutral", "Neutral", "معمول کے مطابق"),
    "happy": ("Happy", "Fröhlich", "خوش"),
    "surprised": ("Surprised", "Überrascht", "حیران"),
    "sad": ("Sad", "Traurig", "اداس"),
    "angry": ("Angry", "Verärgert", "ناراض"),
    "fearful": ("Worried", "Besorgt", "فکرمند"),
    "disgusted": ("Displeased", "Missmutig", "ناخوش"),
    "calm": ("Calm", "Ruhig", "پُرسکون"),
}

# Timeline messages by issue kind; {value} and {text} come from the issue.
ISSUES: dict[str, tuple[str, str, str]] = {
    "awkward_pause": ("{value} s silence", "{value} s Stille", "{value} سیکنڈ کی خاموشی"),
    "hesitation": (
        "{value} s hesitation mid-sentence",
        "{value} s Zögern mitten im Satz",
        "جملے کے بیچ {value} سیکنڈ کی ہچکچاہٹ",
    ),
    "too_fast": (
        "Speaking fast, up to {value} words per minute",
        "Schnelles Sprechen, bis zu {value} Wörter pro Minute",
        "تیز بولنا، {value} الفاظ فی منٹ تک",
    ),
    "too_slow": (
        "Speaking slowly, down to {value} words per minute",
        "Langsames Sprechen, bis zu {value} Wörter pro Minute",
        "آہستہ بولنا، {value} الفاظ فی منٹ تک",
    ),
    "monotone": ("Flat, monotone stretch", "Flache, monotone Passage", "سپاٹ، یکساں لہجے والا حصہ"),
    "too_quiet": (
        "Much quieter than the rest of your talk",
        "Viel leiser als der Rest deines Vortrags",
        "باقی تقریر سے بہت دھیمی آواز",
    ),
    "filler": ('Filler word "{text}"', "Füllwort „{text}“", 'فالتو لفظ "{text}"'),
    "hedge": ('Hedging phrase "{text}"', "Abschwächung „{text}“", 'ہچکچاہٹ والا جملہ "{text}"'),
    "repetition": ('Repeated "{text}"', "Wiederholt: „{text}“", 'تکرار "{text}"'),
    "long_sentence": (
        "Very long sentence (over 30 words)",
        "Sehr langer Satz (über 30 Wörter)",
        "بہت لمبا جملہ (30 سے زیادہ الفاظ)",
    ),
    "looking_away": (
        "Looking away from the camera",
        "Blick von der Kamera abgewandt",
        "کیمرے سے نظریں ہٹی ہوئی",
    ),
    "head_down": ("Head down", "Kopf gesenkt", "سر جھکا ہوا"),
    "slouch": ("Slouching", "Zusammengesunkene Haltung", "جھک کر کھڑے ہونا"),
    "arms_crossed": ("Arms crossed", "Verschränkte Arme", "بازو باندھے ہوئے"),
    "hands_hidden": ("Hands out of view", "Hände nicht im Bild", "ہاتھ نظر سے باہر"),
    "face_touch": ("Touching your face", "Berührt das Gesicht", "چہرے کو چھونا"),
    "fidget": ("Fidgeting with your hands", "Nestelt mit den Händen", "ہاتھوں سے بے چینی"),
    "sway": ("Swaying side to side", "Schwankt hin und her", "دائیں بائیں جھولنا"),
    "tense": ("Tense facial expression", "Angespannter Gesichtsausdruck", "چہرے پر تناؤ"),
}


def _idx(lang: str) -> int:
    return LANGS.index(lang) if lang in LANGS else 0


def text(lang: str, key: str, **kw: Any) -> str:
    s = _T[key][_idx(lang)]
    return s.format(**kw) if kw else s


def table(lang: str, table_: dict[str, tuple[str, str, str]], key: str) -> str:
    return table_[key][_idx(lang)] if key in table_ else key


def issue(lang: str, kind: str, message: str, value: float | None, word: str | None) -> str:
    """The timeline message in the report language; the stored English one as fallback."""
    if lang == "en" or kind not in ISSUES:
        return message
    v = "" if value is None else (f"{value:g}")
    return ISSUES[kind][_idx(lang)].format(value=v, text=word or "")


def strings(lang: str) -> dict[str, str]:
    return {k: v[_idx(lang)] for k, v in _T.items()}
