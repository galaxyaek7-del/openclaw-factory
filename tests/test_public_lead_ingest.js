'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const {
  MAX_BODY_BYTES,
  handleLeadRequest,
  validatePayload,
} = require('../cloudflare/lead-ingest/src/core.js');

const ALLOWED_ORIGIN = 'https://galaxyaek7-del.github.io';

class MemoryKV {
  constructor() {
    this.data = new Map();
  }

  async get(key) {
    return this.data.has(key) ? this.data.get(key) : null;
  }

  async put(key, value) {
    this.data.set(key, String(value));
  }
}

function makeEnv(overrides) {
  return {
    LEADS: new MemoryKV(),
    PUBLIC_LEAD_INGEST_ENABLED: 'true',
    ...(overrides || {}),
  };
}

function makeRequest(options) {
  const opts = options || {};
  const headers = {
    'Content-Type': 'application/json',
    Origin: ALLOWED_ORIGIN,
    ...(opts.headers || {}),
  };
  const init = { method: opts.method || 'POST', headers };
  if (init.method !== 'GET' && init.method !== 'HEAD' && init.method !== 'OPTIONS') {
    init.body = opts.rawBody !== undefined ? opts.rawBody : JSON.stringify(opts.body || {});
  }
  return new Request('https://lead.example/lead', init);
}

function baseBody(overrides) {
  return {
    name: 'Amina',
    email: 'amina@example.com',
    message: 'Please send the EU AI Act toolkit details.',
    product_interest: 'EU AI Act toolkit',
    source: 'eu_ai_act_compliance_toolkit',
    ...(overrides || {}),
  };
}

function deps(overrides) {
  return {
    now: () => 1700000000000,
    idFactory: () => 'lead_test_1',
    ...(overrides || {}),
  };
}

test('public lead ingest is disabled by default and writes nothing', async () => {
  const env = makeEnv({ PUBLIC_LEAD_INGEST_ENABLED: 'false' });
  const response = await handleLeadRequest(makeRequest({ body: baseBody() }), env, deps());
  const body = await response.json();

  assert.equal(response.status, 503);
  assert.equal(body.success, false);
  assert.equal(body.status, 'disabled');
  assert.equal(env.LEADS.data.size, 0);
});

test('enabled ingest stores an unverified external lead and never counts it as demand', async () => {
  const env = makeEnv();
  const response = await handleLeadRequest(makeRequest({ body: baseBody() }), env, deps());
  const body = await response.json();

  assert.equal(response.status, 200);
  assert.equal(body.success, true);
  assert.equal(body.status, 'accepted');
  assert.equal(body.verification_status, 'UNVERIFIED_EXTERNAL');
  assert.equal(body.counted_as_demand, false);
  assert.equal(body.lead_id, 'lead_test_1');
  assert.equal(body.signal_id, 'lead_test_1');

  const record = JSON.parse(await env.LEADS.get('lead:lead_test_1'));
  assert.equal(record.verification_status, 'UNVERIFIED_EXTERNAL');
  assert.equal(record.provenance_quality, 'external_unverified');
  assert.equal(record.counted_as_demand, false);
  assert.equal(record.synthetic, false);
  assert.equal(record.email, 'amina@example.com');
  assert.equal(record.product_interest, 'EU AI Act toolkit');
  assert.equal(record.source, 'eu_ai_act_compliance_toolkit');
});

test('the worker accepts the local API interest alias and product_id alias', () => {
  const ok = validatePayload({
    email: 'a@example.com',
    interest: 'Please send the checklist',
    product_id: 'gpsr_checklist',
  });
  assert.equal(ok.ok, true);
  assert.equal(ok.lead.message, 'Please send the checklist');
  assert.equal(ok.lead.product_interest, 'gpsr_checklist');
});

test('the worker never stores the raw client IP', async () => {
  const env = makeEnv();
  const response = await handleLeadRequest(makeRequest({
    body: baseBody(),
    headers: { 'CF-Connecting-IP': '203.0.113.9' },
  }), env, deps());

  assert.equal(response.status, 200);
  const recordText = await env.LEADS.get('lead:lead_test_1');
  const record = JSON.parse(recordText);
  assert.match(record.ip_hash, /^[0-9a-f]{64}$/);
  assert.equal(Object.prototype.hasOwnProperty.call(record, 'ip'), false);
  assert.equal(recordText.includes('203.0.113.9'), false);
});

test('the honeypot is ignored without storing', async () => {
  const env = makeEnv();
  const response = await handleLeadRequest(makeRequest({
    body: baseBody({ website: 'https://spam.example' }),
  }), env, deps());
  const body = await response.json();

  assert.equal(response.status, 200);
  assert.equal(body.status, 'ignored');
  assert.equal(env.LEADS.data.size, 0);
});

test('invalid email and excessive links are rejected', async () => {
  const env = makeEnv();
  const badEmail = await handleLeadRequest(makeRequest({
    body: baseBody({ email: 'not-an-email' }),
  }), env, deps());
  const badEmailBody = await badEmail.json();
  assert.equal(badEmail.status, 400);
  assert.equal(badEmailBody.error, 'valid_email_required');

  const links = await handleLeadRequest(makeRequest({
    body: baseBody({ message: 'https://a.example https://b.example https://c.example https://d.example' }),
  }), env, deps());
  const linksBody = await links.json();
  assert.equal(links.status, 400);
  assert.equal(linksBody.error, 'too_many_links');
  assert.equal(env.LEADS.data.size, 0);
});

test('oversized bodies and non-JSON content are rejected before storage', async () => {
  const env = makeEnv();
  const oversized = await handleLeadRequest(makeRequest({
    rawBody: JSON.stringify({ email: 'a@example.com', message: 'x'.repeat(MAX_BODY_BYTES) }),
  }), env, deps());
  assert.equal(oversized.status, 413);

  const text = await handleLeadRequest(makeRequest({
    body: baseBody(),
    headers: { 'Content-Type': 'text/plain' },
  }), env, deps());
  assert.equal(text.status, 415);
  assert.equal(env.LEADS.data.size, 0);
});

test('disallowed origins are rejected and allowed origins get CORS', async () => {
  const env = makeEnv();
  const denied = await handleLeadRequest(makeRequest({
    body: baseBody(),
    headers: { Origin: 'https://evil.example' },
  }), env, deps());
  assert.equal(denied.status, 403);
  assert.equal(env.LEADS.data.size, 0);

  const allowed = await handleLeadRequest(makeRequest({ body: baseBody() }), env, deps());
  assert.equal(allowed.status, 200);
  assert.equal(allowed.headers.get('access-control-allow-origin'), ALLOWED_ORIGIN);
});

test('OPTIONS preflight succeeds for the public site', async () => {
  const env = makeEnv();
  const response = await handleLeadRequest(makeRequest({
    method: 'OPTIONS',
    headers: { Origin: ALLOWED_ORIGIN },
  }), env, deps());

  assert.equal(response.status, 204);
  assert.equal(response.headers.get('access-control-allow-origin'), ALLOWED_ORIGIN);
});

test('rate limit stops the sixth submission in a ten-minute window', async () => {
  const env = makeEnv();
  let counter = 0;
  const localDeps = deps({ idFactory: () => `lead_${++counter}` });

  for (let i = 0; i < 5; i += 1) {
    const response = await handleLeadRequest(makeRequest({
      body: baseBody({ message: `Message number ${i}` }),
    }), env, localDeps);
    assert.equal(response.status, 200);
  }

  const limited = await handleLeadRequest(makeRequest({
    body: baseBody({ message: 'Message number six' }),
  }), env, localDeps);
  const body = await limited.json();
  assert.equal(limited.status, 429);
  assert.equal(body.status, 'rate_limited');
  assert.equal(typeof body.retry_after_seconds, 'number');
});

test('duplicate submissions return the first lead id without storing twice', async () => {
  const env = makeEnv();
  const first = await handleLeadRequest(makeRequest({ body: baseBody() }), env, deps());
  assert.equal((await first.json()).status, 'accepted');

  const second = await handleLeadRequest(makeRequest({ body: baseBody() }), env, deps({
    idFactory: () => 'lead_test_2',
  }));
  const body = await second.json();
  assert.equal(second.status, 200);
  assert.equal(body.status, 'duplicate');
  assert.equal(body.lead_id, 'lead_test_1');
  assert.equal(body.counted_as_demand, false);

  const leadKeys = Array.from(env.LEADS.data.keys()).filter((key) => key.startsWith('lead:'));
  assert.deepEqual(leadKeys, ['lead:lead_test_1']);
});

test('Turnstile is required when configured and verified before storage', async () => {
  const env = makeEnv({ TURNSTILE_SECRET: 'test-secret' });
  const missing = await handleLeadRequest(makeRequest({ body: baseBody() }), env, deps());
  const missingBody = await missing.json();
  assert.equal(missing.status, 400);
  assert.equal(missingBody.error, 'turnstile_required');
  const leadKeys = Array.from(env.LEADS.data.keys()).filter((key) => key.startsWith('lead:'));
  assert.deepEqual(leadKeys, []);

  const verified = await handleLeadRequest(makeRequest({
    body: baseBody({ turnstile_token: 'token' }),
  }), env, deps({
    fetchImpl: async () => new Response(JSON.stringify({ success: true }), { status: 200 }),
  }));
  assert.equal(verified.status, 200);
  assert.equal((await verified.json()).status, 'accepted');
});

test('validation accepts a normal payload and rejects a missing message', () => {
  const ok = validatePayload(baseBody());
  assert.equal(ok.ok, true);
  assert.equal(ok.lead.email, 'amina@example.com');

  const missing = validatePayload({ email: 'a@example.com' });
  assert.equal(missing.ok, false);
  assert.equal(missing.error, 'message_required');
});
