# How SmartSpeaking scores a talk

Every score is computed by fixed rules from measured metrics. No AI model
decides a score. The rules live in
[`backend/app/pipeline/scoring_rules.yaml`](../backend/app/pipeline/scoring_rules.yaml),
and this page explains them. If you change a threshold, change it in the YAML
file and update this page.

## How a category score works

Each category starts at **100** and loses points for each rule it breaks.

A rule names one metric, a starting threshold, a "full penalty" threshold and
a maximum penalty. Between the two thresholds the penalty grows in a straight
line. Example: the filler rule starts at 2 fillers per minute and reaches its
full 40 point penalty at 10 per minute, so 6 fillers per minute costs 20 points.

A score never goes below 0. A rule is skipped when its metric cannot be
measured reliably (for example, vocabulary variety on a talk with fewer than
100 words). Skipped rules cost nothing.

## Overall score

The overall score is the weighted average of the categories that were scored:

| Category | Weight |
| --- | --- |
| Voice | 1.0 |
| Pacing | 1.0 |
| Language | 1.0 |
| Pronunciation | 1.0 |
| Eye contact | 1.0 |
| Posture | 0.75 |
| Body language | 0.75 |

A category that could not be scored (for example, no face in the video, or a
feature not built yet) is left out of the average rather than counted as 0.

## Pacing

Measured from Whisper's word timestamps.

- **Words per minute (WPM)** = words ÷ time from the first word to the last.
- **WPM over time** uses a 20 second window moved in 5 second steps.
- **Pauses** are gaps between words of 0.3 s or more:
  - *Effective*: at a sentence or clause break (after `. , ? ! ; :`), under 2.5 s.
  - *Hesitation*: mid-sentence, 0.6 s to 2.5 s.
  - *Awkward*: 2.5 s or longer, anywhere.
  - Mid-sentence gaps under 0.6 s are normal and not reported.

| Rule | Metric | Starts at | Full at | Max points |
| --- | --- | --- | --- | --- |
| too_fast | overall WPM | above 165 | 200 | 30 |
| too_slow | overall WPM | below 115 | 80 | 25 |
| fast_stretches | share of windows above 170 WPM | 20% | 60% | 15 |
| uneven_pace | variation of WPM over time | 30% | 60% | 10 |
| awkward_pauses | awkward pauses per minute | 0.5 | 3 | 20 |
| hesitations | hesitations per minute | 2 | 8 | 15 |
| too_few_pauses | effective pauses per minute (talks of 30 s or more) | below 3 | 0.5 | 10 |
| off_target_time | timed pitch: distance from target length | 10% | 50% | 20 |

Why these numbers: 130 to 160 WPM is the commonly recommended range for
presentations. Above about 170 listeners start to miss content.

## Voice

Measured with Praat (parselmouth) on frames inside spoken words only.

- **Pitch variety** is the standard deviation of pitch in semitones around your
  median pitch. Semitones make it fair across low and high voices. Frames more
  than an octave from the median are treated as tracking errors and ignored.
- **Pitch range** is the distance between the 5th and 95th percentile, in semitones.
- **Volume** is the median level of each second with at least 0.3 s of speech. *Quiet stretches* are seconds more than
  10 dB below your median. *Volume swings* is the robust spread (1.48 × median absolute deviation) of the per-second levels, so one mistimed word does not dominate.
- **Energy trend** is the slope of volume over the talk in dB per minute, only
  for talks with at least 60 seconds of speech.

| Rule | Metric | Starts at | Full at | Max points |
| --- | --- | --- | --- | --- |
| monotone | pitch variety (semitones) | below 2.5 | 1.2 | 35 |
| narrow_range | pitch range (semitones) | below 6 | 3 | 10 |
| quiet_stretches | share of quiet seconds | 10% | 40% | 20 |
| volume_swings | per-second volume spread (dB) | 6 | 10 | 10 |
| trailing_off | energy trend (dB per minute) | below −2 | −8 | 10 |

### Tone label

The tone label (confident, nervous, flat or rushed) is a **heuristic**, not a
trained emotion model. It is shown with the reasons behind it.

- *Rushed* = 0.7 × how far WPM is above 160 (full at 200) + 0.3 × how few pauses there are.
- *Flat* = 0.7 × how far pitch variety is below 2.5 semitones (full at 1.0) + 0.3 × how little the volume moves.
- *Nervous* = 0.5 × fillers per minute (full at 6) + 0.3 × hesitations per minute (full at 4) + 0.2 × pace variation (full at 40%).

The highest of the three wins if it is at least 0.4. Otherwise the label is *confident*.

## Language

Word lists are in
[`backend/app/pipeline/lexicons/en.yaml`](../backend/app/pipeline/lexicons/en.yaml).

- **Fillers** always counted: um, uh, erm, hmm, you know, I mean, basically,
  actually, literally. Counted only in filler position:
  - *like*: after "was/is/I'm…" ("I was like"), or set off by commas
    ("it was, like, huge"). Not after "would", "looks", "feel" and similar.
  - *so* and *well*: at the start of a sentence followed by a comma ("So, …").
- **Hedges**: "I think", "I guess", "sort of", "kind of", "maybe", "probably" and
  similar. Longer phrases win ("I think maybe" counts once).
- **Repetitions**: the same word or two-word phrase twice in a row ("the the",
  "I was I was"), ignoring fillers.
- **Vocabulary variety** is the moving-average type-token ratio (MATTR) over a
  50 word window. It does not drop just because a talk is long.
- **Sentences** are split on Whisper's punctuation.
- **Script mode** aligns your words with your script and reports coverage,
  skipped passages and added passages (3 words or more).

| Rule | Metric | Starts at | Full at | Max points |
| --- | --- | --- | --- | --- |
| fillers | fillers per minute | 2 | 10 | 40 |
| hedging | hedges per minute | 1.5 | 6 | 15 |
| repetitions | repetitions per minute | 1 | 4 | 10 |
| low_variety | MATTR (100+ words) | below 0.6 | 0.45 | 15 |
| long_sentences | share of sentences over 30 words (3+ sentences) | 15% | 50% | 10 |
| off_script | script coverage | below 90% | 50% | 25 |

## Eye contact, posture and body language

Measured with MediaPipe Pose, Face Landmarker (with iris, blendshapes and head
pose) and Hand Landmarker on frames sampled at 10 per second (the face model
runs on every second sampled frame, 5 per second). Fidgeting and swaying are
1 to 4 Hz movements, which 10 frames per second can catch. Distances are
divided by shoulder width, so they do not depend on how far you sit from the
camera.

**These are estimates.** A webcam cannot see exactly where you look, and
lighting, glasses and camera angle all affect tracking.

- **Eye contact** (per frame with a face): head turned at most 15° sideways and
  20° up or down, and the eyes not turned away (MediaPipe eye-look blendshapes
  below 0.45 sideways or up, below 0.55 down, because the screen usually sits
  just under the camera). In live mode, the first 3 seconds calibrate where
  your camera is.
- **Slouching**: ear height above the shoulders is less than 0.35 shoulder widths.
- **Head down**: nose height above the shoulders is less than 0.25 shoulder widths.
- **Shoulder tilt**: shoulder line more than 8° from level.
- **Leaning**: head more than 0.3 shoulder widths to one side of the shoulder centre.
- **Arms crossed**: each wrist past the body's centre line at chest height.
- **Gestures**: a hand moving faster than 1 shoulder width per second starts a gesture.
- **Open hands**: at least three fingertips farther from the wrist than their middle joints.
- **Fidgeting**: both hands close together (under 0.6 shoulder widths) and moving,
  or a hand touching the face.
- **Face touch**: hand centre within 0.6 shoulder widths of the nose for 0.5 s or more.
- **Swaying**: in a 2 second window, the shoulder centre wobbles more than 0.04
  shoulder widths and crosses its average at least twice.
- **Expression**: smiling when the smile blendshape averages 0.35 or more; tense
  when brow-lowering or lip-pressing averages 0.4 or more; otherwise neutral.

| Category | Rule | Metric | Starts at | Full at | Max points |
| --- | --- | --- | --- | --- | --- |
| Eye contact | low_eye_contact | share of time with eye contact | below 75% | 30% | 60 |
| Eye contact | long_look_aways | look-aways of 3 s+ per minute | 0.5 | 3 | 20 |
| Posture | slouching | share of time slouching | 10% | 50% | 35 |
| Posture | head_down | share of time head down | 10% | 40% | 25 |
| Posture | shoulder_tilt | share of time tilted | 20% | 60% | 15 |
| Posture | leaning | share of time leaning | 20% | 60% | 10 |
| Body language | hands_out_of_frame | share of time hands visible | below 20% | 0% | 10 |
| Body language | few_gestures | gestures per minute of visible hands* | below 3 | 0 | 15 |
| Body language | too_many_gestures | gestures per minute of visible hands* | 40 | 80 | 10 |
| Body language | closed_gestures | share of open hands* | below 40% | 10% | 10 |
| Body language | arms_crossed | share of time arms crossed | 5% | 30% | 20 |
| Body language | fidgeting | share of visible-hand time fidgeting* | 10% | 40% | 20 |
| Body language | face_touching | face touches per minute | 0.5 | 3 | 10 |
| Body language | swaying | share of time swaying | 10% | 40% | 15 |
| Body language | tense_face | share of time with a tense face | 30% | 70% | 10 |

\* Only when your hands are visible at least 30% of the time.

- **Facial emotion** (estimate) from blendshapes, FACS-style: happy (smile and
  cheek raise), surprised (raised brows and wide eyes; jaw opening counts only
  a little because it moves while talking), sad (mouth corners down, inner
  brows up), angry (brows down, eyes narrowed, lips pressed), worried/fearful
  (wide eyes, inner brows up, lips stretched), displeased/disgusted (nose
  wrinkle, upper lip raised). The strongest wins if it reaches 0.25 (0.35 for
  happy); otherwise neutral. Sad, angry, worried or displeased for 3 seconds
  or more shows on the timeline.
- **Voice emotion** (estimate) from `superb/wav2vec2-base-superb-er`: neutral,
  happy, angry or sad per 4 second window of speech. It is shown in the report
  and given to the AI coach as context, but it does not change any score.

| Category | Rule | Metric | Starts at | Full at | Max points |
| --- | --- | --- | --- | --- | --- |
| Body language | negative_emotion | share of face frames sad, angry, worried or displeased | 25% | 60% | 10 |

**Not scored instead of guessed:** eye contact is not scored when your face is
visible in less than 30% of the video. Posture and body language are not
scored when your shoulders are visible in less than 30%. A video that is
mostly dark (mean brightness under 50 of 255) gets a lighting warning.

## Pronunciation

**This is an estimate.** It compares your sounds with espeak's standard
pronunciation (US English by default). Accents differ from that reference, so
an accent can be flagged even when you are easy to understand. The report and
the app say this next to the score.

How it works:

1. A wav2vec2 phoneme model (`facebook/wav2vec2-lv-60-espeak-cv-ft`) lists the
   sounds (phonemes) it hears, every 20 ms, across the whole recording.
2. espeak (through `phonemizer`) gives the expected phonemes for every word in
   the transcript.
3. For each Whisper segment, the heard phonemes are aligned against the
   expected phonemes of its words (edit-distance alignment). Aligning a whole
   segment is robust to word timestamps being slightly off. Similar sounds
   (for example the vowels in "bit" and "beat", or t and d) cost less than
   different ones.
4. Each word gets a **phoneme match** from 0 to 1.
5. A word is flagged as **may be mispronounced** when its match is under 0.45,
   or as **unclear** when its match is under 0.65 and Whisper was also unsure
   (confidence under 0.5).

Skipped words, so the estimate stays fair: filler words, short function words
("the", "and", "them", which are naturally reduced in speech), words under 3
letters or 3 phonemes, numbers, acronyms ("LED") and capitalized words in mid
sentence (names, which espeak often gets wrong). The category is not scored
when fewer than 20 words can be checked. If the phoneme model cannot load,
only very low Whisper confidence (under 0.3) is used to flag words.

| Rule | Metric | Starts at | Full at | Max points |
| --- | --- | --- | --- | --- |
| unclear_words | flagged words per 100 words | 2 | 12 | 40 |
| low_phoneme_match | average phoneme match | below 0.85 | 0.6 | 30 |
| hard_to_transcribe | share of words Whisper was unsure about | 10% | 35% | 20 |

## Known limits

- Whisper sometimes stretches a word's end time over a short silence, so very
  short pauses can be missed.
- Fillers depend on Whisper writing them down. The transcription prompt pushes
  it to keep them, but some may still be dropped, so counts can be slightly low.
- Rates on very short clips (under 30 s) swing a lot. One filler in 10 seconds
  is 6 per minute.

## AI-written coaching

Scores never come from the AI. After scoring, a local LLM (Ollama, default
`qwen2.5:7b`, set with `SS_OLLAMA_MODEL`) rewrites the coaching text in a more
personal voice and adds sentence-clarity feedback from the transcript.

What it receives: a list of numbered facts built from the scored rules (each
problem with its advice and drill, each passed rule as a strength), the
category scores with a label (strength, okay, needs work), counts of timeline
issues, and the transcript text. It never receives audio or video.

What is checked before anything is shown:

- Every strength, gap, fix and section must cite fact ids that exist. Strengths
  must cite passed rules, gaps and fixes must cite problems, and a category's
  section may only cite that category's facts.
- Every number in the text must appear in the cited facts (1, 2 and 3 are
  allowed as plain counts). An invented statistic drops the item.
- Clarity examples must quote the transcript word for word.
- Gaps and fixes stay in score order (biggest penalty first); the AI only
  rewords them.

Anything that fails a check is replaced by the template text, and the report
records how many items were dropped. If Ollama is not running, the whole
report uses the templates and says so. Set `SS_LLM_ENABLED=false` to always
use the templates.
