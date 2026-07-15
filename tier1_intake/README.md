# tier1_intake/ — Golden Hunter Tier-1/2 real candidate research

**Status:** Research batch #1 completed 2026-07-15 (per `GOLDEN_HUNTER_V2_STRATEGY.md` §5.3's explicit commitment: run one real research batch, validate against `opportunity_score()`, *before* writing any `market_hunter_tier1.py` code). **Result: the validation failed — not because no good candidates exist, but because `opportunity_score()`'s tier1 gate cannot reject anything.** See `OpenClaw_Brain/00_Governance/ADR-035-tier1-gate-not-discriminating.md` for the full finding. `market_hunter_tier1.py` is NOT built as a result — building it now would wire a real candidate source into a gate that rubber-stamps almost any input, recreating the exact "looks like real market intelligence, isn't" disease this whole audit started from.

## How this batch was produced

Real HTTP calls, not fabricated data: Hacker News Algolia API (`hn.algolia.com/api/v1/search_by_date`, keyless, matches `GOLDEN_HUNTER_V2_STRATEGY.md` §2's approved source) and GitHub Search API (`api.github.com/search/repositories`, keyless for search). Each candidate in `candidates/*.json` cites the real post/repo it's derived from (title, points/stars, url, date) — verifiable by re-fetching those URLs.

## Candidates and their real opportunity_score() result (tier1)

| # | Candidate niche | Source signal | opportunity_score (tier1) | Accepted? |
|---|---|---|---|---|
| 1 | AI Agent Blueprint for SOC 2 Compliance Automation | HN Show HN, Screenata/compliance-automation | 81.6 | true (meaninglessly — see ADR-035) |
| 2 | AI Agent Blueprint for Legacy Software API Modernization | HN Show HN, legacy-use.com, 15 pts (highest in batch) | 81.6 | true |
| 3 | AI Agent Blueprint for Industrial PLC Data Integration | HN Show HN, limenedge.com | 81.6 | true |
| 4 | AI Agent Blueprint for Small SaaS CloudOps Automation | GitHub nudgebee/nudgebee, 378 stars | 81.6 | true |
| 5 | AI Agent Blueprint for Freelance Security Pentesting Automation | HN Show HN, exfault.com | 81.6 | true |

All five identical at 81.6/100 despite completely different real-world evidence strength (15 HN points vs 378 GitHub stars vs 2 points) — proof the scorer isn't using any of the real signal gathered, only shallow niche-string keyword/word-count patterns. A control test (niche = the single character `"x"`) also scored 76.4 and was "accepted" at tier1. Full root-cause math in `ADR-035`.

## What to do with this research

The candidates themselves are real and plausible (vertical, unglamorous B2B automation niches matching the exact pattern `GOLDEN_HUNTER_V2_STRATEGY.md` §2 identified as trending: compliance, legacy modernization, industrial ops, CloudOps, security). Don't discard them — once `ADR-035`'s gate-calibration question is resolved, re-score all five against the corrected gate as the real first test of whether the fix works before building any pipeline on top of it.
