# Video factory: quality evaluation

## Rubric (0-100, ten criteria x 10)

| # | Criterion | 10 means |
|---|---|---|
| 1 | Factual accuracy | every number and claim checked |
| 2 | Script clarity | one idea per scene, plain words, useful takeaway |
| 3 | Narration quality | natural, intelligible voice, good pacing |
| 4 | Audio technical | no clipping, no dead air, consistent loudness |
| 5 | Visual legibility | readable on a phone, strong contrast, nothing clipped |
| 6 | Visual engagement | motion and imagery that hold attention |
| 7 | Subtitles | exact text, synced, readable |
| 8 | Format fit | right aspect and length for the slot; strong opening |
| 9 | Policy and honesty | no misleading claims, disclosures present, no third-party marks |
| 10 | Technical integrity | decodes cleanly, standard codecs, hash recorded |

Gates independent of the score: rights must be CLEARED; criteria 1, 9 and 10 must each be at least 8; publication also needs a human listen. A publishable video should score at least 75.

## Scores (final renders, scored by Claude from measurements and frame review; no human listen yet)

| # | Pilot A | Pilot B | Basis |
|---|---|---|---|
| 1 | 9 | 10 | B arithmetic test-checked; A general principle, "30 to 60 days" phrased as "often" |
| 2 | 8 | 8 | four scenes each, concrete steps |
| 3 | 4 | 4 | Zira is an older robotic SAPI voice; intelligibility not measured |
| 4 | 9 | 9 | mean -20 dB, peak -2 dB, no silence > 1.5 s |
| 5 | 8 | 8 | large type after repairs; landscape still has space on the right |
| 6 | 3 | 3 | text-and-shapes only, slow zoom; no imagery or animation |
| 7 | 9 | 9 | exact text, measured sync <= 50 ms; some cues are three lines |
| 8 | 6 | 7 | A: no visual hook in the first second; B: fits an explainer |
| 9 | 9 | 9 | B has the "not financial advice" line; synthetic voice disclosed |
| 10 | 10 | 10 | verifier PASS, hashes recorded |
| **Total** | **75** | **77** | |

Verdict: technically sound, honest, useful as internal demonstrations of the pipeline. Not publishable: rights UNRESOLVED (gate) and narration/engagement weak (criteria 3 and 6). These are slideshow-style explainers; they are not presented as animation.

## Score history

v1 (before repairs) would have scored lower on 5 (small text, top-heavy layout), 7 (subtitles stayed about 750 ms after speech) and 8 (slow pacing, 50.5 s / 62.6 s): see the repair log.
