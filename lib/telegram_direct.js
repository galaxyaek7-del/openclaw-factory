// Direct Telegram send — bypasses n8n entirely (ADR-085's JS counterpart
// to channels/telegram_direct.py). Every existing Telegram notification
// routed through n8n (ADR-073) depends on n8n both running and its
// 04_Telegram_Notify workflow staying toggled Active — a real, repeatedly-
// confirmed one-click platform requirement (ADR-072) that a stale browser
// tab has already silently reverted once (ADR-073's own postmortem). This
// module sends the same real, critical events directly via Telegram's Bot
// API instead, so they land even when n8n is down or its workflow has
// drifted inactive.
//
// Deliberately fail-safe, same contract as lib/n8n_notify.js's
// notifyN8nProductionEvent(): missing config or a network failure is
// reported, never thrown — a real event (a sale happened, a product is
// ready, the factory hit a real error) must never be lost or crash its
// caller just because a Telegram send failed.

const DEFAULT_TIMEOUT_MS = 5000;

async function sendTelegramMessage(text, {
  token = process.env.TELEGRAM_BOT_TOKEN,
  chatId = process.env.OPENCLAW_TELEGRAM_CHAT_ID,
  timeoutMs = DEFAULT_TIMEOUT_MS,
  log = () => {},
} = {}) {
  if (!token || !chatId) {
    log({ event: 'skipped', reason: 'TELEGRAM_BOT_TOKEN or OPENCLAW_TELEGRAM_CHAT_ID not configured' });
    return { sent: false, message_id: null, error: 'TELEGRAM_BOT_TOKEN or OPENCLAW_TELEGRAM_CHAT_ID not configured' };
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId, text }),
      signal: controller.signal,
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok || !body.ok) {
      const error = (body && body.description) || `HTTP ${res.status}`;
      log({ event: 'failed', error });
      return { sent: false, message_id: null, error };
    }
    log({ event: 'succeeded', message_id: body.result && body.result.message_id });
    return { sent: true, message_id: body.result && body.result.message_id, error: null };
  } catch (err) {
    log({ event: 'error', error: err.message });
    return { sent: false, message_id: null, error: err.message };
  } finally {
    clearTimeout(timer);
  }
}

// ADR-073's standing principle applied to the 3 events it named but left
// unwired: clear Arabic, key numbers, no English-then-translated text.

function buildProductReadyMessage(dossier) {
  const price = dossier.pricing_strategy && dossier.pricing_strategy.recommended_price;
  const lines = [
    '📄 منتج جاهز للمراجعة',
    '',
    `النيتش: ${dossier.niche}`,
  ];
  if (price != null) lines.push(`السعر الموصى به: $${price}`);
  lines.push(`رقم الإنتاج: ${dossier.production_id}`);
  return lines.join('\n');
}

function buildSaleMadeMessage(sale) {
  const lines = [
    '💰 بيع جديد!',
    '',
    `المنصة: ${sale.platform}`,
  ];
  if (sale.amount != null) lines.push(`المبلغ: $${sale.amount}`);
  if (sale.title) lines.push(`المنتج: ${sale.title}`);
  return lines.join('\n');
}

function buildCriticalErrorMessage(reasons) {
  const lines = [
    '🚨 عطل حرج',
    '',
    reasons[0],
  ];
  if (reasons.length > 1) lines.push(`(+${reasons.length - 1} سبب إضافي — راجع NEEDS_ATTENTION.md)`);
  return lines.join('\n');
}

module.exports = {
  sendTelegramMessage,
  buildProductReadyMessage,
  buildSaleMadeMessage,
  buildCriticalErrorMessage,
  DEFAULT_TIMEOUT_MS,
};
