/* Page-visit receiver (BKL-002, Phase 4, 2026-10-16).
 *
 * A storage + statistics layer for page-visit events: append-only JSONL log,
 * rolling stats, and an evidence record for the measurement layer.
 *
 * WHAT THIS DOES NOT DO (read before relying on it):
 *  - It opens no network port and registers no HTTP route. The Phase 4
 *    directive forbids touching server.js, so nothing calls record() from the
 *    internet yet. The experiment pages are on GitHub Pages, whose
 *    /api/page-view is a 404 (observed 2026-10-15T22:24:09Z), so no real
 *    visit can reach this module until a public endpoint exists. Until a real
 *    event is recorded, to_evidence() reports RECEIVER_READY_NO_VISITS_YET,
 *    never CONNECTED.
 *  - It does not know about clicks or purchases. The funnel reports those as
 *    null ("not observed here"), never 0.
 *  - It stores no IP. user_agent and referrer are truncated.
 *
 * server.js already has a page-view receiver (/api/page-view ->
 * data/affiliate_page_views.jsonl). This module does not replace it; when a
 * public route is approved, it should be wired so the two do not diverge.
 */
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const MAX_TEXT = 300;
const FIELDS = ['page', 'product_id', 'source', 'utm_source', 'utm_medium', 'utm_campaign',
  'session_id', 'timestamp', 'user_agent', 'referrer'];

function clip(v) {
  if (v === null || v === undefined) return null;
  if (typeof v === 'number' && Number.isFinite(v)) return v;
  return String(v).slice(0, MAX_TEXT);
}

class PageVisitReceiver {
  constructor(opts = {}) {
    this.log_path = opts.log_path || path.join(ROOT, 'data', 'measurement', 'pagevisit_log.jsonl');
    this.stats_path = opts.stats_path || path.join(ROOT, 'data', 'measurement', 'pagevisit_stats.json');
    this.ensure_dirs();
  }

  ensure_dirs() {
    for (const p of [this.log_path, this.stats_path]) fs.mkdirSync(path.dirname(p), { recursive: true });
  }

  // Record one page-visit event. Unknown fields are dropped.
  record(event) {
    if (!event || typeof event !== 'object' || Array.isArray(event) || !event.page) {
      return { recorded: false, error: 'event must be an object with a page field' };
    }
    const clean = {};
    for (const f of FIELDS) clean[f] = clip(event[f]);
    const synthetic = event.synthetic === true;
    const entry = {
      ...clean,
      recorded_at: new Date().toISOString(),
      evidence_type: synthetic ? 'SYNTHETIC' : 'REAL',
      receiver: 'pagevisit_receiver_v1',
    };
    this.append_log(entry);
    this.update_stats();
    return { recorded: true, entry_id: entry.timestamp || entry.recorded_at };
  }

  append_log(entry) {
    fs.appendFileSync(this.log_path, JSON.stringify(entry) + '\n', 'utf8');
  }

  read_log() {
    if (!fs.existsSync(this.log_path)) return [];
    const out = [];
    for (const line of fs.readFileSync(this.log_path, 'utf8').split('\n')) {
      if (!line.trim()) continue;
      try { out.push(JSON.parse(line)); } catch (e) { /* skip a corrupt line, never crash */ }
    }
    return out;
  }

  update_stats() {
    const tmp = this.stats_path + '.tmp';
    fs.writeFileSync(tmp, JSON.stringify(this.get_stats(), null, 2), 'utf8');
    fs.renameSync(tmp, this.stats_path);
  }

  get_stats(period_hours = 24) {
    const since = Date.now() - period_hours * 3600 * 1000;
    const rows = this.read_log().filter((r) => Date.parse(r.recorded_at) >= since);
    const real = rows.filter((r) => r.evidence_type === 'REAL');
    const count = (key) => {
      const c = {};
      for (const r of real) if (r[key]) c[r[key]] = (c[r[key]] || 0) + 1;
      const top = Object.entries(c).sort((a, b) => b[1] - a[1])[0];
      return top ? top[0] : null;
    };
    return {
      total_visits: real.length,
      synthetic_visits: rows.length - real.length,
      unique_pages: [...new Set(real.map((r) => r.page))],
      top_product: count('product_id'),
      top_source: count('source'),
      conversion_funnel: { visits: real.length, clicks: null, purchases: null },
      funnel_note: 'clicks and purchases are not observed by this receiver (null, not 0)',
      period_hours,
      data_quality: real.length ? 'REAL' : (rows.length ? 'SYNTHETIC' : 'EMPTY'),
    };
  }

  has_real_data() {
    return this.get_stats().total_visits > 0;
  }

  to_evidence() {
    const has_data = this.has_real_data();
    return {
      source: 'pagevisit_receiver',
      timestamp: new Date().toISOString(),
      confidence: has_data ? 0.9 : 0.0,
      data_url: path.relative(ROOT, this.log_path).split(path.sep).join('/'),
      real_evidence: has_data,
      status: has_data ? 'CONNECTED' : 'RECEIVER_READY_NO_VISITS_YET',
      public_route_registered: false,
    };
  }
}

module.exports = new PageVisitReceiver();
module.exports.PageVisitReceiver = PageVisitReceiver;
