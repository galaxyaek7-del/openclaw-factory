# BARRIER MAP — Galaxy Forge commercial execution (C65, 2026-10-10)
# One row per blocker. Status re-verified this cycle. Types: A=autonomous, B=founder, C=forbidden.

| ID | Arm | Evidence + exact cause | Type | Impact | Safe workaround | Next action | Verification | Status |
|---|---|---|---|---|---|---|---|---|
| BL-ZIP | Gumroad | files[] shows PDF only (122465B); v2 ZIP validated locally (manifest+sha256) but dashboard upload needs human session | B | Bundle unadvertised; $29 PDF-only sale unaffected | Sell PDF-only honestly (current) | Founder uploads ZIP (FOUNDER_BATCH #1) | get_product files[] shows 5 files | OPEN |
| BL-REDDIT | Reddit | Zero REDDIT_* keys in .env (scanned); no API/client; 2 drafts ready | B | No buyer conversations (highest-evidence channel idle) | None autonomous | Founder posts draft as self (FOUNDER_BATCH #2) | Reply visible publicly | OPEN |
| BL-GSC | Search Console | gsc_inbox/ has README only, no google*.html; guides unindexed (site:=0) | B | SEO $0 traffic | Telegraph (indexed domain, unproven for us) | Founder adds property + drops file (FOUNDER_BATCH #3) | GSC property verified | OPEN |
| BL-SMTP | Email outreach | Adapter real (outreach_adapter.py), OUTREACH_SMTP_* absent (code self-documents MISSING) | B | No 1:1 outreach at all | None (no consent basis for other senders) | Founder credential OR no-cold-email policy (FOUNDER_BATCH #4) | Test send to self | OPEN |
| BL-FORM-ACT | Lead forms | formsubmit ajax: "needs Activation" (proof response); Tier1-local + mailto cover | B | Pages leads delayed until click | Tier1 local works; mailto fallback live | Founder clicks emailed link (FOUNDER_BATCH #5) | Re-test acceptance | OPEN |
| BL-PADDLE | Paddle | webhook MISSING_SECRET x2; onboarding incomplete (worker-evidenced); product exists | B | $155 Paddle path dead; Gumroad iaiyt works instead | Sell via Gumroad (live $155) | Founder vendors.paddle.com onboarding (FOUNDER_BATCH #6) | checkout poll ready | OPEN |
| BL-X | X/Twitter | HTTP 402 credits depleted (ledger); manual browser post still possible | B(auth)/A(manual) | API publishing dead | Founder manual post (draft ready) | Founder manual post or leave isolated | Post URL | OPEN |
| BL-NOSTR-REACH | Nostr | 0/19 replies; 0/~500 topical notes; communities unsuitable (evidence) | A-hold | Channel exhausted | Halt gate holds; observe only | Re-enter only on reply/signal | Relay REQ counts | HOLD |
| BL-SEO-INDEX | Organic | Unindexed (expected, hours old); Mojeek no-submit (official) | A-wait | No search traffic yet | Telegraph indexed-domain hope; cross-links live | Wait crawl; re-check in days | site: queries | WAIT |
| BL-MEASURE-PAGES | Analytics | Pages static: no POST backend (405 proven); server localhost-only, no tunnel | A/B | Visits UNKNOWN on site | Telegraph counters (working); ref/UTM + sales poll | Founder public-API endpoint (optional, non-blocking) | Counter reads | PARTIAL |
| BL-FAKE-REVIEW | Trust | PROHIBITED: fabricated testimonials/reviews | C | None (must never do) | Honest 0-sales disclosures (live) | Never | N/A | SKIPPED-RULES |
| BL-SPAM | Outreach | PROHIBITED: bulk unsolicited, scraping PII, impersonation | C | None (must never do) | Consent-based forms + public value posts | Never | N/A | SKIPPED-RULES |
| BL-SELFBUY | Revenue | PROHIBITED: purchasing own product to fake a sale | C | None (must never do) | Real buyers only | Never | N/A | SKIPPED-RULES |

Autonomous work continues: counters/claims/sales/forms observation, trust audits, conversion assets, queue discipline.
