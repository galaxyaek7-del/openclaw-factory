// Tests for lib/founder_alert.js (Cycle 95). No real network: every path is
// stubbed, and the module itself blocks unstubbed sends under node --test.
//
//   node --test tests/test_founder_alert.js

const test = require('node:test');
const assert = require('node:assert/strict');

const { formatFounderAlert, sendFounderAlert } = require('../lib/founder_alert.js');

function stubs({ directSent, relaySuccess }) {
  const calls = { direct: [], relay: [] };
  return {
    calls,
    direct: { sendTelegramMessage: async (text) => { calls.direct.push(text); return directSent ? { sent: true, message_id: 42 } : { sent: false, error: 'not configured' }; } },
    n8n: { notifyN8nProductionEvent: async (payload, opts) => { calls.relay.push({ payload, opts }); return { attempted: true, success: relaySuccess }; } },
  };
}

test('direct delivery wins and n8n is not called', async () => {
  const s = stubs({ directSent: true, relaySuccess: true });
  const out = await sendFounderAlert({ event: 'sale_detected', total_new_sales: 1 }, { direct: s.direct, n8n: s.n8n });
  assert.deepEqual(out, { channel: 'telegram_direct', delivered: true, message_id: 42 });
  assert.equal(s.calls.relay.length, 0, 'no duplicate alert through n8n');
  assert.match(s.calls.direct[0], /بيع جديد/);
});

test('n8n acknowledgement is reported as unconfirmed, never delivered', async () => {
  const s = stubs({ directSent: false, relaySuccess: true });
  const opts = { webhookUrl: 'http://stub', envVarName: 'N8N_TELEGRAM_WEBHOOK_URL' };
  const out = await sendFounderAlert({ event: 'factory_recovered', reason: 'x' }, { direct: s.direct, n8n: s.n8n, n8nOptions: opts });
  assert.equal(out.channel, 'n8n_relay');
  assert.equal(out.delivered, 'unconfirmed');
  assert.equal(out.direct_error, 'not configured');
  assert.deepEqual(s.calls.relay[0].opts, opts);
});

test('both paths failing reports not delivered and never throws', async () => {
  const throwing = { sendTelegramMessage: async () => { throw new Error('boom'); } };
  const s = stubs({ directSent: false, relaySuccess: false });
  const logs = [];
  const out = await sendFounderAlert({ event: 'x' }, { direct: throwing, n8n: s.n8n, log: (e) => logs.push(e) });
  assert.equal(out.delivered, false);
  assert.equal(out.channel, 'none');
  assert.equal(out.direct_error, 'boom');
  assert.equal(logs[0].event, 'not_delivered');
});

test('unstubbed real senders are blocked under the test runner', async () => {
  assert.ok(process.env.NODE_TEST_CONTEXT, 'run with node --test');
  const out = await sendFounderAlert({ event: 'sale_detected', total_new_sales: 1 });
  assert.equal(out.delivered, false);
  assert.equal(out.direct_error, 'real send blocked under test runner');
  assert.equal(out.relay.reason, 'real relay blocked under test runner');
});

test('texts match the n8n 04_Telegram_Notify template', () => {
  assert.equal(formatFounderAlert({ event: 'golden_opportunity_accepted', niche: 'N', opportunity_score: 80, price: 19 }),
    '🏆 الصياد الذهبي قبل فرصة جديدة\n\nالمجال: N\nالنقاط: 80/100\nالسعر المقترح: $19');
  assert.equal(formatFounderAlert({ event: 'recovery_completed' }), '✅ اكتملت عملية الاسترجاع\n\nالمرحلة: غير محددة');
  assert.equal(formatFounderAlert({ event: 'pending_review_needed', count: 2 }), '📝 منتج جاهز للمراجعة\n\nيوجد 2 مسودة بانتظار المراجعة البشرية');
  assert.equal(formatFounderAlert({ event: 'unknown_evt' }), '📩 إشعار من Galaxy Forge: unknown_evt');
});
