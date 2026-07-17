// Orphaned-process diagnostic (Phase 10D — Disaster Recovery & Business
// Continuity). Real finding from this phase's own crash-simulation test:
// killing server.js abruptly (simulating a crash/power failure) does NOT
// kill its child Python subprocesses on Windows (`taskkill /F` without
// `/T` only terminates the target process) — a real subprocess can
// survive indefinitely as an orphan, still consuming resources.
//
// This is deliberately a DIAGNOSTIC tool, not an automatic killer: a
// human must look at the list and decide, the same principle as
// deploy_production.js and ops_maintenance.js. Detecting a TRUE orphan
// (no living parent) reliably cross-platform is non-trivial; this
// reports every python.exe process with its start time and command
// line so a human can judge — "started right when I know something
// crashed" is a strong real signal, safer than an automated heuristic
// that might kill a legitimately-running process.
//
//   node scripts/check_orphan_processes.js

const { execSync } = require('child_process');

if (process.platform !== 'win32') {
  console.log('This diagnostic uses Windows-specific process tooling (Get-CimInstance). Not implemented for this platform.');
  process.exit(0);
}

try {
  const out = execSync(
    'powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \\"Name=\'python.exe\'\\" | Select-Object ProcessId,CreationDate,CommandLine | ConvertTo-Json"',
    { encoding: 'utf8' }
  );
  const trimmed = out.trim();
  if (!trimmed) {
    console.log('No python.exe processes currently running.');
    process.exit(0);
  }
  const parsed = JSON.parse(trimmed);
  const processes = Array.isArray(parsed) ? parsed : [parsed];
  console.log(`=== ${processes.length} python.exe process(es) currently running ===\n`);
  for (const p of processes) {
    // WMI CreationDate serializes as /Date(<ms-since-epoch>)/ via PowerShell's
    // ConvertTo-Json — extract the real timestamp rather than showing that raw.
    const match = /\/Date\((\d+)\)\//.exec(p.CreationDate || '');
    const started = match ? new Date(Number(match[1])).toISOString() : 'unknown';
    const ageMin = match ? Math.round((Date.now() - Number(match[1])) / 60000) : null;
    console.log(`PID ${p.ProcessId} — started ${started}${ageMin !== null ? ` (${ageMin} minute(s) ago)` : ''}`);
    console.log(`  ${p.CommandLine}\n`);
  }
  console.log('This factory\'s mission_control_api.py subprocesses normally run for seconds to a few minutes.');
  console.log('A python.exe here that has been running far longer than that, with no server.js action that should still be waiting on it, is a real orphan candidate.');
  console.log('To stop one: taskkill /F /PID <the exact PID> — never a broad taskkill /IM python.exe (this factory may have other, unrelated Python work running).');
} catch (err) {
  console.error(`Could not enumerate python.exe processes: ${err.message}`);
  process.exit(1);
}
