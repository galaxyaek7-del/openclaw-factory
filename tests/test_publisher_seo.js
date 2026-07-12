// Tests for lib/publisher_seo.js (ADR-019, Publisher -> distribution link).
// Uses Node's built-in test runner (node:test, Node 18+) — no new
// dependency added to package.json. groqClient is always a fake here: no
// test ever makes a real network call or spends a real Groq token.
//
//   node --test tests/test_publisher_seo.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const { logPublisherSEO, generatePublisherSEO } = require('../lib/publisher_seo');

test('generatePublisherSEO fails safe without a GROQ key, never calling groqClient', async () => {
  let called = false;
  const fakeClient = { chat: { completions: { create: async () => { called = true; return {}; } } } };
  const result = await generatePublisherSEO(
    { title: 'X', topic: 'Y' },
    { groqClient: fakeClient, groqKey: null, systemPrompt: 'sys' }
  );
  assert.equal(result.ok, false);
  assert.match(result.error, /GROQ_KEY/);
  assert.equal(called, false);
});

test('generatePublisherSEO fails safe when the record has no title/topic', async () => {
  const fakeClient = { chat: { completions: { create: async () => ({ choices: [{ message: { content: 'x' } }] }) } } };
  const result = await generatePublisherSEO({}, { groqClient: fakeClient, groqKey: 'fake', systemPrompt: 'sys' });
  assert.equal(result.ok, false);
  assert.match(result.error, /عنوان/);
});

test('generatePublisherSEO returns groq content on success and passes the system prompt through', async () => {
  const fakeClient = {
    chat: {
      completions: {
        create: async (opts) => {
          assert.equal(opts.messages[0].role, 'system');
          assert.equal(opts.messages[0].content, 'sys-prompt');
          assert.match(opts.messages[1].content, /كتاب تجريبي/);
          return { choices: [{ message: { content: 'SEO TEXT' } }] };
        },
      },
    },
  };
  const result = await generatePublisherSEO(
    { title: 'كتاب تجريبي', topic: 'نيتش تجريبي' },
    { groqClient: fakeClient, groqKey: 'fake', systemPrompt: 'sys-prompt' }
  );
  assert.equal(result.ok, true);
  assert.equal(result.content, 'SEO TEXT');
});

test('generatePublisherSEO reports a groq error without throwing', async () => {
  const fakeClient = { chat: { completions: { create: async () => { throw new Error('boom'); } } } };
  const result = await generatePublisherSEO({ title: 'X' }, { groqClient: fakeClient, groqKey: 'fake', systemPrompt: 'sys' });
  assert.equal(result.ok, false);
  assert.equal(result.error, 'boom');
});

test('generatePublisherSEO falls back to record.topic when title is missing', async () => {
  const fakeClient = { chat: { completions: { create: async () => ({ choices: [{ message: { content: 'ok' } }] }) } } };
  const result = await generatePublisherSEO({ topic: 'نيتش فقط بلا عنوان' }, { groqClient: fakeClient, groqKey: 'fake', systemPrompt: 'sys' });
  assert.equal(result.ok, true);
});

test('logPublisherSEO appends one JSON line with a timestamp to the given path', () => {
  const tmp = path.join(os.tmpdir(), `publisher_seo_test_${Date.now()}.jsonl`);
  logPublisherSEO({ product_title: 'X', ok: true, content: 'c', error: null }, tmp);
  const lines = fs.readFileSync(tmp, 'utf8').trim().split('\n');
  assert.equal(lines.length, 1);
  const entry = JSON.parse(lines[0]);
  assert.equal(entry.product_title, 'X');
  assert.ok(entry.timestamp);
  fs.unlinkSync(tmp);
});

test('logPublisherSEO never throws even if the target path is invalid', () => {
  assert.doesNotThrow(() => {
    logPublisherSEO({ ok: false }, path.join(os.tmpdir(), 'nonexistent-dir-xyz-123', 'log.jsonl'));
  });
});
