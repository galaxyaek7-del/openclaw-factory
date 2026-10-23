// Galaxy Forge -- bounded agent chain: context-preserving handoffs (2026-10-23).
//
// Runs an ordered list of steps for one task. Each step is either an agent
// step (an invokeAgent() call whose validated output is parsed into the shared
// context for the next step) or a protected step (an external side effect),
// which is refused unless explicitly authorized. State is persisted per task
// in data/agent_tasks.jsonl, one line per finished step:
//   { task_id, step, agent, status, attempt, at, correlation_id, error }
// Re-running a task_id skips steps already recorded "done" (no duplicate
// work); a failed step stops the chain after `maxAttempts` attempts.
// This is not a scheduler or a second orchestrator: it is invoked by a
// caller (a script, a route, a test) and returns when the chain ends.

const fs = require('fs');
const path = require('path');
const { invokeAgent } = require('./agent_runtime');

const DEFAULT_STATE = path.join(__dirname, '..', 'data', 'agent_tasks.jsonl');

function readTaskState(taskId, statePath = DEFAULT_STATE) {
  try {
    return fs.readFileSync(statePath, 'utf8').split('\n').filter(Boolean)
      .map((l) => { try { return JSON.parse(l); } catch (_) { return null; } })
      .filter((r) => r && r.task_id === taskId);
  } catch (_) {
    return [];
  }
}

function appendState(row, statePath) {
  fs.mkdirSync(path.dirname(statePath), { recursive: true });
  fs.appendFileSync(statePath, JSON.stringify(row) + '\n');
}

function liveWritesAuthorized(env = process.env) {
  return ['1', 'true', 'yes', 'on'].includes(String(env.FACTORY_LIVE_PUBLISH || '').trim().toLowerCase());
}

/**
 * steps: [{ id, agent, config, buildMessage(ctx) -> string, parse(content, ctx) -> object|null }
 *         | { id, protected: true, run(ctx) -> Promise }]
 * Returns { task_id, status: 'done'|'failed'|'blocked', ctx, steps: [...] }.
 */
async function runChain({ taskId, steps, client, statePath = DEFAULT_STATE, maxAttempts = 2, correlationId,
  agentLogPath, env = process.env, invoke = invokeAgent, initialContext = {} }) {
  const prior = readTaskState(taskId, statePath);
  const doneById = new Map(prior.filter((r) => r.status === 'done').map((r) => [r.step, r]));
  const ctx = Object.assign({}, initialContext, ...prior.filter((r) => r.status === 'done' && r.output).map((r) => r.output));
  const report = [];
  for (const step of steps) {
    if (doneById.has(step.id)) {
      report.push({ step: step.id, status: 'skipped_already_done' });
      continue;
    }
    if (step.protected) {
      if (!liveWritesAuthorized(env)) {
        appendState({ task_id: taskId, step: step.id, status: 'blocked', at: new Date().toISOString(),
          correlation_id: correlationId || null, error: 'protected external action: FACTORY_LIVE_PUBLISH is not true' }, statePath);
        report.push({ step: step.id, status: 'blocked' });
        return { task_id: taskId, status: 'blocked', ctx, steps: report };
      }
      await step.run(ctx);
      appendState({ task_id: taskId, step: step.id, status: 'done', at: new Date().toISOString() }, statePath);
      report.push({ step: step.id, status: 'done' });
      continue;
    }
    let last = null;
    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      const r = await invoke({ name: step.agent, config: step.config, client, message: step.buildMessage(ctx),
        source: 'agent_chain', correlationId: correlationId || taskId, taskId: `${taskId}:${step.id}:${attempt}`,
        logPath: agentLogPath, maxTokens: step.maxTokens || 1024 });
      const parsed = r.ok ? step.parse(r.content, ctx) : null;
      last = { attempt, error: r.ok ? (parsed ? null : 'output did not satisfy the step contract') : r.error };
      if (parsed) {
        Object.assign(ctx, parsed);
        appendState({ task_id: taskId, step: step.id, agent: step.agent, status: 'done', attempt,
          at: new Date().toISOString(), correlation_id: correlationId || taskId, output: parsed }, statePath);
        report.push({ step: step.id, status: 'done', attempt });
        last = null;
        break;
      }
    }
    if (last) {
      appendState({ task_id: taskId, step: step.id, agent: step.agent, status: 'failed', attempt: last.attempt,
        at: new Date().toISOString(), correlation_id: correlationId || taskId, error: String(last.error).slice(0, 300) }, statePath);
      report.push({ step: step.id, status: 'failed', attempts: last.attempt, error: last.error });
      return { task_id: taskId, status: 'failed', ctx, steps: report };
    }
  }
  return { task_id: taskId, status: 'done', ctx, steps: report };
}

module.exports = { runChain, readTaskState, liveWritesAuthorized, DEFAULT_STATE };
