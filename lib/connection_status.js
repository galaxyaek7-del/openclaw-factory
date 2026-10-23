// Galaxy Forge -- Mission Control view of real execution evidence (2026-10-23).
//
// Read-only. Combines what is actually on disk:
//   data/connection_status.json  (connection_verifier.py output)
//   data/agent_executions.jsonl  (lib/agent_runtime.js, one line per agent call)
//   data/agent_tasks.jsonl       (lib/agent_chain.js, one line per finished step)
// A missing source is reported as UNKNOWN with the reason, never as zero or OK.

const fs = require('fs');
const path = require('path');
const { readJsonlEntries } = require('./jsonl');

const DATA = path.join(__dirname, '..', 'data');

// null (not []) when the file is missing, so the caller can report UNKNOWN.
function readJsonl(p) {
  return fs.existsSync(p) ? readJsonlEntries(p) : null;
}

function buildConnectionStatus({ dataDir = DATA, now = Date.now() } = {}) {
  const out = { generated_at: new Date(now).toISOString(), sources: {} };

  let verifier = null;
  try { verifier = JSON.parse(fs.readFileSync(path.join(dataDir, 'connection_status.json'), 'utf8')); } catch (_) { /* missing */ }
  if (verifier) {
    const age = (now - Date.parse(verifier.checked_at)) / 3600000;
    out.verifier = { checked_at: verifier.checked_at, age_hours: Math.round(age * 10) / 10, counts: verifier.counts,
      stale: age > 24, not_verified: (verifier.rows || []).filter((r) => !String(r.status).startsWith('VERIFIED')),
      // Runs when called, but no factory flow calls it: kept apart so it is never read as connected.
      not_connected: (verifier.rows || []).filter((r) => r.status === 'VERIFIED_EXECUTABLE_NOT_CONNECTED') };
    out.sources.verifier = 'data/connection_status.json';
  } else {
    out.verifier = { status: 'UNKNOWN', reason: 'connection_verifier.py has not written data/connection_status.json' };
  }

  const execs = readJsonl(path.join(dataDir, 'agent_executions.jsonl'));
  if (execs === null) {
    out.agents = { status: 'UNKNOWN', reason: 'no data/agent_executions.jsonl yet' };
  } else {
    const byAgent = {};
    for (const e of execs) {
      const a = byAgent[e.agent] || (byAgent[e.agent] = { calls: 0, ok: 0, failures: 0, last: null, sources: {} });
      a.calls += 1;
      if (e.outcome === 'ok') a.ok += 1; else a.failures += 1;
      a.sources[e.source] = (a.sources[e.source] || 0) + 1;
      a.last = { at: e.started_at, outcome: e.outcome, source: e.source, duration_ms: e.duration_ms, error: e.error };
    }
    out.agents = byAgent;
    out.sources.agents = 'data/agent_executions.jsonl';
  }

  const steps = readJsonl(path.join(dataDir, 'agent_tasks.jsonl'));
  if (steps === null) {
    out.tasks = { status: 'UNKNOWN', reason: 'no data/agent_tasks.jsonl yet' };
  } else {
    const tasks = {};
    for (const s of steps) {
      const t = tasks[s.task_id] || (tasks[s.task_id] = { steps: [], status: null, last_at: null });
      t.steps.push({ step: s.step, agent: s.agent, status: s.status, attempt: s.attempt, at: s.at, error: s.error });
      t.last_at = s.at;
    }
    for (const t of Object.values(tasks)) {
      const statuses = t.steps.map((x) => x.status);
      t.status = statuses.includes('failed') ? 'failed' : statuses.includes('blocked') ? 'blocked' : 'done';
    }
    out.tasks = tasks;
    out.sources.tasks = 'data/agent_tasks.jsonl';
  }
  return out;
}

module.exports = { buildConnectionStatus };
