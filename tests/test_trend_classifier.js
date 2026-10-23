// lib/trend_classifier.js -- the scout agent decides whether a Sensing trend
// is a need someone would pay to solve. Fake model client; temp telemetry log.
//   node --test tests/test_trend_classifier.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { classifyTrend, parseClassification } = require('../lib/trend_classifier');
const { readAgentExecutions } = require('../lib/agent_runtime');

const logPath = () => path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'gf_tc_')), 'agents.jsonl');

function client(reply) {
  const seen = [];
  return { seen, chat: { completions: { create: async ({ messages }) => {
    seen.push(messages[1].content);
    if (reply instanceof Error) throw reply;
    return { choices: [{ message: { content: reply } }], usage: {} };
  } } } };
}

test('a person is rejected and the call is recorded as a factory call', async () => {
  const log = logPath();
  const c = client('COMMERCIAL: NO\nREASON: a celebrity name, interest ends with the news.');
  const r = await classifyTrend({ niche: 'khloe kardashian', client: c, logPath: log });
  assert.equal(r.commercial, false);
  assert.equal(r.failed, false);
  assert.match(r.reason, /celebrity/);
  assert.ok(c.seen[0].includes('khloe kardashian'));
  const ex = readAgentExecutions(log);
  assert.deepEqual(ex.map((e) => [e.agent, e.source, e.outcome]), [['scout', 'sensing_trends', 'ok']]);
});

test('a recurring need is accepted', async () => {
  const r = await classifyTrend({ niche: 'small business bookkeeping', client: client('COMMERCIAL: YES\nREASON: ongoing task.'), logPath: logPath() });
  assert.equal(r.commercial, true);
});

test('an API failure fails closed with the reason', async () => {
  const r = await classifyTrend({ niche: 'x', client: client(new Error('503 upstream')), logPath: logPath() });
  assert.equal(r.commercial, false);
  assert.equal(r.failed, true);
  assert.match(r.reason, /^classifier_unavailable: .*503/);
});

test('an answer outside the contract fails closed and is recorded as invalid output', async () => {
  const log = logPath();
  const r = await classifyTrend({ niche: 'x', client: client('Sure! This looks promising.'), logPath: log });
  assert.equal(r.commercial, false);
  assert.equal(r.failed, true);
  assert.equal(readAgentExecutions(log)[0].outcome, 'invalid_output');
});

test('an empty answer is retried once, so a real need is not dropped', async () => {
  const log = logPath();
  const replies = ['', 'COMMERCIAL: YES\nREASON: recurring bookkeeping task.'];
  const c = { chat: { completions: { create: async () => ({ choices: [{ message: { content: replies.shift() } }], usage: {} }) } } };
  const r = await classifyTrend({ niche: 'small business bookkeeping', client: c, logPath: log });
  assert.equal(r.commercial, true);
  assert.deepEqual(readAgentExecutions(log).map((e) => e.outcome), ['invalid_output', 'ok']);
});

test('two failed attempts still fail closed, with no third call', async () => {
  const log = logPath();
  let calls = 0;
  const c = { chat: { completions: { create: async () => { calls += 1; return { choices: [{ message: { content: '' } }], usage: {} }; } } } };
  const r = await classifyTrend({ niche: 'x', client: c, logPath: log });
  assert.equal(r.commercial, false);
  assert.equal(r.failed, true);
  assert.equal(calls, 2);
});

test('parseClassification is strict about the verdict line', () => {
  assert.equal(parseClassification('COMMERCIAL: maybe'), null);
  assert.deepEqual(parseClassification('commercial: yes\nreason: fine'), { commercial: true, reason: 'fine' });
});
