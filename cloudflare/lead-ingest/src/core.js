'use strict';

const MAX_BODY_BYTES = 8192;
const MAX_NAME = 200;
const MAX_MESSAGE = 4000;
const MAX_PRODUCT_INTEREST = 2000;
const MAX_SOURCE = 80;
const MAX_CAMPAIGN = 80;
const MAX_PAGE = 200;
const MAX_LINKS = 3;
const RATE_LIMIT_MAX = 5;
const RATE_LIMIT_WINDOW_SECONDS = 600;
const DEDUP_TTL_SECONDS = 30 * 24 * 60 * 60;
const ALLOWED_ORIGINS = new Set([
  'https://galaxyaek7-del.github.io',
  'http://localhost:3000',
  'http://127.0.0.1:3000',
]);
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function isEnabled(env) {
  return String((env && env.PUBLIC_LEAD_INGEST_ENABLED) || '').toLowerCase() === 'true';
}

function corsHeaders(origin) {
  const headers = {
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Vary': 'Origin',
  };
  if (origin && ALLOWED_ORIGINS.has(origin)) {
    headers['Access-Control-Allow-Origin'] = origin;
  }
  return headers;
}

function jsonResponse(status, payload, origin) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store',
      'X-Content-Type-Options': 'nosniff',
      ...corsHeaders(origin),
    },
  });
}

function preflightResponse(origin) {
  return new Response(null, { status: 204, headers: corsHeaders(origin) });
}

async function sha256Hex(value) {
  const bytes = new TextEncoder().encode(String(value));
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, '0')).join('');
}

function clientIp(request) {
  const direct = request.headers.get('CF-Connecting-IP');
  if (direct) return direct;
  const forwarded = request.headers.get('X-Forwarded-For');
  if (forwarded) return forwarded.split(',')[0].trim();
  return 'unknown';
}

function validatePayload(payload) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    return { ok: false, error: 'invalid_json' };
  }
  if (payload.website) {
    return { ok: false, ignored: true };
  }

  const email = String(payload.email || '').trim().toLowerCase();
  const message = String(payload.message || payload.interest || '').trim();
  const name = String(payload.name || '').trim();
  const productInterest = String(payload.product_interest || payload.product_id || '').trim();
  const source = String(payload.source || 'customer_site').trim();
  const campaign = String(payload.campaign || '').trim();
  const page = String(payload.page || '').trim();

  if (!email || email.length > 254 || !EMAIL_RE.test(email)) {
    return { ok: false, error: 'valid_email_required' };
  }
  if (!message) {
    return { ok: false, error: 'message_required' };
  }
  if (message.length > MAX_MESSAGE) {
    return { ok: false, error: 'message_too_long' };
  }
  if (name.length > MAX_NAME) {
    return { ok: false, error: 'name_too_long' };
  }
  if (productInterest.length > MAX_PRODUCT_INTEREST) {
    return { ok: false, error: 'product_interest_too_long' };
  }
  if (source.length > MAX_SOURCE) {
    return { ok: false, error: 'source_too_long' };
  }
  if (campaign.length > MAX_CAMPAIGN) {
    return { ok: false, error: 'campaign_too_long' };
  }
  if (page.length > MAX_PAGE) {
    return { ok: false, error: 'page_too_long' };
  }
  const links = (message.match(/https?:\/\//gi) || []).length;
  if (links > MAX_LINKS) {
    return { ok: false, error: 'too_many_links' };
  }

  return {
    ok: true,
    lead: {
      email,
      message,
      name: name || null,
      product_interest: productInterest || null,
      source: source || 'customer_site',
      campaign: campaign || null,
      page: page || null,
    },
  };
}

async function checkRateLimit(env, ipHash, nowMs) {
  if (!env || !env.LEADS || typeof env.LEADS.get !== 'function' || typeof env.LEADS.put !== 'function') {
    return { ok: false, error: 'storage_unavailable' };
  }
  const window = Math.floor(nowMs / (RATE_LIMIT_WINDOW_SECONDS * 1000));
  const key = `rate:${ipHash}:${window}`;
  try {
    const raw = await env.LEADS.get(key);
    const count = Number(raw || 0);
    if (count >= RATE_LIMIT_MAX) {
      const retryAfter = RATE_LIMIT_WINDOW_SECONDS - Math.floor((nowMs / 1000) % RATE_LIMIT_WINDOW_SECONDS);
      return { ok: false, error: 'rate_limited', retryAfter };
    }
    await env.LEADS.put(key, String(count + 1), { expirationTtl: RATE_LIMIT_WINDOW_SECONDS + 60 });
    return { ok: true };
  } catch (_) {
    return { ok: false, error: 'storage_unavailable' };
  }
}

async function verifyTurnstile(env, token, ip, fetchImpl) {
  if (!env || !env.TURNSTILE_SECRET) {
    return { ok: true, skipped: true };
  }
  if (!token) {
    return { ok: false, error: 'turnstile_required' };
  }
  try {
    const body = new URLSearchParams({
      secret: env.TURNSTILE_SECRET,
      response: String(token),
      remoteip: String(ip || ''),
    });
    const response = await fetchImpl('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
      method: 'POST',
      body,
    });
    const result = await response.json();
    return result && result.success === true ? { ok: true } : { ok: false, error: 'turnstile_failed' };
  } catch (_) {
    return { ok: false, error: 'turnstile_unavailable' };
  }
}

function leadId(nowMs, idFactory) {
  if (typeof idFactory === 'function') return idFactory();
  const random = crypto.randomUUID ? crypto.randomUUID().replace(/-/g, '').slice(0, 12) : String(Math.random()).slice(2, 14);
  return `lead_${nowMs}_${random}`;
}

async function handleLeadRequest(request, env, deps) {
  const origin = request.headers.get('Origin') || '';
  const nowMs = deps && typeof deps.now === 'function' ? deps.now() : Date.now();
  const fetchImpl = (deps && deps.fetchImpl) || fetch;
  const idFactory = deps && deps.idFactory;

  if (request.method === 'OPTIONS') {
    if (origin && !ALLOWED_ORIGINS.has(origin)) {
      return jsonResponse(403, { success: false, status: 'rejected', error: 'origin_not_allowed' }, origin);
    }
    return preflightResponse(origin);
  }
  if (request.method !== 'POST') {
    return jsonResponse(405, { success: false, status: 'rejected', error: 'method_not_allowed' }, origin);
  }
  if (origin && !ALLOWED_ORIGINS.has(origin)) {
    return jsonResponse(403, { success: false, status: 'rejected', error: 'origin_not_allowed' }, origin);
  }
  if (!isEnabled(env)) {
    return jsonResponse(503, {
      success: false,
      status: 'disabled',
      error: 'public lead ingest is disabled',
    }, origin);
  }

  const declaredLength = Number(request.headers.get('Content-Length') || 0);
  if (declaredLength > MAX_BODY_BYTES) {
    return jsonResponse(413, { success: false, status: 'rejected', error: 'body_too_large' }, origin);
  }
  const contentType = String(request.headers.get('Content-Type') || '').toLowerCase();
  if (!contentType.includes('application/json')) {
    return jsonResponse(415, { success: false, status: 'rejected', error: 'json_required' }, origin);
  }

  let text;
  try {
    text = await request.text();
  } catch (_) {
    return jsonResponse(400, { success: false, status: 'rejected', error: 'invalid_body' }, origin);
  }
  if (new TextEncoder().encode(text).length > MAX_BODY_BYTES) {
    return jsonResponse(413, { success: false, status: 'rejected', error: 'body_too_large' }, origin);
  }

  let payload;
  try {
    payload = JSON.parse(text);
  } catch (_) {
    return jsonResponse(400, { success: false, status: 'rejected', error: 'invalid_json' }, origin);
  }

  const validation = validatePayload(payload);
  if (!validation.ok) {
    if (validation.ignored) {
      return jsonResponse(200, { success: true, status: 'ignored' }, origin);
    }
    return jsonResponse(400, { success: false, status: 'rejected', error: validation.error }, origin);
  }

  const ip = clientIp(request);
  const ipHash = await sha256Hex(`${ip}:${(env && env.LEAD_IP_SALT) || 'galaxyforge'}`);

  const rate = await checkRateLimit(env, ipHash, nowMs);
  if (!rate.ok) {
    if (rate.error === 'rate_limited') {
      return jsonResponse(429, {
        success: false,
        status: 'rate_limited',
        error: 'too many requests',
        retry_after_seconds: rate.retryAfter,
      }, origin);
    }
    return jsonResponse(503, { success: false, status: 'unavailable', error: 'storage_unavailable' }, origin);
  }

  const turnstile = await verifyTurnstile(env, payload.turnstile_token, ip, fetchImpl);
  if (!turnstile.ok) {
    return jsonResponse(400, { success: false, status: 'rejected', error: turnstile.error }, origin);
  }

  const dedupHash = await sha256Hex(`${validation.lead.email}|${validation.lead.message}`);
  const dedupKey = `dedup:${dedupHash}`;
  try {
    const existing = await env.LEADS.get(dedupKey);
    if (existing) {
      return jsonResponse(200, {
        success: true,
        status: 'duplicate',
        lead_id: existing,
        signal_id: existing,
        verification_status: 'UNVERIFIED_EXTERNAL',
        counted_as_demand: false,
      }, origin);
    }

    const id = leadId(nowMs, idFactory);
    const record = {
      lead_id: id,
      received_at: new Date(nowMs).toISOString(),
      email: validation.lead.email,
      name: validation.lead.name,
      message: validation.lead.message,
      product_interest: validation.lead.product_interest,
      source: validation.lead.source,
      campaign: validation.lead.campaign,
      page: validation.lead.page,
      verification_status: 'UNVERIFIED_EXTERNAL',
      provenance_quality: 'external_unverified',
      counted_as_demand: false,
      synthetic: false,
      ip_hash: ipHash,
      user_agent: String(request.headers.get('User-Agent') || '').slice(0, 200),
      country: request.cf && request.cf.country ? String(request.cf.country) : null,
    };
    await env.LEADS.put(`lead:${id}`, JSON.stringify(record), {
      metadata: { verification_status: 'UNVERIFIED_EXTERNAL' },
    });
    try {
      await env.LEADS.put(dedupKey, id, { expirationTtl: DEDUP_TTL_SECONDS });
    } catch (_) {
      // The lead is already stored; a dedup failure must not turn a stored
      // lead into a false error that pushes the visitor to the email fallback.
    }

    return jsonResponse(200, {
      success: true,
      status: 'accepted',
      lead_id: id,
      signal_id: id,
      verification_status: 'UNVERIFIED_EXTERNAL',
      counted_as_demand: false,
      note: 'Stored as an unverified external lead. It does not count as demand until a human proves it.',
    }, origin);
  } catch (_) {
    return jsonResponse(503, { success: false, status: 'unavailable', error: 'storage_unavailable' }, origin);
  }
}

module.exports = {
  ALLOWED_ORIGINS,
  MAX_BODY_BYTES,
  MAX_MESSAGE,
  MAX_PRODUCT_INTEREST,
  RATE_LIMIT_MAX,
  handleLeadRequest,
  isEnabled,
  validatePayload,
};
