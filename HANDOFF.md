# HANDOFF — Galaxy Forge commercial ops (2026-10-11, context compaction point)

## Done (verified, on origin/main)
- 50 Gumroad listings live/honest/priced/tagged; storefront + guides + lead forms (3, E2E-proven) live on Pages.
- Trust fixes: freelancer $39-bundle-mismatch -> $19; B2B terms reconciled; titles cleaned.
- Kit v2 bundles built (Etsy + Freelancer, READY-TO-ATTACH, founder dashboard).
- Distribution live: 10 Nostr posts (0 replies, HALTED on evidence), 9 Telegraph pages metered (~120 views unattributed),
  SEO guides indexed-NO (GSC gated), 4 pending-review drafts (human identity).
- Infra: server (express 5.3.0) + loop + n8n (2.25.7, rescued after failed upgrade) all alive; deps renewed
  (reportlab 5.0.1, pypdf 6.20.0); dotenv major + pdfkit held with reasons.
- First-Buyer-Free rule ACTIVE (policy file + storefront banner + 2 Nostr free posts, 0 claims).
- Revenue $0 (live APIs), spend $0. Queue: data/gf33_acquisition_queue.jsonl (180+ lines, valid JSON).
- Mission record: data/gf54_mission_record.json. Founder asks: reports/FOUNDER_BATCH.md (6 steps).

## Blocked (all founder-side)
- Bundle attach, Reddit identity, GSC click, SMTP credential/decision, formsubmit activation click, Paddle onboarding.

## Useful commands (no secrets)
- Health: curl localhost:3000/health | python -c json parse
- Sales: python Temp/opencode/gumcheck.py (Gumroad /v2/sales)
- Telegraph views: per-file scripts Temp/opencode/tgviews*.py (token OUTSIDE repo, Temp only)
- Gumroad admin: Temp/opencode scripts use channels.gumroad_arm (update/get; never delete)
- Verify push ONLY via: git log origin/main --oneline -1 (never output text)
- Workers: server PID~6004-era, loop PID 13104-era, n8n main+runner (Get-Process node)

## Standing rules (from mandates)
- No fake buyers/reviews/sales; no spam/impersonation/scraping; $0 spend.
- No new broadcast without new variable + observable counter (halt gates hold until signal).
- No test-submit to lead forms (founder noise + fake leads); synthetic tests to LOCAL endpoint only, labeled.
- No touching live n8n workflows (ADR-045 precedent: founder-authorized procedure only).
- Never kill healthy workers for supervision; engage supervisor only on natural restart.
- Never create accounts; never bypass auth; tokens never committed.
