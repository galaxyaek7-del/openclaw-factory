/* Galaxy Forge tracker v2 (static/js/gf-tracker-v2.js).
 *
 * Superset of customer_site/assets/gf-pageview.js. Same hard rules:
 *   - never throws (page stability first),
 *   - failures are OBSERVABLE (window.gfTracker.failed), never swallowed,
 *   - known crawlers are skipped before any request,
 *   - one view per page per session,
 *   - sends only a page id and the referrer; no IP, no user agent, no PII.
 *
 * New in v2:
 *   - configurable endpoint (meta[name="gf-tracker-endpoint"] or window.GF_TRACKER_ENDPOINT),
 *   - a small bounded retry queue with backoff for transient failures,
 *   - a public API: window.gfTracker.track(pageId), .flush(), .stats(),
 *   - optional source attribution from ?utm_source= / ?source=.
 *
 * It still cannot make a static host store anything: on GitHub Pages the POST
 * 404s, gfTracker.failed becomes true, and one non-sensitive warning is logged.
 * That is by design — silent success on a host with no receiver would be a lie.
 */
(function () {
  'use strict';
  if (window.gfTracker && window.gfTracker.__v === 2) return;

  var MAX_QUEUE = 20;
  var MAX_RETRIES = 2;
  var state = {
    __v: 2,
    sent: false,
    failed: false,
    failures: 0,
    retries: 0,
    skipped: null,
    endpoint: null,
    queue: []
  };
  window.gfTracker = state;

  function endpoint() {
    if (typeof window.GF_TRACKER_ENDPOINT === 'string' && window.GF_TRACKER_ENDPOINT) {
      return window.GF_TRACKER_ENDPOINT;
    }
    var meta = document.querySelector('meta[name="gf-tracker-endpoint"]');
    if (meta && meta.getAttribute('content')) return meta.getAttribute('content');
    return '/api/page-view';
  }
  state.endpoint = endpoint();

  function warnOnce() {
    if (window.__gfTrackerWarned) return;
    window.__gfTrackerWarned = true;
    try {
      console.warn('[gf-tracker] analytics NOT recorded at ' + state.endpoint +
        ' (static host has no receiver). gfTracker.failed = true.');
    } catch (e) { /* never throw */ }
  }

  function fail(payload) {
    state.failed = true;
    state.failures += 1;
    warnOnce();
    if (state.queue.length < MAX_QUEUE) state.queue.push(payload);
  }

  function post(payload, attempt) {
    var done = false;
    try {
      fetch(state.endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        keepalive: true
      }).then(function (r) {
        if (r.ok) { state.sent = true; state.failed = false; return; }
        if (attempt < MAX_RETRIES) {
          state.retries += 1;
          setTimeout(function () { post(payload, attempt + 1); }, 500 * (attempt + 1));
        } else { fail(payload); }
      }).catch(function () {
        if (attempt < MAX_RETRIES) {
          state.retries += 1;
          setTimeout(function () { post(payload, attempt + 1); }, 500 * (attempt + 1));
        } else { fail(payload); }
      });
    } catch (e) { fail(payload); }
    return done;
  }

  function crawler() {
    var ua = (navigator && navigator.userAgent) ? navigator.userAgent.toLowerCase() : '';
    return ua && /bot|crawl|spider|slurp|mediapartners|baidu|yandex|sogou|facebot|ia_archiver|headless|phantomjs|selenium|puppeteer|playwright|python-requests|curl\/|wget|httpclient|okhttp|postman|insomnia/.test(ua);
  }

  function source() {
    try {
      var p = new URLSearchParams(window.location.search);
      return p.get('utm_source') || p.get('source') || null;
    } catch (e) { return null; }
  }

  function track(pageId) {
    if (!pageId) pageId = 'unknown';
    pageId = String(pageId).slice(0, 120);
    var key = 'gf_tracker_' + pageId;
    try {
      if (sessionStorage.getItem(key)) { state.skipped = 'duplicate'; return false; }
      sessionStorage.setItem(key, '1');
    } catch (e) { /* private mode: continue without dedupe */ }
    return post({ page_id: pageId, source: source() }, 0);
  }

  function flush() {
    var q = state.queue.slice();
    state.queue.length = 0;
    q.forEach(function (p) { post(p, 0); });
    return q.length;
  }

  if (crawler()) { state.skipped = 'crawler'; return; }

  var pageId = (document.body && document.body.getAttribute('data-page-id')) || null;
  if (!pageId) {
    var h1 = document.querySelector('h1');
    pageId = (h1 ? h1.textContent : document.title || 'unknown')
      .replace(/\s+/g, ' ').trim().slice(0, 80);
  }
  track(pageId);

  window.gfTracker.track = track;
  window.gfTracker.flush = flush;
  window.gfTracker.stats = function () {
    return { sent: state.sent, failed: state.failed, failures: state.failures,
             retries: state.retries, skipped: state.skipped, queued: state.queue.length,
             endpoint: state.endpoint };
  };
})();
