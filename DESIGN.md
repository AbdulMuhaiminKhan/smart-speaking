---
name: SmartSpeaking
description: A speaking coach whose sessions read like an engraved conductor's score.
colors:
  conductor-blue: "oklch(0.5 0.19 264)"
  conductor-blue-deep: "oklch(0.42 0.17 265)"
  conductor-blue-bright: "oklch(0.58 0.18 263)"
  conductor-blue-wash: "oklch(0.97 0.018 262)"
  score-navy: "oklch(0.22 0.06 268)"
  score-navy-raised: "oklch(0.28 0.07 267)"
  score-mist: "oklch(0.86 0.05 262)"
  score-mist-light: "oklch(0.93 0.03 262)"
  brass: "oklch(0.8 0.14 80)"
  brass-deep: "oklch(0.72 0.15 72)"
  brass-light: "oklch(0.86 0.11 85)"
  paper: "oklch(0.982 0.006 255)"
  sheet: "#ffffff"
  hairline: "oklch(0.91 0.014 256)"
  rule: "oklch(0.84 0.018 257)"
  ink-muted: "oklch(0.55 0.025 259)"
  ink-soft: "oklch(0.36 0.03 261)"
  ink: "oklch(0.21 0.034 265)"
  ink-night: "oklch(0.16 0.032 266)"
  voice-violet: "oklch(54.1% 0.281 293.009)"
  pacing-sky: "oklch(58.8% 0.158 241.966)"
  language-amber: "oklch(66.6% 0.179 58.318)"
  pronunciation-rose: "oklch(58.6% 0.253 17.585)"
  eye-contact-emerald: "oklch(59.6% 0.145 163.225)"
  posture-orange: "oklch(64.6% 0.222 41.116)"
  body-language-teal: "oklch(60% 0.118 184.704)"
typography:
  display:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, \"Segoe UI\", \"Helvetica Neue\", Arial, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 600
    lineHeight: "2rem"
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, \"Segoe UI\", \"Helvetica Neue\", Arial, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: "1.5rem"
  tempo:
    fontFamily: "\"Iowan Old Style\", \"Charter\", \"Palatino Linotype\", Palatino, Georgia, serif"
    fontSize: "1.125rem"
    fontWeight: 700
    lineHeight: "1.75rem"
    letterSpacing: "0.005em"
  body:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, \"Segoe UI\", \"Helvetica Neue\", Arial, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: "1.25rem"
    fontFeature: "\"kern\", \"liga\", \"tnum\""
  label:
    fontFamily: "ui-sans-serif, system-ui, -apple-system, \"Segoe UI\", \"Helvetica Neue\", Arial, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: "1rem"
  bar-number:
    fontFamily: "ui-monospace, \"SF Mono\", Menlo, Consolas, monospace"
    fontSize: "10px"
    fontWeight: 400
  urdu-text:
    fontFamily: "\"Noto Nastaliq Urdu\", \"Jameel Noori Nastaleeq\", \"Urdu Typesetting\", \"Noto Naskh Arabic\", ui-sans-serif, system-ui, sans-serif"
    lineHeight: 1.9
  urdu-control:
    fontFamily: "\"Noto Naskh Arabic\", \"Geeza Pro\", ui-sans-serif, system-ui, sans-serif"
    lineHeight: 1.3
rounded:
  sm: "4px"
  md: "6px"
  lg: "8px"
  xl: "10px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  card: "20px"
  lg: "24px"
  xl: "40px"
components:
  button-primary:
    backgroundColor: "{colors.conductor-blue}"
    textColor: "{colors.sheet}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  button-primary-hover:
    backgroundColor: "{colors.conductor-blue-deep}"
  button-quiet:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  button-quiet-hover:
    backgroundColor: "{colors.paper}"
  segment-selected:
    backgroundColor: "{colors.conductor-blue}"
    textColor: "{colors.sheet}"
    rounded: "{rounded.md}"
    padding: "8px 12px"
  segment-idle:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink-soft}"
    rounded: "{rounded.md}"
    padding: "8px 12px"
  field:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: "8px 12px"
  card:
    backgroundColor: "{colors.sheet}"
    rounded: "{rounded.xl}"
    padding: "{spacing.card}"
  rail:
    backgroundColor: "{colors.score-navy}"
    textColor: "{colors.score-mist}"
    width: "15rem"
  rail-link-active:
    textColor: "{colors.sheet}"
    rounded: "{rounded.md}"
    padding: "8px 12px"
  achievement-earned:
    backgroundColor: "{colors.brass}"
    textColor: "{colors.ink-night}"
    rounded: "{rounded.full}"
    size: "36px"
---

# Design System: SmartSpeaking

## Overview

**Creative North Star: "The Engraved Score"**

A talk is a performance read like a conductor's score: tempo, rests and dynamics marked against time. The app is set like a well-engraved orchestral part. A deep score-navy rail holds the instrument list (the navigation); the main sheet is cool paper with a faint blue cast, ruled in hairlines, printed in ink. Information is dense and exact, the way a score is: tabular figures, small radii, no ornament that does not mean something.

The world refuses the category default of grey cards with a blue button and a gamified confetti layer. There is one action color (conductor blue), one reward color (brass, rationed to things the speaker earned), and one decorative voice (the bold italic serif tempo marking). Everything else is ink on paper. Musical notation is the native visual language, not a theme applied on top: sessions are staves, issues are note heads on their category's line, weekly goals are a measure of beats, pauses are breath marks, caesuras and fermatas, and pace is named Adagio to Presto.

The whole system runs on system fonts and inline SVG. Nothing is downloaded at runtime, light and dark follow the OS, and the same score reads in English, German and right-to-left Urdu.

**Key Characteristics:**
- Navy score rail, paper sheet, ink text; hairline borders instead of shadows.
- Conductor blue marks actions and the current place, and nothing else.
- Brass appears only on earned things: met weekly measures, streak days, earned achievements.
- Notation as data: staves, bar lines, note heads, ties, breath marks and tempo words carry real values.
- Bold italic serif tempo markings are the only display voice; all other type is the system sans with tabular figures.
- System font stacks only, including Nastaliq for Urdu text and Naskh for Urdu form controls.

## Colors

Ink on cool paper, a navy shell, one blue for action, one rationed brass for reward, and seven category hues that only ever appear on the stave and its marks.

### Primary
- **Conductor Blue** (conductor-blue): primary buttons, selected segments and tabs, links, the playhead, the latest note head on the trend stave, progress fills, focus rings (bright variant), caret and native control accents. Hover deepens to Conductor Blue Deep. Conductor Blue Wash tints an active drop zone.

### Secondary
- **Score Navy** (score-navy): the app rail, the sign-in panel and the live prep overlay. Score Navy Raised fills controls sitting on the rail (the language picker). Score Mist is the rail's resting text; Score Mist Light carries tempo markings set on navy.

### Tertiary
- **Brass** (brass, brass-deep, brass-light): earned things only. A met weekly measure turns its note heads brass with a brass-deep stroke; practiced days in the streak calendar are brass squares; earned achievement badges are brass discs with ink-night icons on a brass-light tinted card.

### Category Hues (the stave's voices)
- **Voice Violet, Pacing Sky, Language Amber, Pronunciation Rose, Eye-contact Emerald, Posture Orange, Body-language Teal**: one hue per feedback category, used on the session stave's note heads and ties, its legend, and the matching transcript highlights (filler amber, hedge violet, repetition sky, mispronounced rose). Dark mode lifts each to its 400 step.

### Neutral
- **Paper** (paper): the page ground in light mode.
- **Sheet** (sheet): cards, fields and quiet buttons sitting on paper.
- **Hairline** (hairline): card borders and list dividers.
- **Rule** (rule): stave lines, field and quiet-button borders, scrollbar thumbs.
- **Ink Muted** (ink-muted): secondary text, labels, axis figures.
- **Ink Soft** (ink-soft): idle segment text and tempo markings on paper.
- **Ink** (ink): body text in light mode; past note heads.
- **Ink Night** (ink-night): the dark-mode page ground; text on brass.

### Named Rules

**The Earned Brass Rule.** Brass marks only something the speaker achieved (a met goal, a practiced day, an earned badge). It is never an accent, a warning, a hover or a highlight.

**The One Baton Rule.** Conductor blue is the only action and current-place color. Selected state is a solid blue fill with white text; idle state is ink on sheet with a rule border. No second action hue.

**The Staff Stays on the Staff Rule.** Category hues belong to issue marks on the stave, its legend and transcript highlights. They never color buttons, headings or panels.

## Typography

**Display Font:** none; headings use the system sans at weight 600.
**Body Font:** system sans (ui-sans-serif, system-ui, -apple-system, Segoe UI, Helvetica Neue, Arial).
**Tempo Font:** Iowan Old Style, Charter, Palatino, Georgia, set bold italic.
**Mono:** ui-monospace, SF Mono, Menlo, Consolas, for bar numbers and transcript timestamps.

**Character:** a plain, exact engraver's sans for everything that is read, and one bold italic serif voice for the markings a conductor would write above the stave.

### Hierarchy
- **Display** (600, 1.5rem, tight tracking): page titles. The sign-in pitch rises to 1.875rem.
- **Headline** (600, 1rem): card and section headings; sizes stay flat, weight carries rank.
- **Tempo** (bold italic serif, 1.125rem; up to 2.25rem for the streak count and 1.875rem on sign-in): tempo words (Adagio, Andante, Moderato, Allegro, Vivace, Presto) above the session stave, under the live pace gauge and on the dashboard; the streak number; the prep marking on the live overlay.
- **Body** (400, 0.875rem): controls, lists, transcript and most running text.
- **Label** (500, 0.75rem, ink-muted): field labels, legends, footnotes. Sentence case, no tracking.
- **Bar number** (mono, 10px, ink-muted): time labels above stave bar lines.

### Named Rules

**The Tabular Figure Rule.** Every number that can change or be compared (scores, words per minute, counts, times, table cells) is set with tabular figures.

**The Single Marking Voice Rule.** The tempo serif is reserved for musical markings and the streak count. Headings, buttons and labels are always the sans.

**The Script Fits the Control Rule.** Urdu text is set in Nastaliq at line height 1.9; Urdu inputs and selects switch to Naskh at line height 1.3 so one-line controls fit. Mono and tabular spans fall back to the sans in Urdu. All are system faces; none is fetched.

## Layout

Desktop is a two-column score: a sticky 15rem navy rail (wordmark, five nav links, language picker, account line, privacy line) and a main sheet capped at 72rem with 40px side padding and 40px top padding. Below the large breakpoint (1024px) the rail becomes a top bar: wordmark and language picker on one row, the nav as a horizontally scrolling row with its scrollbar hidden, and sign-out and privacy move to a hairline footer at the end of the main column (16px gutters, 24px from 640px).

Rhythm is tight and engraved: 20px inside cards, 16px and 24px between cards, 8px between controls in a group. Grids are content-led: dashboard trends at 3fr/2fr from 1280px, live practice as video plus an 18rem side column, the session report in two equal columns, settings and upload as a single 42rem column. Sign-in splits 1.1fr navy panel to 1fr form (form capped at 24rem); on phones only the form shows.

Right-to-left Urdu mirrors the shell with logical properties, but every timeline, chart, gauge, stave and number group is pinned left-to-right, because time and scales run left to right on a score.

## Elevation & Depth

Flat. Depth is tonal and ruled: paper ground, sheet panels outlined by a hairline, the navy rail as the one dark plane. The primary button carries a barely-there 1px contact shadow so it reads as pressable; the active rail link is marked by a light fill and a 1px inset white hairline, not a lift.

### Shadow Vocabulary
- **Contact** (`box-shadow: 0 1px 2px rgb(0 0 0 / 0.12)`): primary buttons only.
- **Rail hairline** (`box-shadow: inset 0 0 0 1px rgb(255 255 255 / 0.08)`): the active link on the navy rail.

### Named Rules

**The Hairline-Not-Shadow Rule.** Panels separate from paper by a 1px hairline border and a white sheet, never by a drop shadow.

## Shapes

Small, quiet radii: 6px for buttons, fields, segments and rail links; 10px for cards, list panels, video frames and the drop zone; full circles for achievement discs, goal status dots and progress tracks. The only other recurring shapes are notational: tilted oval note heads (rotated -22 degrees, filled for major, open for minor, small dot for info), rounded ties for stretches over 1.5 seconds, thin bar lines and a heavy final double bar, and the five-line stave in the brand mark.

## Components

### Buttons
- **Shape:** gently squared (6px), 8px by 16px padding, 0.875rem medium text, 150ms color transition, 50% opacity when disabled.
- **Primary:** conductor blue with white text and the contact shadow; hover deepens to conductor-blue-deep.
- **Quiet:** sheet background, ink text, rule border; hover darkens the border and tints to paper. In dark mode, ink-night sheet with a dark border.
- **Outline action:** a conductor-blue border with blue text for a secondary live action.

### Segmented choices and tabs
- **Style:** rows of 6px-radius buttons. Selected is solid conductor blue with white text; idle is a rule border with ink text, or borderless ink-soft text with a paper hover for metric tabs. Used for live mode, target length, upload options, model presets and trend metrics.

### Cards / Containers
- **Corner Style:** 10px.
- **Background:** sheet on paper (ink in dark mode on ink-night).
- **Shadow Strategy:** none; see Elevation.
- **Border:** 1px hairline.
- **Internal Padding:** 20px (16px for the stave card and live side panels).

### Inputs / Fields
- **Style:** full-width, sheet background, rule border, 6px radius, 8px by 12px padding, ink-muted placeholder.
- **Focus:** border turns conductor-blue-bright and the global 2px conductor-blue-bright focus ring sits 2px outside. Caret and native accents are conductor blue.
- **Error:** a red-700 alert line under the form; no red border treatment.

### Navigation
- **Rail:** score navy, 15rem, sticky full height on desktop. Links are 0.875rem medium with an 18px line icon, score-mist at rest, a faint white wash on hover, and a light fill with an inset hairline plus white text when current. On phones it becomes a scrolling row in the top bar.

### Icons
- Inline line icons on a 24px grid, 1.75 stroke, round caps and joins, drawn in currentColor. Nothing from an icon font or package.

### Session Stave (signature)
The session timeline is a five-line stave in a card: bar lines at a computed bar length (5 to 300 seconds, at most about 14 bars) with mono bar numbers as time, a heavy final double bar, and each category on its own line or space. Issues are tilted note heads in their category hue; long stretches carry a translucent tie. Prompt markers are blue diamonds and notes are ink-ringed squares above the stave. A conductor-blue playhead runs down it. A tempo marking with words per minute is set above, and a note-head legend sits below. Hover or focus reads the issue aloud through a polite live region; clicking seeks.

### Trend Stave
Session trends are drawn as five staff lines across the value range with a light bar line per session and a final double bar. Each session is an ink note head joined by a thin ink line; the latest is conductor blue. A target band is a 12% emerald wash.

### Weekly Measure
The weekly goal is one measure: five lines, a bar line at the start, a double bar at the end, one note head per beat. Done beats are ink heads, remaining beats are open; when the goal is met every done head turns brass.

### Pause Marks
Transcript pauses use notation: a breath mark (comma) in emerald for a good pause, a caesura (two slashes) in amber for a hesitation, and a fermata in red for a long silence.

### Pace Gauge
A half-circle gauge with sky (slow), emerald (in range) and amber (fast) zones, an ink needle that eases over 700ms, the words-per-minute figure in the zone color, and the tempo marking beneath it.

### Achievements
A 2 to 5 column grid of compact rows: a 36px circular badge and the title. Earned rows get a brass-light border and tint and a brass disc with an ink-night icon; unearned rows are neutral with a thin conductor-blue progress track.

## Do's and Don'ts

### Do:
- **Do** draw time-based data as notation: staves, bar lines, note heads, ties and tempo words, each carrying a real value.
- **Do** keep conductor blue for actions, selection, links, focus and the current place.
- **Do** keep brass for things the speaker earned and nothing else.
- **Do** separate panels with a 1px hairline on a sheet over paper, 10px corners.
- **Do** set every comparable number in tabular figures and every tempo marking in the bold italic serif.
- **Do** use system font stacks only, with Nastaliq for Urdu text and Naskh for Urdu controls.
- **Do** pin charts, staves, gauges and number groups left-to-right inside right-to-left layouts.
- **Do** follow the OS for light and dark, and stop decorative animation under reduced motion.

### Don't:
- **Don't** use drop shadows to lift cards or panels.
- **Don't** add a gamified confetti layer, or use brass, amber or category hues as general decoration.
- **Don't** introduce a second action color or color buttons with category hues.
- **Don't** set headings, buttons or labels in the tempo serif.
- **Don't** fetch fonts, icons or images at runtime, or pull in an icon package.
- **Don't** set Urdu form controls in Nastaliq; it overflows one-line fields.
