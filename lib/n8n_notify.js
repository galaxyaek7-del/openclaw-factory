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

const DEFAULT_TIMEOUT_MS = 5000;

async function notifyN8nProductionEvent(payload, { webhookUrl, timeoutMs = DEFAULT_TIMEOUT_MS, log = () => {} } = {}) {
  if (!webhookUrl) {
    log({ event: 'skipped', reason: 'N8N_PRODUCTION_WEBHOOK_URL not configured' });
    return { attempted: false, reason: 'N8N_PRODUCTION_WEBHOOK_URL not configured' };
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
      return { attempted: true, success: false, status: res.status };
    }
    log({ event: 'succeeded', status: res.status, duration_ms });
    return { attempted: true, success: true, status: res.status };
  } catch (err) {
    // Covers unreachable n8n, DNS failure, and the abort-on-timeout case
    // above — all real, recoverable, non-fatal conditions.
    const duration_ms = Date.now() - startedAt;
    log({ event: 'error', error: err.message, duration_ms });
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
    reason: opportunityScore.reason,
    generated_at: new Date().toISOString(),
  };
}

module.exports = {
  notifyN8nProductionEvent, buildProductionNotifyPayload,
  buildGoldenHunterNotifyPayload, DEFAULT_TIMEOUT_MS,
};
