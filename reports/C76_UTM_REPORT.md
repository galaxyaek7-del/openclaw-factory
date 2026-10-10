# C76 REPORT — UTM coverage audit + fix (2026-10-10)

1. number/timestamp: C76, 2026-10-10. Objective: measurement coverage (UTM on every buy link).
2. baseline: C75 (ZIP pending, states fresh).
3. attempted/completed: full-site Gumroad-link audit (74 tagged across 7 ref sources); found 5 bare links in 3 files (EU landing CTA x2, turo x2, mindfulness x1); fixed all with source-appropriate ref values; direct verification shows 100% tagged (remaining detector hits were regex artifacts).
4. files: modified [customer_site/eu-ai-act-compliance-toolkit.html, customer_site/turo-guest-dispute-toolkit.html, customer_site/guide-mindfulness-focus-for-founders.html]; created [reports/C76_UTM_REPORT.md].
5. tests: local file reads (direct ?ref= proof); claims re-check 0/0 both posts both relays.
6. published URLs: none new. 7. ZIP: still PDF-only.
8. distribution: none new (gates hold).
9. metrics: UTM 100% OBSERVED; claims 0/0; purchases 0 (cited); revenue $0; spend $0; window 2026-10-10.
10. blockers: unchanged 5+1; next: C77 conversion (tickets/forms watch).
