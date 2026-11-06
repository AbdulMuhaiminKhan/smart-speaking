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

## Coming in later phases

Pronunciation (Phase 4), eye contact, posture and body language (Phase 3) are
shown as "not scored" until their analysis is built.

## Known limits

- Whisper sometimes stretches a word's end time over a short silence, so very
  short pauses can be missed.
- Fillers depend on Whisper writing them down. The transcription prompt pushes
  it to keep them, but some may still be dropped, so counts can be slightly low.
- Rates on very short clips (under 30 s) swing a lot. One filler in 10 seconds
  is 6 per minute.
