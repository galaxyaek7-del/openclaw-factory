// Safe, optional, logged outbound notification from a real production
// event to n8n (n8n Integration Gap fix, Executive Directive "Fix the
// n8n integration gap"). No Express/http-server dependency — mirrors
// lib/metrics.js's convention — so it's unit-testable in isolation by
// mocking global.fetch, without booting a real server.
//
// n8n is used only as an orchestration/notification layer here: the
// payload passed in by the caller is a plain projection of an already-
// computed real dossier (production_factory) — this module makes no
// business decision of its own.
//
// Deliberately fail-safe: with no webhookUrl, this no-ops immediately
// (never attempts a network call, never throws). A real production run
// must never fail or block just because n8n isn't reachable or wired up
// yet — the underlying dossier this notifies about is already safely
// persisted regardless of whether n8n heard about it.

const factoryState = require('./factory_state');

const DEFAULT_TIMEOUT_MS = 5000;

async function notifyN8nProductionEvent(payload, {
  webhookUrl, timeoutMs = DEFAULT_TIMEOUT_MS, log = () => {},
  // ADR-065 Step 3(a): this sender is now shared by two different env vars
  // (server.js's N8N_PRODUCTION_WEBHOOK_URL and factory_loop.js's new
  // N8N_TELEGRAM_WEBHOOK_URL) — a caller can name which one it actually
  // read so the logged/returned reason stays accurate. Defaulting to the
  // original var name keeps every existing caller's message byte-for-byte
  // unchanged.
  envVarName = 'N8N_PRODUCTION_WEBHOOK_URL',
  // Unified Recovery System §3 (2026-07-18): forwarded to
  // factoryState.enqueueRetry() below purely for test isolation — omitting
  // it (every caller before this option existed) uses the real default
  // data/factory_state.json path, unchanged.
  statePath = undefined,
  // The retry attempt this call represents (1 = a fresh failure, not yet
  // retried). process_pending_retries() passes retry.attempt + 1 when
  // replaying a queued entry, so the backoff schedule actually escalates
  // across repeated failures instead of resetting to attempt 1 every time.
  attempt = 1,
} = {}) {
  if (!webhookUrl) {
    log({ event: 'skipped', reason: `${envVarName} not configured` });
    return { attempted: false, reason: `${envVarName} not configured` };
  }

  const startedAt = Date.now();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(webhookUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    const duration_ms = Date.now() - startedAt;
    if (!res.ok) {
      log({ event: 'failed', status: res.status, duration_ms });
      // Unified Recovery System §3: a real, reached-but-rejected n8n
      // response is remembered for a later retry — never silently lost.
      // context carries everything process_pending_retries() needs to
      // actually resend this exact message, not just count it.
      factoryState.enqueueRetry(`telegram_notify:${payload.event}`, `HTTP ${res.status}`, statePath, attempt, { payload, webhookUrl, envVarName });
      return { attempted: true, success: false, status: res.status };
    }
    log({ event: 'succeeded', status: res.status, duration_ms });
    return { attempted: true, success: true, status: res.status };
  } catch (err) {
    // Covers unreachable n8n, DNS failure, and the abort-on-timeout case
    // above — all real, recoverable, non-fatal conditions.
    const duration_ms = Date.now() - startedAt;
    log({ event: 'error', error: err.message, duration_ms });
    factoryState.enqueueRetry(`telegram_notify:${payload.event}`, err, statePath, attempt, { payload, webhookUrl, envVarName });
    return { attempted: true, success: false, error: err.message };
  } finally {
    clearTimeout(timer);
  }
}

// Pure field projection from a real production_factory dossier to the
// notify payload — no new business logic, just selecting the fields
// worth reporting. Only called for dossiers that exist (server.js only
// invokes this when result.processed > 0), so it never needs to handle
// "no dossiers" itself.
function buildProductionNotifyPayload(dossier) {
  return {
    event: 'production_dossier_completed',
    production_id: dossier.production_id,
    niche: dossier.niche,
    generated_at: dossier.generated_at,
    recommended_price: dossier.pricing_strategy?.recommended_price ?? null,
    pre_production_checks_passed: dossier.pre_production_verification?.all_checks_passed ?? null,
  };
}

// ADR-065 Step 3(a): same plain-projection pattern as
// buildProductionNotifyPayload() above, for factory_loop.js's Golden Hunter
// Bridge instead of server.js's production pipeline — a different real
// event (an opportunity clearing profit_oracle's acceptance gate), reusing
// the exact same generic notifyN8nProductionEvent() sender rather than a
// second HTTP-call implementation.
function buildGoldenHunterNotifyPayload(niche, opportunityScore) {
  return {
    event: 'golden_opportunity_accepted',
    niche,
    opportunity_score: opportunityScore.score,
    // ADR-073: price is only present when the gate that produced this
    // result was the ladder-aware one (getLadderOpportunityScore()) —
    // the older tier-based getOpportunityScore() has no price concept.
    // undefined here is dropped by JSON.stringify, so the receiving n8n
    // workflow's Arabic message template omits the price line cleanly
    // instead of showing "undefined".
    price: opportunityScore.price,
    reason: opportunityScore.reason,
    generated_at: new Date().toISOString(),
  };
}

// Unified Recovery System §4 (2026-07-18): 4 new founder-facing "the
// factory itself" events — same pure-payload-builder pattern as the two
// above, reusing the identical notifyN8nProductionEvent() sender. Routed
// through 03_Production_Notify/04_Telegram_Notify's already-present
// `event` field (today unused by either workflow's branching logic —
// this is what gives that field real purpose).

function buildFactoryStoppedUnexpectedlyPayload(reason, currentTask) {
  return {
    event: 'factory_stopped_unexpectedly',
    reason,
    current_task: currentTask || null,
    generated_at: new Date().toISOString(),
  };
}

function buildFactoryRecoveredPayload(reason, currentTask) {
  return {
    event: 'factory_recovered',
    reason,
    current_task: currentTask || null,
    generated_at: new Date().toISOString(),
  };
}

function buildRecoveryCompletedPayload(stage, idempotencyKey) {
  return {
    event: 'recovery_completed',
    stage: stage || null,
    idempotency_key: idempotencyKey || null,
    generated_at: new Date().toISOString(),
  };
}

// Reports counts, never every queued item — a retry queue can legitimately
// hold several entries at once, and a per-item Telegram message would
// spam the founder every tick it stays non-empty.
function buildRetryQueueStatusPayload(pendingRetries) {
  const byTask = {};
  for (const r of pendingRetries || []) {
    const key = (r.task || 'unknown').split(':')[0];
    byTask[key] = (byTask[key] || 0) + 1;
  }
  return {
    event: 'retry_queue_status',
    pending_count: (pendingRetries || []).length,
    by_task: byTask,
    generated_at: new Date().toISOString(),
  };
}

// "Nervous system" notifications, wave 2 (2026-07-19) — same pure-payload-
// builder pattern as every event above, closing the two gaps a live audit
// of 04_Telegram_Notify.prepared.json found: pending_review transitions
// only ever produced a desktop toast (sendDesktopNotification), never a
// Telegram message, and pollSales() detecting a real new sale produced no
// notification of any kind.

function buildPendingReviewNeededPayload(count) {
  return {
    event: 'pending_review_needed',
    count,
    generated_at: new Date().toISOString(),
  };
}

// outcomes: the same per-arm outcome array pollSales() already builds from
// /api/sales/poll's real response (arm, new_sales) — projected here, not
// recomputed.
function buildNewSaleDetectedPayload(outcomes, totalNewSales) {
  return {
    event: 'sale_detected',
    total_new_sales: totalNewSales,
    outcomes: (outcomes || []).filter(o => (o.new_sales || 0) > 0).map(o => ({ arm: o.arm, new_sales: o.new_sales })),
    generated_at: new Date().toISOString(),
  };
}

module.exports = {
  notifyN8nProductionEvent, buildProductionNotifyPayload,
  buildGoldenHunterNotifyPayload, DEFAULT_TIMEOUT_MS,
  buildFactoryStoppedUnexpectedlyPayload, buildFactoryRecoveredPayload,
  buildRecoveryCompletedPayload, buildRetryQueueStatusPayload,
  buildPendingReviewNeededPayload, buildNewSaleDetectedPayload,
};
