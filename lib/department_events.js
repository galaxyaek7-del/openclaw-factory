// Department Events (EOS Phase 2, Round 2, 2026-07-19) — the formalized,
// shared JSONL correlation-index envelope this factory's Department
// Collaboration design (COMPANY_INTEGRATION_MAP.md) settled on instead
// of a pub/sub bus (zero EventEmitter/observer code exists anywhere in
// this repo, and CLAUDE.md's own "no scheduler" stance exists
// specifically to keep every side effect deliberate — a live bus would
// be the single biggest culture violation available in this milestone).
//
// Emitted at the SAME call site as each real existing writer — never a
// re-derivation scan (the anti-duplication guarantee: a scan job would
// be the actual duplicate-store risk). No business data is ever
// duplicated here — only IDs and a one-line summary; a reader follows
// ref_id/source_log back to the real record in its own real log.
//
// Twelve department slots exist; Researchers and Customer Intelligence
// have no real code to emit from yet (confirmed repeatedly across this
// session) — calling emit() for them would be premature, not wrong, but
// no caller does today. Honest, not fabricated.

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { readJsonlEntries } = require('./jsonl');

const DEFAULT_LOG_PATH = path.join(__dirname, '..', 'data', 'department_events.jsonl');

const VALID_DEPARTMENTS = [
  'executive', 'market_intelligence', 'golden_hunter', 'pioneer', 'researchers',
  'production', 'publishing', 'finance', 'customer_intelligence', 'infrastructure',
  'recovery', 'ai_capability_manager',
];

function emit({ department, event_type, ref_id = null, source_log = null, summary = '' }, logPath = DEFAULT_LOG_PATH) {
  if (!VALID_DEPARTMENTS.includes(department)) {
    throw new Error(`department_events.emit: unknown department "${department}"`);
  }
  const record = {
    event_id: crypto.randomBytes(8).toString('hex'),
    emitted_at: new Date().toISOString(),
    department, event_type, ref_id, source_log, summary,
  };
  try {
    fs.mkdirSync(path.dirname(logPath), { recursive: true });
    fs.appendFileSync(logPath, JSON.stringify(record) + '\n');
    return record;
  } catch (err) {
    // Same discipline as appendGoldenHunterEvent(): a correlation-index
    // write failure must never break the real underlying action.
    return { ...record, _logFailed: true, _error: err.message };
  }
}

function readEvents(logPath = DEFAULT_LOG_PATH) {
  return readJsonlEntries(logPath, Infinity);
}

module.exports = { emit, readEvents, VALID_DEPARTMENTS, DEFAULT_LOG_PATH };
