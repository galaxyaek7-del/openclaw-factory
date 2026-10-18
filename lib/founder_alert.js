'use strict';

// Founder alerts: direct Telegram first, n8n relay only as a fallback
// (Cycle 95 n8n engineering review, reports/governance/N8N_ENGINEERING_REVIEW_CYCLE95.md).
//
// Why: the n8n webhooks answer HTTP 200 on receipt, before their workflow
// runs, so a 200 from n8n is an acknowledgement, not a delivery. On
// 2026-10-10 19:37:11 the factory logged "succeeded" while the n8n execution
// failed in the same second. The direct Bot API path returns a real
// message_id, so it is tried first; n8n is used only when the direct path is
// not configured or fails, and its result is reported as acknowledged, never
// as delivered.

const telegramDirect = require('./telegram_direct');
const n8nNotify = require('./n8n_notify');

const ORIGINAL_DIRECT_SEND = telegramDirect.sendTelegramMessage;
const ORIGINAL_RELAY_SEND = n8nNotify.notifyN8nProductionEvent;

// Under `node --test` a founder alert must never reach the real Telegram chat
// or the real n8n webhook: a test that forgot to stub them would message the
// founder. Stubbed functions (patched on the module object) still run.
function blockedUnderTestRunner(fn, original) {
  return Boolean(process.env.NODE_TEST_CONTEXT) && fn === original;
}

// Same texts as the n8n workflow 04_Telegram_Notify "Build Telegram Message"
// node, so the founder sees identical messages whichever path delivers.
function formatFounderAlert(payload) {
  const p = payload || {};
  switch (p.event) {
    case 'golden_opportunity_accepted':
      return `🏆 الصياد الذهبي قبل فرصة جديدة\n\nالمجال: ${p.niche}\nالنقاط: ${p.opportunity_score}/100` +
        (p.price ? `\nالسعر المقترح: $${p.price}` : '');
    case 'factory_stopped_unexpectedly':
      return `🚨 عطل حرج — توقّف المصنع بشكل غير متوقع\n\nالسبب: ${p.reason}`;
    case 'factory_recovered':
      return `✅ تعافى المصنع وعاد للعمل\n\nالسبب: ${p.reason}`;
    case 'recovery_completed':
      return `✅ اكتملت عملية الاسترجاع\n\nالمرحلة: ${p.stage || 'غير محددة'}`;
    case 'retry_queue_status':
      return `🔁 حالة قائمة إعادة المحاولة\n\nعدد المهام المعلَّقة: ${p.pending_count}`;
    case 'pending_review_needed':
      return `📝 منتج جاهز للمراجعة\n\nيوجد ${p.count} مسودة بانتظار المراجعة البشرية`;
    case 'sale_detected':
      return `💰 بيع جديد!\n\nعدد المبيعات الجديدة: ${p.total_new_sales}`;
    default:
      return `📩 إشعار من Galaxy Forge: ${p.event}`;
  }
}

// Never throws. Returns { channel, delivered, ... }:
//   delivered: true        — Telegram returned a message_id
//   delivered: 'unconfirmed' — only n8n acknowledged receipt
//   delivered: false       — neither path accepted it
async function sendFounderAlert(payload, {
  n8nOptions = {},
  direct = telegramDirect,
  n8n = n8nNotify,
  log = () => {},
} = {}) {
  let directResult = null;
  try {
    directResult = blockedUnderTestRunner(direct.sendTelegramMessage, ORIGINAL_DIRECT_SEND)
      ? { sent: false, error: 'real send blocked under test runner' }
      : await direct.sendTelegramMessage(formatFounderAlert(payload));
  } catch (err) {
    directResult = { sent: false, error: err.message };
  }
  if (directResult && directResult.sent) {
    const out = { channel: 'telegram_direct', delivered: true, message_id: directResult.message_id };
    log({ event: 'delivered', channel: out.channel, message_id: out.message_id });
    return out;
  }

  let relay = null;
  try {
    relay = blockedUnderTestRunner(n8n.notifyN8nProductionEvent, ORIGINAL_RELAY_SEND)
      ? { attempted: false, reason: 'real relay blocked under test runner' }
      : await n8n.notifyN8nProductionEvent(payload, n8nOptions);
  } catch (err) {
    relay = { attempted: false, error: err.message };
  }
  const acknowledged = Boolean(relay && relay.success);
  const out = {
    channel: acknowledged ? 'n8n_relay' : 'none',
    delivered: acknowledged ? 'unconfirmed' : false,
    direct_error: (directResult && directResult.error) || null,
    relay,
  };
  log({ event: acknowledged ? 'relay_acknowledged_unconfirmed' : 'not_delivered',
    channel: out.channel, direct_error: out.direct_error });
  return out;
}

module.exports = { formatFounderAlert, sendFounderAlert };
