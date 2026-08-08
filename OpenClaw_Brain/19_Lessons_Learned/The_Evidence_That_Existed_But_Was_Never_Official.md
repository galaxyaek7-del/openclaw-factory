# The Evidence That Existed But Was Never Official

## The mistake

`commission_engine.py::_derive_verification_status()` promoted a commission opportunity to `VERIFIED` the moment *any* evidence URL was recorded against it — a terms link, a program page, a blog post mentioning the program, anything non-empty. The function never asked *whose domain the evidence actually lived on*.

## The consequence

Two real opportunities (Creative Market, Canva) had real evidence recorded — but every citation was a third-party blog or aggregator describing the program secondhand, never the partner's own official page. Both were sitting at `VERIFIED` on the strength of hearsay. Conversely, several opportunities that genuinely did have official terms pages linked (via a `terms_url` field that had been captured but never actually read by the derivation function) were sitting at a lower status than they'd earned. The company's own confidence signal was, in both directions, disconnected from what the evidence actually was.

## How it was found

Phase 35's own external cross-check (a handful of deliberate `WebFetch` calls against the partner programs' real pages) surfaced two live discrepancies (Zapier's real page describes a different program shape than what was recorded; Google Workspace's real page shows a different commission structure) — investigating *why* those had gone unnoticed traced back to the derivation function accepting any evidence as equally trustworthy.

## The fix

`categorize_evidence_source()` (`partner_intelligence_agent.py`) + a new `PARTNER_DOMAIN_MAP` (19 platform → real domain) let `_derive_verification_status()` check whether a piece of evidence's URL actually resolves to the partner's own domain. Official-domain evidence earns `VERIFIED`; evidence that exists but is entirely third-party earns the new, honest `THIRD_PARTY_ONLY` status instead of being blended into the same bucket as the real thing.

## The generalizable lesson

**"Evidence exists" and "evidence is authoritative" are two different claims, and a verification system that only checks the first one is measuring the wrong thing.** A confidence label is only as trustworthy as the weakest link in what it silently assumes about its inputs — here, that any non-empty URL was as good as any other. The fix cost one new dict and one new domain-matching function; the bug had been silently inflating trust in company data since the very first version of this scoring function.
