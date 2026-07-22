// Tests for lib/telegram_direct.js (ADR-085).
// Uses Node's built-in test runner (node:test), same convention as
// tests/test_n8n_notify.js. No real network calls — global.fetch is
// mocked and restored around every test.
//
//   node --test tests/test_telegram_direct.js

const test = require('node:test');
const assert = require('node:assert/strict');

const {
  sendTelegramMessage, buildProductReadyMessage, buildSaleMadeMessage, buildCriticalErrorMessage,
} = require('../lib/telegram_direct.js');

function withMockedFetch(impl, fn) {
  const original = global.fetch;
  global.fetch = impl;
  return fn().finally(() => { global.fetch = original; });
}

function withEnv(vars, fn) {
  const original = {};
  for (const k of Object.keys(vars)) { original[k] = process.env[k]; process.env[k] = vars[k]; }
  return fn().finally(() => {
    for (const k of Object.keys(vars)) {
      if (original[k] === undefined) delete process.env[k];
      else process.env[k] = original[k];
    }
  });
}

test('missing token/chatId -> no-ops, never calls fetch, reports error not throw', async () => {
  let fetchCalled = false;
  await withMockedFetch(
    async () => { fetchCalled = true; throw new Error('fetch must not be called'); },
    async () => {
      const result = await sendTelegramMessage('hello', { token: null, chatId: null });
      assert.equal(result.sent, false);
      assert.match(result.error, /not configured/);
      assert.equal(fetchCalled, false);
    }
  );
});

test('real send success -> reports message_id, posts real chat_id/text payload', async () => {
  await withMockedFetch(
    async (url, opts) => {
      assert.equal(url, 'https://api.telegram.org/bottest-token/sendMessage');
      const body = JSON.parse(opts.body);
      assert.equal(body.chat_id, '999');
      assert.equal(body.text, 'hello world');
      return { ok: true, json: async () => ({ ok: true, result: { message_id: 55 } }) };
    },
    async () => {
      const result = await sendTelegramMessage('hello world', { token: 'test-token', chatId: '999' });
      assert.deepEqual(result, { sent: true, message_id: 55, error: null });
    }
  );
});

test('telegram rejection -> reported, not thrown', async () => {
  await withMockedFetch(
    async () => ({ ok: false, status: 400, json: async () => ({ ok: false, description: 'chat not found' }) }),
    async () => {
      const result = await sendTelegramMessage('hello', { token: 't', chatId: 'c' });
      assert.equal(result.sent, false);
      assert.equal(result.error, 'chat not found');
    }
  );
});

test('network failure -> reported, not thrown', async () => {
  await withMockedFetch(
    async () => { throw new Error('network down'); },
    async () => {
      const result = await sendTelegramMessage('hello', { token: 't', chatId: 'c' });
      assert.equal(result.sent, false);
      assert.equal(result.error, 'network down');
    }
  );
});

test('falls back to process.env when token/chatId not passed explicitly', async () => {
  await withEnv({ TELEGRAM_BOT_TOKEN: 'env-token', OPENCLAW_TELEGRAM_CHAT_ID: 'env-chat' }, async () => {
    await withMockedFetch(
      async (url) => {
        assert.equal(url, 'https://api.telegram.org/botenv-token/sendMessage');
        return { ok: true, json: async () => ({ ok: true, result: { message_id: 1 } }) };
      },
      async () => {
        const result = await sendTelegramMessage('hi');
        assert.equal(result.sent, true);
      }
    );
  });
});

test('buildProductReadyMessage includes niche and price when present', () => {
  const msg = buildProductReadyMessage({
    niche: 'AI compliance automation', production_id: 'PROD-123',
    pricing_strategy: { recommended_price: 388 },
  });
  assert.match(msg, /منتج جاهز للمراجعة/);
  assert.match(msg, /AI compliance automation/);
  assert.match(msg, /\$388/);
  assert.match(msg, /PROD-123/);
});

test('buildProductReadyMessage omits price line cleanly when absent, never shows undefined', () => {
  const msg = buildProductReadyMessage({ niche: 'x', production_id: 'PROD-1', pricing_strategy: null });
  assert.doesNotMatch(msg, /undefined/);
  assert.doesNotMatch(msg, /السعر/);
});

test('buildSaleMadeMessage includes platform and amount', () => {
  const msg = buildSaleMadeMessage({ platform: 'Paddle', amount: 388, title: 'AI Compliance System' });
  assert.match(msg, /بيع جديد/);
  assert.match(msg, /Paddle/);
  assert.match(msg, /\$388/);
});

test('buildCriticalErrorMessage shows first reason and a count of extras', () => {
  const msg = buildCriticalErrorMessage(['reason one', 'reason two', 'reason three']);
  assert.match(msg, /عطل حرج/);
  assert.match(msg, /reason one/);
  assert.match(msg, /\+2/);
  assert.doesNotMatch(msg, /reason two/); // only the first is shown verbatim, never all of them
});

test('buildCriticalErrorMessage with a single reason has no "+N extra" line', () => {
  const msg = buildCriticalErrorMessage(['only reason']);
  assert.doesNotMatch(msg, /\+\d/);
});
