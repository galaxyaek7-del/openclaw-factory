// Recovery action audit logging (Phase 10D — Disaster Recovery &
// Business Continuity). Pure, framework-free — mirrors lib/metrics.js's
// convention — so it's unit-testable in isolation. Every real recovery
// action (a restart, a rollback, a restore) should call
// recordRecoveryAction() so there is always a real, append-only,
// auditable record of what happened, why, and what the result was.
//
// Fields required by this directive's objective 5: timestamp, operator,
// reason, affected systems, recovery result — all real, never inferred.

const fs = require('fs');
const path = require('path');
const { readJsonlEntries } = require('./jsonl');
const departmentEvents = require('./department_events');

function recordRecoveryAction({ operator, reason, affectedSystems, result, logPath, departmentEventsPath }) {
  if (!operator) throw new Error('recordRecoveryAction requires an operator');
  if (!reason) throw new Error('recordRecoveryAction requires a reason');
  if (!Array.isArray(affectedSystems) || !affectedSystems.length) {
    throw new Error('recordRecoveryAction requires a non-empty affectedSystems array');
  }
  if (!result) throw new Error('recordRecoveryAction requires a result');

  const record = {
    timestamp: new Date().toISOString(),
    operator,
    reason,
    affected_systems: affectedSystems,
    result,
  };

  const targetPath = logPath || path.join(__dirname, '..', 'data', 'recovery_actions.jsonl');
  fs.mkdirSync(path.dirname(targetPath), { recursive: true });
  fs.appendFileSync(targetPath, JSON.stringify(record) + '\n');

  // EOS Phase 2, Round 2 (2026-07-19): also emits a real correlation-
  // index entry -- envelope only, same call site as the real write
  // above. Best-effort: a department_events failure must never affect
  // the real recovery action just recorded.
  try {
    departmentEvents.emit({
      department: 'recovery', event_type: 'recovery.action_taken',
      ref_id: operator, source_log: 'data/recovery_actions.jsonl',
      summary: `${reason} (${result})`,
    }, departmentEventsPath || departmentEvents.DEFAULT_LOG_PATH);
  } catch (_) { /* best effort */ }

  return record;
}

// Engineering Evolution Mode follow-up: was its own independent
// implementation, identical in behavior to lib/jsonl.js#readJsonlEntries()
// — now a thin wrapper over the shared version.
function readRecoveryActions(logPath) {
  const targetPath = logPath || path.join(__dirname, '..', 'data', 'recovery_actions.jsonl');
  return readJsonlEntries(targetPath, Infinity);
}

module.exports = { recordRecoveryAction, readRecoveryActions };
