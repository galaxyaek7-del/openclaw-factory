// lib/agent_runtime.js -- one agent invocation path with execution evidence.
// Fake model clients only; nothing reaches the network.
//
//   node --test tests/test_agent_runtime.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const rt = require('../lib/agent_runtime');
const AGENT_PROMPTS = require('../lib/agent_prompts');

function tmpLog() {
  return path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'gf_agents_')), 'agent_executions.jsonl');
}
const client = (impl) => ({ chat: { completions: { create: impl } } });
const reply = (content, usage) => async () => ({ choices: [{ message: { content } }], usage });

test('the six personas exist with a system prompt and a trigger', () => {
  assert.deepEqual(Object.keys(AGENT_PROMPTS), ['scout', 'builder', 'design', 'qa', 'publisher', 'finance']);
  for (const [name, cfg] of Object.entries(AGENT_PROMPTS)) {
    assert.ok(cfg.system && cfg.trigger, name);
  }
});

test('a successful call returns content and records one execution line', async () => {
  const log = tmpLog();
  const r = await rt.invokeAgent({ name: 'qa', config: AGENT_PROMPTS.qa, client: client(reply('checklist ok', { prompt_tokens: 10, completion_tokens: 3 })),
    logPath: log, correlationId: 'corr_test' });
  assert.equal(r.ok, true);
  assert.equal(r.content, 'checklist ok');
  const lines = rt.readAgentExecutions(log);
  assert.equal(lines.length, 1);
  const e = lines[0];
  for (const k of ['task_id', 'correlation_id', 'agent', 'source', 'started_at', 'duration_ms', 'outcome', 'model']) assert.ok(k in e, k);
  assert.equal(e.agent, 'qa');
  assert.equal(e.outcome, 'ok');
  assert.equal(e.correlation_id, 'corr_test');
  assert.equal(e.completion_tokens, 3);
});

test('the log never contains the prompt or the output text', async () => {
  const log = tmpLog();
  await rt.invokeAgent({ name: 'finance', config: AGENT_PROMPTS.finance, message: 'CONFIDENTIAL-INPUT',
    client: client(reply('CONFIDENTIAL-OUTPUT')), logPath: log });
  const raw = fs.readFileSync(log, 'utf8');
  assert.ok(!raw.includes('CONFIDENTIAL-INPUT'));
  assert.ok(!raw.includes('CONFIDENTIAL-OUTPUT'));
  assert.ok(!raw.includes(AGENT_PROMPTS.finance.system.slice(0, 30)));
});

test('empty output is recorded as invalid_output, not success', async () => {
  const log = tmpLog();
  const r = await rt.invokeAgent({ name: 'design', config: AGENT_PROMPTS.design, client: client(reply('   ')), logPath: log });
  assert.equal(r.ok, false);
  assert.equal(rt.readAgentExecutions(log)[0].outcome, 'invalid_output');
});

test('a hung provider times out and is recorded', async () => {
  const log = tmpLog();
  const r = await rt.invokeAgent({ name: 'scout', config: AGENT_PROMPTS.scout, client: client(() => new Promise(() => {})),
    timeoutMs: 50, logPath: log });
  assert.equal(r.ok, false);
  assert.equal(rt.readAgentExecutions(log)[0].outcome, 'timeout');
});

test('provider errors are sanitized: keys never reach the log', async () => {
  const log = tmpLog();
  const boom = async () => { throw new Error('401 invalid key gsk_ABCDEFGHIJKLMNOPQRSTUV for Bearer xyz.abc'); };
  const r = await rt.invokeAgent({ name: 'builder', config: AGENT_PROMPTS.builder, client: client(boom), logPath: log });
  assert.equal(r.ok, false);
  const raw = fs.readFileSync(log, 'utf8');
  assert.ok(!raw.includes('gsk_ABCDEFGHIJKLMNOPQRSTUV'));
  assert.ok(!raw.includes('xyz.abc'));
  assert.ok(raw.includes('[REDACTED]'));
});

test('unknown agent and missing client are recorded errors, never a call', async () => {
  const log = tmpLog();
  let called = false;
  const r1 = await rt.invokeAgent({ name: 'ghost', config: undefined, client: client(async () => { called = true; }), logPath: log });
  const r2 = await rt.invokeAgent({ name: 'qa', config: AGENT_PROMPTS.qa, client: null, logPath: log });
  assert.equal(r1.ok || r2.ok, false);
  assert.equal(called, false);
  assert.equal(rt.readAgentExecutions(log).length, 2);
});
