// Galaxy Forge -- once-a-day product chain run for factory_loop.js (2026-10-23).
//
// Every tick may call this; it does work at most once per UTC day:
//   - no trend for today in OPPORTUNITIES.md       -> none (nothing to work from)
//   - today's task already ended (done/stopped/blocked) -> none
//   - MAX_FAILED_RUNS failed attempts today          -> none (wait for tomorrow)
//   - otherwise run lib/product_chain.js steps as task product_<day>, source "loop".
// A run never publishes: the chain ends at the protected distribute step.

const { runChain, readTaskState, DEFAULT_STATE } = require('./agent_chain');
const { productSteps } = require('./product_chain');
const { todaysTrends } = require('./research_chain');

const MAX_FAILED_RUNS = 3;
const TERMINAL = new Set(['stopped', 'blocked']);

function todayStatus(taskId, statePath) {
  const rows = readTaskState(taskId, statePath);
  const ended = rows.find((r) => TERMINAL.has(r.status));
  const failed = rows.filter((r) => r.status === 'failed').length;
  return { ended, failed, rows };
}

async function runDailyProductChain({ client, day = new Date().toISOString().slice(0, 10), statePath = DEFAULT_STATE,
  trends, opportunitiesPath, stepsOptions, agentLogPath, env = process.env, invoke } = {}) {
  const taskId = `product_${day}`;
  const items = trends || todaysTrends(day, opportunitiesPath);
  if (!items.length) return { action: 'none', detail: `no trend recorded for ${day} in OPPORTUNITIES.md`, task_id: taskId };
  const s = todayStatus(taskId, statePath);
  if (s.ended) return { action: 'none', detail: `${taskId} already ended today (${s.ended.step}: ${s.ended.status})`, task_id: taskId };
  if (s.failed >= MAX_FAILED_RUNS) return { action: 'none', detail: `${taskId}: ${s.failed} failed attempts today, next run tomorrow`, task_id: taskId };
  if (!client) return { action: 'failed', detail: 'no model client (GROQ_KEY not configured)', task_id: taskId };

  const r = await runChain({ taskId, steps: productSteps(stepsOptions), client, statePath, agentLogPath, env, source: 'loop',
    initialContext: { trends: items, task_id: taskId }, ...(invoke ? { invoke } : {}) });
  const last = r.steps[r.steps.length - 1] || {};
  const detail = r.status === 'stopped' ? r.reason
    : r.status === 'blocked' ? `package ready for founder review: ${r.ctx.package_path}; distribute blocked (no live-publish authorization)`
      : r.status === 'failed' ? `${last.step} failed: ${String(last.error || '').slice(0, 200)}` : 'done';
  return { action: r.status === 'failed' ? 'failed' : r.status, detail, task_id: taskId, package_path: r.ctx.package_path || null };
}

module.exports = { runDailyProductChain, MAX_FAILED_RUNS };
