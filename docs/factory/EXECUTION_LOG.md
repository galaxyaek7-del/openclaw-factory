# Execution log

Newest first. One line per meaningful step; details live in commits and reports.

- 2026-10-29 17:05Z: CI group (a) passes on Linux again (run 40917097622) after the second guard fix (`681eaec`): the guard's "real" isdir/exists went through the guarded os.stat on POSIX, so an overlay-only folder (niche_reports) looked live and os.listdir failed. Found by the grouped CI annotations (`c6dbe02`), which name each distinct failure with its file:line.
- 2026-10-29: listing repairs prepared and dry-run (`scripts/apply_listing_repairs_20261029.py`): trademark kit gets the promised tracker (fee sheet rebuilt on the USPTO schedule, read 2026-10-29) and a guide with a dated fee-correction page (statement of use $150, extension $125; the guide said $200-250 and $225); GPSR kit gets the promised cost planner; 27 listings drop "and this guide.". Live run refused to the agent by the tool's safety classifier; founder runs it (`docs/factory/FOUNDER_ACTIONS.md`).
- 2026-10-29: storefront catalogue 100 -> 107 (B16-001..007), dashboard decision queue derived from files, 30 of 39 archives verified byte-for-byte against their built bundle (9 older ones unknown).

- 2026-10-29: commercial-engineering directive (GF-100K-S3). Live publishing stopped: the scheduled B16-008..010 publish was cancelled before it ran (stricter rule wins); `FACTORY_LIVE_PUBLISH=false` confirmed. Live reconciliation 16:02Z: Gumroad 0 transactions / $0, Paddle 403, Etsy/Payhip no credential.
- 2026-10-29: delivery audit (GET-only): 112 products, 109 published; 24 published listings deliver less than they describe (21 thin, 3 promise a spreadsheet not attached, 1 promises more files, 1 published without a file, 1 preview delivered). Founder decision; nothing changed on Gumroad. `reports/GUMROAD_DELIVERY_AUDIT_2026-10-29.json`.
- 2026-10-29: first exposure reading in 20 days: 8 Telegraph articles, 130 platform-reported views (~121 net of own loads; not verified human visits); daily reading now in the loop (`distribution_metrics_daily.py`). Commercial funnel (15 states) and diagnosis on the dashboard (`lib/commercial_funnel.js`): A_OR_B_OR_C, visits unmeasured.
- 2026-10-29: EXP-B16-007-LI-01 prepared and recorded PENDING_APPROVAL (`docs/factory/EXPERIMENT_EXP-B16-007-LI-01.md`); nothing posted.
- 2026-10-29: CI red since 2026-10-28 traced to two causes and fixed in `30330e0`: write guard mishandled dir_fd paths (Linux rmtree), and `channels/publication_authorization.py` was imported by committed code but never committed.
- 2026-10-29: incident INC-680b5a7fa9ec: shared `lib/ceo_command_center.js` truncated by an in-place edit, restored byte-exact from the OpenCode snapshot store; procedure `docs/factory/SHARED_FILE_EDITING.md`.
- 2026-10-29: batch 16: ten Excel tools built (1,016 formula checks, 0 failures); B16-001..007 published and verified on Gumroad, B16-008..010 held; site pages for batch 15 (never committed before) and the seven live batch-16 tools published.

- 2026-10-23: correction: public site traffic is not measured (no receiver on GitHub Pages; recorded page views are probes). Earlier 'about ten visits a month' was wrong. B6 blocked on a founder-owned analytics account.
- 2026-10-23: B2 product registry (`product_registry.py`) live: 92 products, 89 PUBLIC_LISTING_VERIFIED by page check, drift reported; B3 daily loop step.
- 2026-10-23: Phase A baseline written (`docs/factory/`). Live reconciliation: 92 Gumroad listings, 0 sales, catalog misses only batch 14, canonical inventory matches 0 live ids. Next: B1 (paid files out of the public tree), then B2 (product identity registry + drift check).
- 2026-10-23: batch 14 (10 spreadsheet tools) built, 872 formula checks, published and verified on Gumroad; site pages, sitemap, IndexNow.
- 2026-10-23: agent runtime, six-agent daily chain, Sensing classifier, demand sensing, site auto-publish (site-only), IndexNow with keyLocation, service timeouts.
