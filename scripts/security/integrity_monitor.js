#!/usr/bin/env node
/* Pre-flight wrapper (Phase 4, 2026-10-16) around the factory's real ledger
 * integrity check, integrity_monitor.py (Security P1 C3). No second
 * implementation: this only runs it and prints CLEAN or DRIFT.
 * Its only write is integrity_monitor.py's own baseline file.
 * Exit 0 = CLEAN, 1 = DRIFT or the check could not run. */
'use strict';
const { spawnSync } = require('child_process');
const path = require('path');

const root = path.resolve(__dirname, '..', '..');
const py = process.env.PYTHON || 'python';
const r = spawnSync(py, ['integrity_monitor.py'], { cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
if (r.status !== 0) {
  console.log('INTEGRITY: ERROR - integrity_monitor.py did not run cleanly');
  console.log((r.stderr || '').split('\n').slice(-5).join('\n'));
  process.exit(1);
}
let report;
try { report = JSON.parse(r.stdout); } catch (e) {
  console.log('INTEGRITY: ERROR - unparseable output'); process.exit(1);
}
const findings = JSON.stringify(report);
const drift = /"(MODIFIED|TRUNCATED|TAMPERED|DRIFT)"/i.test(findings) || report.status === 'DRIFT' || report.ok === false;
console.log(JSON.stringify(report, null, 2));
console.log(drift ? 'INTEGRITY: DRIFT' : 'INTEGRITY: CLEAN');
process.exit(drift ? 1 : 0);
