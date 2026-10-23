# Digital product taxonomy

A map of opportunities, not a production plan. "Capability" is what the factory can produce and verify today: **EXISTS** (built and shipped), **PARTIAL** (generator or QA exists, not both), **NONE**.

Platform note for every row: Gumroad sells downloadable files, memberships and license keys; before the first listing in any new category, check Gumroad's current terms of service and prohibited-products list for that category (software, AI services, subscriptions, third-party assets). Not yet verified for categories marked NONE.

## QA adapters (shared by many categories)

| Adapter | Checks | Exists today |
|---|---|---|
| Spreadsheet | opens; formulas present; every key cell recalculated by `lib/xlsx_eval.py` and matched to an independent model; number formats; protected formulas; example data | yes (`file_testing_engine`, `lib/xlsx_eval.py`, `books/_batch14_src/run.py`) |
| PDF / e-book | text extraction finds title and disclaimer; page count; rendered pages inspected (PyMuPDF); claims match numbers | partial (batch 14 runner; `inspectors.py` for books) |
| Document template (docx) | opens; headings; no placeholders left | partial (cohort builds) |
| Automation (n8n JSON) | valid JSON; node types exist; credentials as placeholders; import test on a local n8n | no |
| Software / script | install from clean env; tests; no secrets; license file | no |
| Research / data | sources with dates; claim-by-claim evidence; schema validation; duplicates; privacy | partial (evidence engine, market evidence) |
| Creative asset | file integrity; preview renders; originality and licence record | no |
| Educational | objectives; answer keys consistent with exercises; age suitability | no |
| Bundle | manifest lists every file; hashes; cross-file consistency | yes (zip + manifest hash in batch 14) |

## Categories

| # | Category | Format | Adapter | Capability | Notes |
|---|---|---|---|---|---|
| 1-5 | E-books, practical guides, workbooks, courses, professional references | PDF, docx, xlsx | PDF, spreadsheet | EXISTS (guides, workbooks) / NONE (courses) | 79 earlier listings are mostly guides; ~20 found thin |
| 6-10 | Language learning, lesson plans, children's resources, interactive stories, printable activities | PDF | PDF, educational | NONE | age-appropriateness review needed |
| 11 | Notion templates | Notion share link + PDF | template | NONE | delivery is a duplicate link |
| 12 | Excel / Google Sheets templates | xlsx | spreadsheet | EXISTS | batch 14 |
| 13 | Canva templates | Canva link | template | NONE | Canva template-sharing terms apply |
| 14-20 | Business documents, planners, presentations, project management, CRM, inventory, HR templates | docx, xlsx, pptx, PDF | template, spreadsheet | EXISTS (CRM, inventory, docx kits) / NONE (pptx) | |
| 21-30 | Pricing, break-even, cash flow, freelancer, budget, scenario, risk register, SOPs, reporting, dashboards | xlsx, docx | spreadsheet | EXISTS (21-25, 26 partial) | strongest current capability |
| 31 | AI prompt systems | PDF, txt | PDF | PARTIAL | low differentiation, many free alternatives |
| 32-33 | n8n workflow exports, automation packs | JSON | automation | NONE | needs local n8n import test; no credentials in files |
| 34-37, 40-42 | Software utilities, scripts, developer tools, API examples, plugins, data tools, code libraries | zip | software | NONE | licence and support burden |
| 38-39 | Website templates, UI kits | zip (HTML/CSS) | software, creative | NONE | |
| 43-56 | Icons, illustrations, fonts, brand kits, photos, backgrounds, brushes, presets, 3D, video, sound, music, animation | image/audio/video files | creative | NONE | originality and licence record mandatory; fonts/music only with full rights |
| 57-66 | Market reports, competitor reports, directories, databases, synthetic datasets, research briefs, comparisons | PDF, CSV | research, data | PARTIAL (research tooling exists) | every claim dated and sourced; privacy for directories |
| 67-75 | Article templates, copy frameworks, content calendars, script templates, newsletters, writing workbooks, YouTube resources, children's stories | docx, xlsx, PDF | template, PDF | PARTIAL | |
| 76-82 | Bundles, tiered editions, libraries, subscriptions, recurring research, updates, project kits | mixed | bundle | PARTIAL (bundles) | tiers must differ in real features |

## Selection rule

A category is worth entering when all are true: a specific buyer with a recurring problem; evidence that people pay for it (not only competitor asking prices); a meaningful advantage over free alternatives; a QA adapter that can verify it; and delivery Gumroad supports. Given R1 (no traffic), prefer categories where the factory can also produce search-intent pages that bring visitors.
