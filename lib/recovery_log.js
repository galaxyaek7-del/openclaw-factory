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

function recordRecoveryAction({ operator, reason, affectedSystems, result, logPath }) {
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
  return record;
}

function readRecoveryActions(logPath) {
  const targetPath = logPath || path.join(__dirname, '..', 'data', 'recovery_actions.jsonl');
  if (!fs.existsSync(targetPath)) return [];
  return fs.readFileSync(targetPath, 'utf8')
    .split('\n')
    .filter(Boolean)
    .map(line => {
      try { return JSON.parse(line); } catch { return null; }
    })
    .filter(Boolean);
}

module.exports = { recordRecoveryAction, readRecoveryActions };
