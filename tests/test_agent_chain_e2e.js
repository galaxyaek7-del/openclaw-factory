// End-to-end agent handoff: task -> scout -> qa -> protected step (2026-10-23).
// The model client is a fake; state and telemetry go to temp files.
//
//   node --test tests/test_agent_chain_e2e.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const { runChain, readTaskState } = require('../lib/agent_chain');
const { researchSteps, todaysTrends } = require('../lib/research_chain');
const { readAgentExecutions } = require('../lib/agent_runtime');

const SCOUT_REPLY = '##TITLE##\nدليل تنظيم المهام للمستقلين\n##TOPIC##\nنظام عملي لإدارة العملاء والمواعيد\n##AUDIENCE##\nالمستقلون\n##PRICE##\n39\n##CHAPTERS##\n6';
const QA_REPLY = 'VERDICT: PASS\nREASON: clear buyer and concrete outcome.';

function tmp() {
  const d = fs.mkdtempSync(path.join(os.tmpdir(), 'gf_chain_'));
  return { state: path.join(d, 'tasks.jsonl'), agents: path.join(d, 'agents.jsonl') };
}

function fakeClient(script) {
  const seen = [];
  return {
    seen,
    chat: { completions: { create: async ({ messages }) => {
      const sys = messages[0].content;
      const who = sys.includes('استكشاف') ? 'scout' : 'qa';
      seen.push({ who, user: messages[1].content });
      const next = script[who].shift();
      if (next instanceof Error) throw next;
      return { choices: [{ message: { content: next } }], usage: { completion_tokens: 10 } };
    } } },
  };
}

test('a task flows scout -> qa with context, persists, and the protected step is blocked', async () => {
  const p = tmp();
  const client = fakeClient({ scout: [SCOUT_REPLY], qa: [QA_REPLY] });
  const r = await runChain({ taskId: 'T1', steps: researchSteps(), client, statePath: p.state, agentLogPath: p.agents,
    initialContext: { trends: ['remote work', 'freelance invoicing'] }, env: {} });
  // 1-4: accepted, scout selected and invoked, output validated into a brief
  assert.equal(client.seen[0].who, 'scout');
  assert.ok(client.seen[0].user.includes('freelance invoicing'), 'scout received the trends');
  assert.equal(r.ctx.brief.title, 'دليل تنظيم المهام للمستقلين');
  // 5: qa received the scout's brief as context
  assert.equal(client.seen[1].who, 'qa');
  assert.ok(client.seen[1].user.includes('دليل تنظيم المهام للمستقلين'));
  assert.equal(r.ctx.qa_verdict, 'PASS');
  // 9: the protected step is refused without authorization
  assert.equal(r.status, 'blocked');
  // 6: state and execution evidence persisted
  const state = readTaskState('T1', p.state);
  assert.deepEqual(state.map((s) => [s.step, s.status]), [['scout_brief', 'done'], ['qa_review', 'done'], ['distribute', 'blocked']]);
  const ex = readAgentExecutions(p.agents);
  assert.deepEqual(ex.map((e) => [e.agent, e.outcome, e.source]), [['scout', 'ok', 'agent_chain'], ['qa', 'ok', 'agent_chain']]);
});

test('an agent failure is detected, retried within bounds, and stops the chain', async () => {
  const p = tmp();
  const client = fakeClient({ scout: [new Error('503 upstream'), 'not a brief'], qa: [] });
  const r = await runChain({ taskId: 'T2', steps: researchSteps(), client, statePath: p.state, agentLogPath: p.agents, env: {} });
  assert.equal(r.status, 'failed');
  assert.equal(client.seen.filter((s) => s.who === 'qa').length, 0, 'qa never ran on a failed brief');
  const state = readTaskState('T2', p.state);
  assert.equal(state.at(-1).status, 'failed');
  assert.equal(state.at(-1).attempt, 2);
  // The model answered the second time ("ok" at the runtime layer), but the
  // answer is not a brief: the step contract rejects it in the task state.
  assert.deepEqual(readAgentExecutions(p.agents).map((e) => e.outcome), ['error', 'ok']);
  assert.match(state.at(-1).error, /step contract/);
});

test('re-running a task never repeats completed steps', async () => {
  const p = tmp();
  const c1 = fakeClient({ scout: [SCOUT_REPLY], qa: [new Error('timeout'), new Error('timeout')] });
  const r1 = await runChain({ taskId: 'T3', steps: researchSteps(), client: c1, statePath: p.state, agentLogPath: p.agents, env: {} });
  assert.equal(r1.status, 'failed');
  const c2 = fakeClient({ scout: [], qa: [QA_REPLY] });
  const r2 = await runChain({ taskId: 'T3', steps: researchSteps(), client: c2, statePath: p.state, agentLogPath: p.agents, env: {} });
  assert.equal(c2.seen.filter((s) => s.who === 'scout').length, 0, 'scout was not invoked again');
  assert.equal(r2.steps[0].status, 'skipped_already_done');
  assert.equal(r2.ctx.brief.title, 'دليل تنظيم المهام للمستقلين', 'context restored from persisted state');
  assert.equal(r2.ctx.qa_verdict, 'PASS');
});

test('todaysTrends reads only the given day from OPPORTUNITIES.md', () => {
  const f = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'gf_opp_')), 'O.md');
  fs.writeFileSync(f, '- [2026-10-22T07:00:00Z] old niche — x\n- [2026-10-23T07:41:46Z] new niche — x\n- [2026-10-23T07:41:47Z] new niche — x\n');
  assert.deepEqual(todaysTrends('2026-10-23', f), ['new niche']);
});
