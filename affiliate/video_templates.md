# Affiliate Video Templates (specs reusing the proven auto_draft pipeline)

The Systeme.io draft (`assets/affiliate/systeme_io/auto_draft/`) proved the
mechanics: approved script → single-pass edge_tts narration + word timings →
PIL scene cards (arabic_reshaper + bidi + Tahoma) → imageio-ffmpeg assembly →
SRT validation → secret scan → QA report. Templates below reuse those exact
steps; nothing here invents a second pipeline.

## Common spine (all templates)
1. Approved script in (text file, UTF-8). 2. Single-pass TTS + timings.
3. Scene cards per storyboard beats (simulations labeled illustrative, never
   live screens). 4. Proportional scene cuts off approved timing plans.
5. SRT from synthesis timings, monotonicity enforced. 6. Secret scan
   (zero token bytes). 7. QA: duration/streams/frames/subs/thumbnail.
8. Report file. No publish step exists in any template.

## T1 — Tutorial (proven)
Beats: hook → problem → system overview → step-by-step build → tool mention
+ disclosure → CTA + next steps. Reference: auto_draft (7 scenes, 464s).

## T2 — Comparison
Beats: problem → criteria table (spoken + card) → option A → option B →
verdict matrix → disclosure if affiliate links → CTA. Extra QA: every
compared fact needs a source line in the script; no winner declared without
stated criteria.

## T3 — Review / implementation guide
Beats: who-it-is-for gate (disqualify openly) → setup walkthrough →
evidence checklist → limitations → disclosure → CTA. Extra QA: limitations
section mandatory; absence = HOLD.

## T4 — Problem/solution + checklist + case-study
Beats: pain → cost-of-inaction (no invented numbers; ranges only with
sources) → method → worked example → checklist card → disclosure → CTA.
Extra QA: every number traced to a cited source or marked illustrative.

## Language rule
Arabic default (proven). English or others only with a native review gate
booked before production — never blind translation. Terminology validated
per language before TTS (a glossary file per language, reviewed once).
