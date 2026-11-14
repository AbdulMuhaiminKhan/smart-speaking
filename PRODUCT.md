# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
People who want to get better at speaking out loud: students preparing presentations, job seekers rehearsing interviews, professionals pitching, and Toastmasters-style club members. They practice alone at a desk with a laptop camera and microphone, usually in short sessions (one to ten minutes), then review a report. (Inferred from the brief and the app; not confirmed in an interview.)

## Product Purpose
SmartSpeaking is an AI public speaking coach. It records a talk live or from an uploaded video and measures voice, pace, filler words, language, pronunciation, eye contact, posture and gestures, then gives timestamped feedback, drills and progress over time. Success is a speaker who practices regularly and can see measurable improvement session to session.

## Positioning
Everything runs on the user's own computer with open-source models: no recording, transcript or metric leaves the machine, and nothing is paid for. Feedback is grounded in measured metrics with timestamps, and the AI coach may only state facts the measurements support.

## Operating Context
Docker Compose on the user's Mac (OrbStack), served at http://localhost:8080; Ollama runs natively for the AI coach. Typical loop: pick a practice mode (free talk, timed pitch, script rehearsal with teleprompter, impromptu, elevator pitch, interview Q&A, Table Topics), record with live feedback, read the report, replay the video with pinned notes, export a PDF, and check the dashboard for trends, streaks, goals and achievements.

## Capabilities and Constraints
- Languages: English, German and Urdu, for both the interface and the speech analysis. Urdu is right to left.
- Must be free and local: no paid APIs, no cloud services, no fonts or assets fetched at runtime from third parties.
- No new npm dependencies can be installed in this environment; UI is React + Vite + TypeScript + Tailwind CSS v4.
- Light and dark themes follow the operating system.
- Camera-based and pronunciation results are estimates and must be labelled as such.

## Brand Commitments
Name "SmartSpeaking". No logo or palette has been made binding. (Inferred: none found in the repository.)

## Evidence on Hand
No testimonials, customers or benchmarks exist; none may be invented. Demonstration content in development uses a synthetic test recording (backend/tests/fixtures/sample_speech.mp4).

## Product Principles
1. Private by construction: say so plainly and never weaken it.
2. Every judgement is backed by a measurement and a moment in the recording.
3. Coaching, not grading: show what to do next, not only what went wrong.
4. Practice should be quick to start and pleasant to come back to.
5. Equal quality in every supported language, including right-to-left Urdu.

## Accessibility & Inclusion
Readable in three languages and two scripts; respects reduced motion; colour is never the only signal for good, close and needs-work states.
