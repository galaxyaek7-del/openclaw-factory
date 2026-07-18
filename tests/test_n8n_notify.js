// Tests for lib/n8n_notify.js (n8n Integration Gap fix).
// Uses Node's built-in test runner (node:test), same convention as
// tests/test_metrics.js/test_dashboard_data.js. No real network calls —
// global.fetch is mocked and restored around every test.
//
//   node --test tests/test_n8n_notify.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const {
  notifyN8nProductionEvent, buildProductionNotifyPayload, buildGoldenHunterNotifyPayload,
  buildFactoryStoppedUnexpectedlyPayload, buildFactoryRecoveredPayload,
  buildRecoveryCompletedPayload, buildRetryQueueStatusPayload,
} = require('../lib/n8n_notify.js');
const factoryState = require('../lib/factory_state.js');

function tempStatePath() {
  return path.join(os.tmpdir(), `n8n_notify_test_state_${Date.now()}_${Math.random().toString(36).slice(2)}.json`);
}

function withMockedFetch(impl, fn) {
  const original = global.fetch;
  global.fetch = impl;
  return fn().finally(() => { global.fetch = original; });
}

test('no webhookUrl configured -> no-ops, never calls fetch, never throws', async () => {
  let fetchCalled = false;
  await withMockedFetch(
    async () => { fetchCalled = true; throw new Error('fetch must not be called'); },
    async () => {
      const logs = [];
      const result = await notifyN8nProductionEvent({ event: 'x' }, { webhookUrl: null, log: (e) => logs.push(e) });
      assert.deepEqual(result, { attempted: false, reason: 'N8N_PRODUCTION_WEBHOOK_URL not configured' });
      assert.equal(fetchCalled, false);
      assert.equal(logs.length, 1);
      assert.equal(logs[0].event, 'skipped');
    }
  );
});

test('successful POST -> attempted true, success true, logs succeeded with status/duration', async () => {
  await withMockedFetch(
    async (url, opts) => {
      assert.equal(url, 'http://localhost:5678/webhook/production-notify');
      assert.equal(opts.method, 'POST');
      assert.equal(JSON.parse(opts.body).event, 'production_dossier_completed');
      return { ok: true, status: 200 };
    },
    async () => {
      const logs = [];
      const result = await notifyN8nProductionEvent(
        { event: 'production_dossier_completed', niche: 'x' },
        { webhookUrl: 'http://localhost:5678/webhook/production-notify', log: (e) => logs.push(e) }
      );
      assert.deepEqual(result, { attempted: true, success: true, status: 200 });
      assert.equal(logs.length, 1);
      assert.equal(logs[0].event, 'succeeded');
      assert.equal(logs[0].status, 200);
      assert.equal(typeof logs[0].duration_ms, 'number');
    }
  );
});

test('non-2xx response -> attempted true, success false, logs failed with status', async () => {
  await withMockedFetch(
    async () => ({ ok: false, status: 500 }),
    async () => {
      const logs = [];
      const result = await notifyN8nProductionEvent({ event: 'x' }, { webhookUrl: 'http://x', log: (e) => logs.push(e) });
      assert.deepEqual(result, { attempted: true, success: false, status: 500 });
      assert.equal(logs[0].event, 'failed');
      assert.equal(logs[0].status, 500);
    }
  );
});

test('network error (unreachable n8n) -> never throws, reports success false with the real error message', async () => {
  await withMockedFetch(
    async () => { throw new Error('ECONNREFUSED'); },
    async () => {
      const logs = [];
      const result = await notifyN8nProductionEvent({ event: 'x' }, { webhookUrl: 'http://x', log: (e) => logs.push(e) });
      assert.equal(result.attempted, true);
      assert.equal(result.success, false);
      assert.equal(result.error, 'ECONNREFUSED');
      assert.equal(logs[0].event, 'error');
    }
  );
});

test('timeout aborts the request and is reported as a non-throwing failure', async () => {
  await withMockedFetch(
    (url, opts) => new Promise((resolve, reject) => {
      opts.signal.addEventListener('abort', () => reject(new Error('The operation was aborted')));
    }),
    async () => {
      const logs = [];
      const result = await notifyN8nProductionEvent(
        { event: 'x' },
        { webhookUrl: 'http://x', timeoutMs: 20, log: (e) => logs.push(e) }
      );
      assert.equal(result.attempted, true);
      assert.equal(result.success, false);
      assert.ok(result.error);
    }
  );
});

test('buildProductionNotifyPayload: projects the real production_factory dossier fields server.js relies on', () => {
  // Synthetic fixture matching production_factory/dossier.py's real,
  // documented field names (production_id, generated_at, niche,
  // pricing_strategy.recommended_price, pre_production_verification.
  // all_checks_passed) — not a claim about any real business opportunity.
  const dossier = {
    production_id: 'prod-abc123',
    generated_at: '2026-07-16T12:00:00.000Z',
    niche: 'test niche (synthetic fixture)',
    pricing_strategy: { recommended_price: 19 },
    pre_production_verification: { all_checks_passed: true },
  };
  const payload = buildProductionNotifyPayload(dossier);
  assert.deepEqual(payload, {
    event: 'production_dossier_completed',
    production_id: 'prod-abc123',
    niche: 'test niche (synthetic fixture)',
    generated_at: '2026-07-16T12:00:00.000Z',
    recommended_price: 19,
    pre_production_checks_passed: true,
  });
});

test('buildProductionNotifyPayload: missing nested fields degrade to null, never throw', () => {
  const dossier = { production_id: 'p2', generated_at: 't', niche: 'n' };
  const payload = buildProductionNotifyPayload(dossier);
  assert.equal(payload.recommended_price, null);
  assert.equal(payload.pre_production_checks_passed, null);
});

test('envVarName lets a second caller report an accurate reason for its own webhook var', async () => {
  let fetchCalled = false;
  await withMockedFetch(
    async () => { fetchCalled = true; throw new Error('fetch must not be called'); },
    async () => {
      const result = await notifyN8nProductionEvent(
        { event: 'golden_opportunity_accepted' },
        { webhookUrl: null, envVarName: 'N8N_TELEGRAM_WEBHOOK_URL' }
      );
      assert.deepEqual(result, { attempted: false, reason: 'N8N_TELEGRAM_WEBHOOK_URL not configured' });
      assert.equal(fetchCalled, false);
    }
  );
});

// ADR-065 Step 3(a) — factory_loop.js's Golden Hunter Bridge notify.
test('buildGoldenHunterNotifyPayload: projects a real opportunity_score() result', () => {
  const opportunityScore = { score: 85.3, reason: 'accepted: opportunity_score 85.3/100 (raw 106.6 >= 81.2 floor, tier=tier4)' };
  const payload = buildGoldenHunterNotifyPayload('AI-powered compliance automation subscription system', opportunityScore);
  assert.equal(payload.event, 'golden_opportunity_accepted');
  assert.equal(payload.niche, 'AI-powered compliance automation subscription system');
  assert.equal(payload.opportunity_score, 85.3);
  assert.equal(payload.reason, opportunityScore.reason);
  assert.ok(payload.generated_at);
});

// ADR-073 (mission follow-up, 2026-07-18): the "key numbers" a Telegram
// notification shows now include price, not just score.
test('buildGoldenHunterNotifyPayload: carries price when the ladder gate produced one', () => {
  const opportunityScore = { score: 85.3, price: 388, reason: 'accepted: ladder_score 85.3/100 >= 65, price $388 >= $97 (ladder=ai_saas)' };
  const payload = buildGoldenHunterNotifyPayload('x', opportunityScore);
  assert.equal(payload.price, 388);
});

test('buildGoldenHunterNotifyPayload: price is omitted (not "undefined") when the old tier gate produced no price', () => {
  const opportunityScore = { score: 70, reason: 'accepted: opportunity_score 70/100 (tier=tier4)' };
  const payload = buildGoldenHunterNotifyPayload('x', opportunityScore);
  assert.equal(payload.price, undefined);
  assert.equal(JSON.stringify(payload).includes('"price"'), false);
});

test('payload is sent as the real, unmodified JSON body (no field renaming/dropping)', async () => {
  const payload = {
    event: 'production_dossier_completed',
    production_id: 'p1',
    niche: 'real niche',
    generated_at: '2026-07-16T00:00:00.000Z',
    recommended_price: 19,
    pre_production_checks_passed: true,
  };
  await withMockedFetch(
    async (url, opts) => {
      assert.deepEqual(JSON.parse(opts.body), payload);
      return { ok: true, status: 200 };
    },
    async () => {
      await notifyN8nProductionEvent(payload, { webhookUrl: 'http://x' });
    }
  );
});

// Unified Recovery System §4 (2026-07-18) — the 4 new founder-facing
// "the factory itself" events.

test('buildFactoryStoppedUnexpectedlyPayload: carries the reason and the interrupted task', () => {
  const currentTask = { name: 'production', step: null, idempotency_key: 'abc123' };
  const payload = buildFactoryStoppedUnexpectedlyPayload('unresolved production stage', currentTask);
  assert.equal(payload.event, 'factory_stopped_unexpectedly');
  assert.equal(payload.reason, 'unresolved production stage');
  assert.deepEqual(payload.current_task, currentTask);
  assert.ok(payload.generated_at);
});

test('buildFactoryStoppedUnexpectedlyPayload: a null current_task is honest, never fabricated', () => {
  const payload = buildFactoryStoppedUnexpectedlyPayload('x', null);
  assert.equal(payload.current_task, null);
});

test('buildFactoryRecoveredPayload: carries the reason and the resumed task', () => {
  const currentTask = { name: 'decision', step: null };
  const payload = buildFactoryRecoveredPayload('safe to auto-resume', currentTask);
  assert.equal(payload.event, 'factory_recovered');
  assert.equal(payload.reason, 'safe to auto-resume');
  assert.deepEqual(payload.current_task, currentTask);
});

test('buildRecoveryCompletedPayload: carries the stage and idempotency key', () => {
  const payload = buildRecoveryCompletedPayload('production', 'key1');
  assert.equal(payload.event, 'recovery_completed');
  assert.equal(payload.stage, 'production');
  assert.equal(payload.idempotency_key, 'key1');
});

test('buildRecoveryCompletedPayload: missing fields degrade to null, never throw', () => {
  const payload = buildRecoveryCompletedPayload();
  assert.equal(payload.stage, null);
  assert.equal(payload.idempotency_key, null);
});

test('buildRetryQueueStatusPayload: reports counts grouped by task prefix, never every item', () => {
  const pendingRetries = [
    { task: 'groq_generation' },
    { task: 'arm_publish:paddle:PROD-1' },
    { task: 'arm_publish:paddle:PROD-2' },
    { task: 'telegram_notify:factory_recovered' },
  ];
  const payload = buildRetryQueueStatusPayload(pendingRetries);
  assert.equal(payload.event, 'retry_queue_status');
  assert.equal(payload.pending_count, 4);
  assert.deepEqual(payload.by_task, { groq_generation: 1, arm_publish: 2, telegram_notify: 1 });
});

test('buildRetryQueueStatusPayload: an empty queue reports zero, never throws', () => {
  const payload = buildRetryQueueStatusPayload([]);
  assert.equal(payload.pending_count, 0);
  assert.deepEqual(payload.by_task, {});
});

test('buildRetryQueueStatusPayload: missing/undefined input degrades to an empty report', () => {
  const payload = buildRetryQueueStatusPayload(undefined);
  assert.equal(payload.pending_count, 0);
});

// Unified Recovery System §3 (2026-07-18) — a real notify failure is
// remembered for a later retry, never just lost.

test('a non-2xx response enqueues a retry for this event', async () => {
  const statePath = tempStatePath();
  try {
    await withMockedFetch(
      async () => ({ ok: false, status: 500 }),
      async () => {
        await notifyN8nProductionEvent({ event: 'recovery_completed' }, { webhookUrl: 'http://x', statePath });
      }
    );
    const due = factoryState.dueRetries(statePath);
    assert.equal(due.length, 1);
    assert.equal(due[0].task, 'telegram_notify:recovery_completed');
    assert.match(due[0].last_error, /500/);
  } finally {
    if (fs.existsSync(statePath)) fs.unlinkSync(statePath);
  }
});

test('an unreachable n8n enqueues a retry for this event', async () => {
  const statePath = tempStatePath();
  try {
    await withMockedFetch(
      async () => { throw new Error('ECONNREFUSED'); },
      async () => {
        await notifyN8nProductionEvent({ event: 'factory_recovered' }, { webhookUrl: 'http://x', statePath });
      }
    );
    const due = factoryState.dueRetries(statePath);
    assert.equal(due.length, 1);
    assert.equal(due[0].task, 'telegram_notify:factory_recovered');
    assert.match(due[0].last_error, /ECONNREFUSED/);
  } finally {
    if (fs.existsSync(statePath)) fs.unlinkSync(statePath);
  }
});

test('a successful notify never enqueues a retry', async () => {
  const statePath = tempStatePath();
  try {
    await withMockedFetch(
      async () => ({ ok: true, status: 200 }),
      async () => {
        await notifyN8nProductionEvent({ event: 'factory_recovered' }, { webhookUrl: 'http://x', statePath });
      }
    );
    assert.equal(fs.existsSync(statePath), false, 'a successful notify must never write a retry-queue file at all');
  } finally {
    if (fs.existsSync(statePath)) fs.unlinkSync(statePath);
  }
});

test('a no-webhook-configured no-op never enqueues a retry', async () => {
  const statePath = tempStatePath();
  try {
    await notifyN8nProductionEvent({ event: 'factory_recovered' }, { webhookUrl: null, statePath });
    assert.equal(fs.existsSync(statePath), false);
  } finally {
    if (fs.existsSync(statePath)) fs.unlinkSync(statePath);
  }
});
