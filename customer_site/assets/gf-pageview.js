/* Galaxy Forge page-view beacon (Cycle 89).
 *
 * WHY THIS FILE EXISTS
 * The inline beacon this replaces swallowed every failure with
 * .catch(() => {}), so when the site is served as a static GitHub Pages tree
 * there is no /api/page-view handler at all, the POST 404s, and the failure is
 * invisible. Analytics silently collected nothing and nobody could tell the
 * difference between "no visitors" and "no measurement".
 *
 * WHAT THIS DOES DIFFERENTLY
 *  1. The endpoint is configurable, so the same pages work the moment they are
 *     served by a host that actually has the receiver. Override per page with
 *     <meta name="gf-pageview-endpoint" content="https://.../api/page-view">
 *     or window.GF_PAGEVIEW_ENDPOINT. Default is the same-origin /api/page-view.
 *  2. Failures are OBSERVABLE. A failed beacon sets window.gfPageview.failed
 *     to true and increments a counter, and logs one short, non-sensitive
 *     warning. It never logs a payload, a URL with query data, an IP, or
 *     anything personal. It still never throws, so page stability is preserved.
 *  3. Known crawlers are skipped in the browser before any request is made, so
 *     bots never inflate a visit count even if the receiver is live.
 *  4. Repeated views of the same page inside one session are recorded once,
 *     so a re-render or a back-and-forth cannot double-count a visitor.
 *  5. It sends only a page id and the referrer. No IP, no user agent is sent
 *     by this script; classification happens server-side.
 */
(function () {
  'use strict';
  if (window.gfPageview && window.gfPageview.sent) return;

  var state = window.gfPageview = {
    sent: false, failed: false, failures: 0, endpoint: null, skipped: null
  };

  // 1. configurable endpoint
  var endpoint = '/api/page-view';
  if (typeof window.GF_PAGEVIEW_ENDPOINT === 'string' && window.GF_PAGEVIEW_ENDPOINT) {
    endpoint = window.GF_PAGEVIEW_ENDPOINT;
  } else {
    var meta = document.querySelector('meta[name="gf-pageview-endpoint"]');
    if (meta && meta.getAttribute('content')) endpoint = meta.getAttribute('content');
  }
  state.endpoint = endpoint;

  function fail() {
    state.failed = true;
    state.failures += 1;
    // observable, non-sensitive, once-per-session noise
    if (!window.__gfPageviewWarned) {
      window.__gfPageviewWarned = true;
      try {
        console.warn('[gf-pageview] tracking unavailable at ' + endpoint +
          ' - analytics are NOT being recorded. This page is served statically.');
      } catch (e) { /* never throw */ }
    }
  }

  // 3. crawler guard - do not even issue the request
  var ua = (navigator && navigator.userAgent) ? navigator.userAgent.toLowerCase() : '';
  var isCrawler = ua && /bot|crawl|spider|slurp|mediapartners|baidu|yandex|sogou|facebot|ia_archiver|headless|phantomjs|selenium|puppeteer|playwright|python-requests|curl\/|wget|httpclient|okhttp|postman|insomnia/.test(ua);
  if (isCrawler) { state.skipped = 'crawler'; return; }

  // 4. per-session dedupe per page
  var pageId = document.body && document.body.getAttribute('data-page-id');
  if (!pageId) {
    var h1 = document.querySelector('h1');
    pageId = (h1 ? h1.textContent : document.title || 'unknown')
      .replace(/\s+/g, ' ').trim().slice(0, 80);
  }
  var key = 'gf_pv_' + pageId;
  try {
    if (sessionStorage.getItem(key)) { state.skipped = 'duplicate'; return; }
    sessionStorage.setItem(key, '1');
  } catch (e) { /* private mode: continue without dedupe */ }

  var body;
  try {
    body = JSON.stringify({ page_id: String(pageId).slice(0, 120) });
  } catch (e) { state.skipped = 'unserialisable'; return; }

  state.sent = true;
  try {
    fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body,
      keepalive: true
    }).then(function (r) {
      if (!r.ok) fail();
    }).catch(fail);
  } catch (e) {
    fail();
  }
})();
