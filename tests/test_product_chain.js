// lib/product_chain.js + lib/daily_product_chain.js: all six agents hand off
// to a founder-review package; the distribute step stays blocked.
// Fake model client; state, telemetry and packages go to temp paths.
//   node --test tests/test_product_chain.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const { runDailyProductChain, MAX_FAILED_RUNS } = require('../lib/daily_product_chain');
const { readTaskState } = require('../lib/agent_chain');
const { readAgentExecutions } = require('../lib/agent_runtime');
const { financeContract, outlineContract, listingContract } = require('../lib/product_chain');

const REPLIES = {
  scout: '##TITLE##\nSmall Business Bookkeeping Starter Kit\n##TOPIC##\nmonthly bookkeeping routine for sole traders\n##AUDIENCE##\nsole traders\n##PRICE##\n29\n##CHAPTERS##\n5',
  qa: 'VERDICT: PASS\nREASON: clear buyer and outcome.',
  finance: 'PRICE_USD: 27\nPLATFORM: Gumroad\nREASON: comparable kits sell at 20-35.',
  design: 'COVER: clean ledger grid with one accent color\nINTERIOR: monthly checklist pages\nPALETTE: navy, white, amber',
  builder: 'CHAPTER 1: Set up your books - accounts and categories\nCHAPTER 2: Weekly routine - 20 minute review\nCHAPTER 3: Month end - reconcile and close',
  publisher: 'TITLE: Bookkeeping Starter Kit for Sole Traders\nDESCRIPTION: A monthly routine with checklists. No accounting degree needed.\nTAGS: bookkeeping, sole trader, small business, checklist, finance',
};

const WHO = { 'استكشاف': 'scout', 'ضمان الجودة': 'qa', 'التمويل': 'finance', 'التصميم': 'design', 'بناء المحتوى': 'builder', 'النشر': 'publisher' };

function fakeClient(overrides = {}) {
  const calls = [];
  return { calls, chat: { completions: { create: async ({ messages }) => {
    const who = Object.entries(WHO).find(([k]) => messages[0].content.includes(k))[1];
    calls.push({ who, user: messages[1].content });
    const r = who in overrides ? overrides[who] : REPLIES[who];
    if (r instanceof Error) throw r;
    return { choices: [{ message: { content: r } }], usage: {} };
  } } } };
}

function paths() {
  const d = fs.mkdtempSync(path.join(os.tmpdir(), 'gf_pc_'));
  return { state: path.join(d, 'tasks.jsonl'), agents: path.join(d, 'agents.jsonl'), packages: path.join(d, 'pkg') };
}

const run = (p, client, extra = {}) => runDailyProductChain({ client, day: '2026-10-24', statePath: p.state, agentLogPath: p.agents,
  trends: ['small business bookkeeping'], stepsOptions: { packagesDir: p.packages }, env: {}, ...extra });

test('six agents hand off in order and the chain ends at a founder-review package', async () => {
  const p = paths();
  const c = fakeClient();
  const r = await run(p, c);
  assert.equal(r.action, 'blocked');
  assert.deepEqual(c.calls.map((x) => x.who), ['scout', 'qa', 'finance', 'design', 'builder', 'publisher']);
  // each agent received the scout's brief as context
  for (const call of c.calls.slice(1)) assert.ok(call.user.includes('Small Business Bookkeeping Starter Kit'), call.who);
  assert.ok(c.calls[5].user.includes('Price (USD): 27'), 'publisher saw the finance price');
  const pkg = JSON.parse(fs.readFileSync(path.join(p.packages, 'product_2026-10-24.json'), 'utf8'));
  assert.equal(pkg.status, 'AWAITING_FOUNDER_REVIEW');
  assert.equal(pkg.pricing.platform, 'gumroad');
  assert.equal(pkg.outline.length, 3);
  assert.equal(pkg.listing.tags.length, 5);
  const state = readTaskState('product_2026-10-24', p.state);
  assert.equal(state.at(-1).step, 'distribute');
  assert.equal(state.at(-1).status, 'blocked');
  assert.ok(readAgentExecutions(p.agents).every((e) => e.source === 'loop'), 'recorded as factory calls');
});

test('qa REVISE stops the chain as a decision; later agents never run; no package', async () => {
  const p = paths();
  const c = fakeClient({ qa: 'VERDICT: REVISE\nREASON: trends unrelated to the brief.' });
  const r = await run(p, c);
  assert.equal(r.action, 'stopped');
  assert.match(r.detail, /qa REVISE/);
  assert.deepEqual(c.calls.map((x) => x.who), ['scout', 'qa']);
  assert.equal(fs.existsSync(p.packages), false);
});

test('the same day never runs twice once the task ended', async () => {
  const p = paths();
  await run(p, fakeClient());
  const c2 = fakeClient();
  const r = await run(p, c2);
  assert.equal(r.action, 'none');
  assert.match(r.detail, /already ended/);
  assert.equal(c2.calls.length, 0);
});

test('failures are bounded per day and resume from the failed step', async () => {
  const p = paths();
  const bad = fakeClient({ finance: new Error('503') });
  for (let i = 0; i < MAX_FAILED_RUNS; i += 1) assert.equal((await run(p, bad)).action, 'failed');
  assert.equal(bad.calls.filter((x) => x.who === 'scout').length, 1, 'scout ran once; later runs resumed at finance');
  const r = await run(p, fakeClient());
  assert.equal(r.action, 'none');
  assert.match(r.detail, /failed attempts today/);
});

test('no trend today means nothing runs', async () => {
  const p = paths();
  const c = fakeClient();
  const r = await run(p, c, { trends: [] });
  assert.equal(r.action, 'none');
  assert.equal(c.calls.length, 0);
});

test('contracts reject answers missing required fields', () => {
  assert.equal(financeContract('PRICE_USD: 27\nPLATFORM: amazon ads'), null);
  assert.equal(outlineContract('CHAPTER 1: a\nCHAPTER 2: b'), null);
  assert.equal(listingContract('TITLE: x\nDESCRIPTION: y\nTAGS: a, b'), null);
});
