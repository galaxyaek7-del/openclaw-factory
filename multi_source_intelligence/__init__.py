"""
Galaxy Forge — Multi-Source Market Intelligence Layer (ADR-059).

Not a new engine, not a new decision engine, no acceptance threshold
touched, no fabricated confidence. The only objective: increase the
amount of REAL market evidence available, and report honestly on
exactly how much of it actually exists per source.

Ten connectors, one per requested source, each independently isolated
(one source failing never breaks another, never breaks the factory).
Real, working, free/keyless integrations exist for exactly three
sources today, confirmed directly before writing any code:
  - Hacker News (HN Algolia) — already real since ADR-042, reused here
  - GitHub (Search API) — already real since ADR-042, reused here
  - Stack Overflow (Stack Exchange API) — genuinely new, verified
    reachable (test call succeeded, 299/300 daily quota remaining) —
    free, keyless, no signup required

The other seven (Amazon, Etsy, Gumroad, Product Hunt, Reddit, Google
Trends, public search engines) each honestly report "unavailable" with
a specific, real, already-documented reason (no credentials in .env,
Amazon's ToS-driven manual-only mechanism, n8n Sensing Engine built but
not activated, etc.) — never invented, never silently omitted.

Per explicit instruction ("No production logic may change. Only improve
evidence quality."), this layer does NOT feed into profit_oracle.py's
scoring formula or decision_engine's acceptance logic. It is evidence
collection and coverage reporting only — coverage.py's Evidence Coverage
Score is the actual deliverable this phase measures success by, not any
change in accepted-opportunity count.
"""
