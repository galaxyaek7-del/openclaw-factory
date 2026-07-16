"""
OpenClaw Factory — Real Market Evidence Engine (ADR-058).

Requirement: replace ESTIMATED competition/profit with VERIFIABLE
evidence, never fabricate, "Unknown" when data cannot be verified.

Hard boundary, stated plainly: this factory has no free, legal,
automated Amazon API of any kind, and none is built here. The only real
Amazon data source this factory has EVER had is niche_validator_v2.py's
deliberately offline, manual mechanism — a human saves a real Amazon
search-results page via their own browser (Ctrl+S), and the script
parses that saved HTML locally. Zero live scraping, zero API cost, zero
risk to the Amazon account (niche_validator_v2.py's own docstring).
Building automated live Amazon scraping would violate Amazon's Terms of
Service and this factory's own explicit "zero risk to Amazon account"
principle — a real, deliberate boundary, not an oversight, and not
something this engine crosses.

evidence_collector.collect_evidence(niche) sources exclusively from
profit_oracle._find_niche_report() — the exact same real saved-report
lookup profit_oracle.py's own _score_competition()/_score_margin()
already use (ADR-041/042) — never a second implementation of that
lookup. This engine does not change profit_oracle.py's scoring logic;
that "prefer real evidence over an estimate when it exists" mechanism
has existed since ADR-041/042. This engine exposes that evidence in the
structured contract requested (source/timestamp/confidence/raw_value/
normalized_value/explanation) and reports honestly when none exists.

Confirmed directly, 2026-07-16: niche_reports/ is empty — zero saved
Amazon reports exist in this factory today. Every one of the 10
requested metrics will therefore honestly report UNKNOWN for every real
niche evaluated today. That is the correct answer, not a bug — and 4 of
the 10 metrics (Best Seller Rank, marketplace age, update frequency,
seller concentration) are structurally UNKNOWN even WITH a saved report,
because a single search-results-page snapshot never captures them
(revenue indicators are UNKNOWN unconditionally — Amazon never makes
real sales figures publicly observable, saved page or not).
"""
