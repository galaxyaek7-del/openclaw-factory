# Arms exercise (2026-11-06T14:47:55+00:00)

Each arm's engine was run on real or recorded inputs, read-only. WORKS means the output was produced and checked; it says nothing about demand.

| Arm | Result | Evidence |
|---|---|---|
| Digital Products | WORKS | `{"products": 126, "published": 119, "verified_public": 118, "sales": 0, "note": "listing, delivery and measurement work; no buyer yet"}` |
| Micro-B2B: spreadsheet normalization | WORKS | `{"rows_in": 13, "rows_out": 12, "rows_expected": 12, "qa_report_keys": ["rows", "qa"]}` |
| Micro-B2B: feed preflight | WORKS | `{"summary": {"status": "CHECKED", "rows": 12, "errors": 10, "warnings": 3, "rows_with_errors": 8, "rows_clean": 4}, "findings_keys": ["status", "rows", "errors", "warnings", "rows_with_errors", "rows_clean"], "reproduces_the_stored_demo_report": true}` |
| Research & Data: data products | WORKS | `{"releases_revalidated_today": {"eaa-penalty-register@2026-10-31.2": {"status": "PASS", "findings": 0}, "gf-public-catalog@2026-10-29": {"status": "PASS", "findings": 0}, "uspto-trademark-fees@2026-10-29": {"status": "PASS", "findings": 0}}}` |
| Affiliate Intelligence (simulation) | WORKS | `{"simulated_scenarios": 46, "passed": 46, "failed": 0, "environment": "SIMULATION (temp dir, synthetic SIM- ids)", "note": "SIMULATION: no real program, link, click or commission exists"}` |
| Content & Distribution | WORKS | `{"telegraph_readings_recorded": 23, "last": {"timestamp": "2026-11-06T00:03:54.621436+00:00", "views": {"gpsr_takedown": 23, "homebuyer_method": 20, "homebuyer_credit": 20, "landlord_movein": 13, "cottage_food": 14, "b2b_batch": 18, "restaurant_foodcost": 12, "dental_verify": 15}, "views_status": {"` |
| AI Operations: automation health audit | WORKS | `{"exit": 0, "verdicts_seen": ["FAILING", "INACTIVE", "OK", "STALE", "UNKNOWN"], "output_chars": 2167}` |
| Productized AI: accessibility check | WORKS | `{"own_site": {"pages_checked": 141, "pages_with_errors": 0, "errors": 0, "warnings": 6}, "detection_proof": "the deliberately flawed synthetic page yields 11 finding(s): the checker can see defects", "top_issues": {"page has no h1 (WCAG 1.3.1)": {"pages": 3, "occurrences": 3}, "heading level skipped` |
| Children's Media Studio | WORKS | `{"episodes": [{"episode": "ep01_nunu_little_bridge", "failing": ["approval", "credentials"]}, {"episode": "ep02_lulus_lost_ball", "failing": ["approval", "credentials"]}], "meaning": "every technical check passes; only the founder's approval and YouTube credentials are missing"}` |
| Umrah assistant (Phase 2) | WORKS | `{"assistant_tests_pass": [true, true], "data": "SIMULATION agency data; no real agency yet"}` |
