---
version: 1
slug: "frontend-src"
primary_target: "frontend/src"
related_targets: []
---

# Surface: SmartSpeaking app (all screens under frontend/src)

Scope: the whole working app (dashboard, live practice, upload, sessions, session report, settings, sign-in). Mode: Operate. Build path: code-led (app screens; no image generation used). Decision round ran unattended: the owner was away, so the assigned direction was built without the decision page; re-roll on request.

Audience and job: one speaker practicing alone at a laptop, starting a session in seconds, reading a report, coming back tomorrow. Constraints: EN/DE/UR with right-to-left Urdu, light and dark from the OS, no new npm packages, no fonts or assets fetched at runtime, system font stacks only.

## Direction contract

THESIS: A talk is a performance you can read like a conductor's score: tempo, rests and dynamics, marked against time. The app refuses the category default of grey cards with a blue button and a gamified confetti layer.

OWN-WORLD: Engraved-score publishing. Deep score-navy shell rail, cool paper-white ground with a faint blue cast, ink-black text, conductor blue for actions, brass gold only for earned things (streak, achievements). Tempo voice: bold italic serif from the system stack for markings; everything else a system sans with tabular figures. Hairline rules, tight engraved density, small radii.

STORY: The speaker sees where they stand (score, trend, streak), starts practice in one click, and reads each session like an annotated score: where they rushed, rested too long or filled silence.

FIRST VIEWPORT: Desktop: navy side rail (wordmark, Dashboard, Live, Upload, Sessions, Settings, language, sign out, privacy line). Main: greeting and Practice live / Upload actions; streak, weekly goal and targets row; trends card. Mobile: rail becomes a top bar with a scrollable nav.

FORM: Grounded candidate 3 of 7 (orchestral score), seed:4796afe9a58e9b0a. Signature move: the session timeline drawn as a five-line stave with bar lines every ten seconds, bar numbers as time, issue marks as note heads on their category's line, and a tempo marking (Adagio, Andante, Allegro, Presto with words per minute) set above; the same tempo marking labels the live pace gauge.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
