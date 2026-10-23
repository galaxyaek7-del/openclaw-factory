// Galaxy Forge -- demand sensing from real questions people ask (2026-10-23).
//
// Google Trends' daily feed is people and news; after the commercial-intent
// filter (lib/trend_classifier.js) it yields almost nothing. This adds two
// free, read-only, no-account sources of real problems:
//   - Stack Exchange "hot" questions on freelancing, money, workplace,
//     project management and webmasters (api.stackexchange.com, no key);
//   - Ask HN posts from the last 7 days with real engagement (hn.algolia.com).
// Each new question goes through the SAME path as a Sensing trend: POST
// /api/trends (quality gate -> safety filter -> scout commercial check), so
// nothing reaches OPPORTUNITIES.md that the existing gates would not accept.
// Once per UTC day, at most MAX_PER_DAY questions, never the same id twice.

const fs = require('fs');
const path = require('path');

const STATE = path.join(__dirname, '..', 'data', 'demand_sensing.json');
const SE_SITES = ['freelancing', 'money', 'workplace', 'pm', 'webmasters'];
const MAX_PER_DAY = 20;
const HN_MIN_POINTS = 20;

const ENTITIES = { '&amp;': '&', '&quot;': '"', '&#39;': "'", '&lt;': '<', '&gt;': '>' };
function clean(text) {
  return String(text || '').replace(/&(amp|quot|#39|lt|gt);/g, (m) => ENTITIES[m])
    .replace(/^(Ask|Tell) HN:\s*/i, '').replace(/\s+[—–]\s+/g, ' - ').replace(/\s+/g, ' ').trim().slice(0, 200);
}

async function getJson(url, fetchImpl, timeoutMs = 20000) {
  const ac = new AbortController();
  const t = setTimeout(() => ac.abort(), timeoutMs);
  try {
    const r = await fetchImpl(url, { signal: ac.signal, headers: { 'User-Agent': 'GalaxyForge-demand-sensing/1.0' } });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  } finally {
    clearTimeout(t);
  }
}

async function fetchCandidates({ fetchImpl = fetch, now = Date.now() } = {}) {
  const out = [];
  const errors = [];
  for (const site of SE_SITES) {
    try {
      const d = await getJson(`https://api.stackexchange.com/2.3/questions?order=desc&sort=hot&site=${site}&pagesize=5`, fetchImpl);
      for (const q of d.items || []) out.push({ id: `se:${site}:${q.question_id}`, title: clean(q.title), source: `stackexchange/${site}` });
    } catch (err) {
      errors.push(`stackexchange/${site}: ${err.message}`);
    }
  }
  try {
    const since = Math.floor(now / 1000) - 7 * 86400;
    const d = await getJson(`https://hn.algolia.com/api/v1/search?tags=ask_hn&numericFilters=points>${HN_MIN_POINTS},created_at_i>${since}&hitsPerPage=10`, fetchImpl);
    for (const h of d.hits || []) out.push({ id: `hn:${h.objectID}`, title: clean(h.title), source: 'ask_hn' });
  } catch (err) {
    errors.push(`ask_hn: ${err.message}`);
  }
  return { candidates: out.filter((c) => c.title.length >= 10), errors };
}

function readState(p) {
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch (_) { return { seen: [], last_day: null }; }
}

function writeState(p, s) {
  fs.mkdirSync(path.dirname(p), { recursive: true });
  const tmp = `${p}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(s, null, 1));
  fs.renameSync(tmp, p);
}

/** post(items) -> { added, results } : delivers items to POST /api/trends. */
async function runDemandSensing({ post, day = new Date().toISOString().slice(0, 10), statePath = STATE, fetchImpl = fetch, now = Date.now() } = {}) {
  const state = readState(statePath);
  if (state.last_day === day) return { action: 'none', detail: `demand sensing already ran for ${day}` };
  const { candidates, errors } = await fetchCandidates({ fetchImpl, now });
  const seen = new Set(state.seen || []);
  const fresh = candidates.filter((c) => !seen.has(c.id)).slice(0, MAX_PER_DAY);
  if (!candidates.length) {
    return { action: 'failed', detail: `no source answered: ${errors.join('; ').slice(0, 200)}` };
  }
  let added = 0;
  if (fresh.length) {
    const r = await post(fresh.map((c) => ({ niche: c.title, title: c.title, source: c.source })));
    added = r.added || 0;
  }
  // Only mark the day done after delivery: a failed POST retries next tick.
  writeState(statePath, { last_day: day, seen: [...seen, ...fresh.map((c) => c.id)].slice(-2000), last_run: { day, fetched: candidates.length, sent: fresh.length, added, errors } });
  return { action: added ? 'added' : 'none', detail: `${candidates.length} questions fetched, ${fresh.length} new sent to /api/trends, ${added} accepted${errors.length ? `; source errors: ${errors.join('; ').slice(0, 150)}` : ''}` };
}

module.exports = { runDemandSensing, fetchCandidates, clean, MAX_PER_DAY, SE_SITES };
