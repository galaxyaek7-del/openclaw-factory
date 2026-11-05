# الأدوات المساعدة والعقيدة التشغيلية (منقول من CLAUDE.md)

### Other Python utilities

- `market_analyzer.py` — Static niche scoring logic; called live via `POST /api/market-analyze` (`server.js`).
- `quality_doctor.py` and its `POST /api/qa-check` route were removed (Executive Intelligence Core, Round 7, 2026-07-29): the module was a confirmed-fake legacy prototype (found in the Strategic Phase audit, 2026-07-19) — every `_check_*()` method appended a fabricated "fix" string without regenerating/redrawing/repricing anything real, and `health_score`/`ready_to_publish` weren't derived from any real check. It had zero real callers (no UI button, no pipeline stage) even after being disclosed via a `warning` field, and the new directive's own explicit "no fake metrics" rule was the clean trigger to finally remove it rather than leave a known-fake module live. `ai_doctor.py` was already its real, non-fabricated replacement (EOS Phase 2, 2026-07-19). `inspectors.py`'s Dual Inspection remains the real, load-bearing QA gate every actual generated product is checked against.
- `cover_designer_v2.py` — The live cover-generation engine, imported by `book_generator.py`, `inspectors.py`, `profit_oracle.py`, and `server.js`. (An older `cover_generator.py` existed as an unwired Day-05 scratch script and was removed 2026-07-13.)
- `niche_validator_v2.py` — The live niche-validation engine (imported as `NICHE_VALIDATOR` by `book_generator.py`/`profit_oracle.py`). (An older `niche_validator.py` v1 existed, claimed a `/analyze-niche` endpoint that no longer exists in `server.js`, and was removed 2026-07-13.)
- `audit_seed.py`, `hive_logbook_generator.py`, `seed_english_book.py` — standalone CLI tools run manually, by design not imported by any other module ("Zero factory impact" per `audit_seed.py`'s own docstring; `seed_english_book.py`'s own docstring: "Standalone... Does NOT touch the live factory pipeline. Safe to run/delete."). `hive_logbook_generator.py` produced the real HiveNotes KDP product (`seeds/hivenotes/`) entirely outside the generic `book_generator.py` pipeline and outside `factory_loop.js`'s awareness. `seed_english_book.py` produced the real `seeds/morning-focus-journal-for-remote-workers-v1.docx` — it imports `book_generator._parse_sectioned_book` (read-only reuse) but nothing in the live pipeline calls it back; until this line was added (STRUCTURAL_DIAGNOSIS.md disease #11) its standalone status wasn't documented outside its own docstring and a bare filename in `ARMS_ARCHITECTURE_INPUT.md`'s tree snapshot.

### No scheduler exists

Nothing in this repo runs anything on a timer: `factory_loop.js` (the Golden Hunter loop) has no cron, no `package.json` script, and no CI workflow — it only runs when invoked manually (`node factory_loop.js`). It also does not auto-process Human-in-the-Loop approvals: it only counts files in `pending_review/queue/` and writes an alert to `NEEDS_REVIEW.md`; a human must run `scripts/process_approved_drafts.py` manually after approving a draft. Confirmed by full-repo audit, 2026-07-13.

### `index.html` encoding

The file is saved as **UTF-16 LE with BOM**. When reading or editing it, ensure your editor preserves this encoding, or the Arabic text and emoji will corrupt.

### Permanent Operating Doctrine (2026-10-19)

`OpenClaw_Brain/00_Governance/PERMANENT_OPERATING_DOCTRINE.md` is the operating doctrine for every cycle from Cycle 103 on — *how* a cycle is run and what proves it. It does **not** replace `MASTER_OPERATING_CONSTITUTION.md` (which stays the constitution and ADR index); the constitution wins on any overlap.

It is enforced by real modules and a single gate, not by prose:

| Layer | Module |
|---|---|
| Incident memory (15 fields, control must exist on disk) | `incident_memory.py` → `data/incident_memory.jsonl` |
| Claim vs. reality audit (critical/warning, unsupported rate) | `doctrine_review.py::audit_structured_claims()` |
| UNKNOWN protocol (OBSERVED/DERIVED/INFERRED/ESTIMATED/UNKNOWN/BLOCKED) | `operational_history.py`, `truth_first.py` |
| Handoff contracts (7 fields; BLOCKED needs a delay reason) | `handoffs.py` → `data/handoffs.jsonl` |
| Rework / cycle time | `cycle_metrics.py` → `data/cycle_metrics.jsonl` |
| Weak signals (3 signals, 2 independent groups, then review) | `weak_signals.py` → `data/weak_signals.jsonl` |
| Business arms (READY/PARTIAL/PLANNED/BLOCKED/REVENUE_VERIFIED) | `business_arms.py` |

Gate: `python scripts/check_doctrine.py` (exit 1 if any layer is outside its rule; read-only). Tests: `tests/test_doctrine_layers.py`. The seven release states (`BUILD_COMPLETE` → `FIRST_SALE_VERIFIED`) are never collapsed; `FIRST_SALE_VERIFIED` is the only definition of success and is currently zero. `REVENUE_VERIFIED` is structurally unreachable because no per-arm revenue attribution exists.
