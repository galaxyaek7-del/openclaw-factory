// Re-run rule for the once-a-day ops record (2026-11-06).
//
// The record is written once per UTC day and the loop then skips the day. On 2026-11-06 the host's network was down at
// 02:50Z, so the record said website FAIL / gumroad BLOCKED for the whole day although both were fine an hour later.
// A record whose failures are TRANSIENT network errors may be refreshed, at most MAX_RERUNS times, MIN_GAP_MS apart.
// Real findings (content errors, n8n execution errors, a genuine HOLD) never trigger a re-run.

const TRANSIENT = /unreachable|URLError|UNAVAILABLE|ETIMEDOUT|ECONNRESET|ENOTFOUND|EAI_AGAIN|timed out|fetch failed/i;
const NETWORK_AREAS = new Set(['website', 'gumroad']);
const MAX_RERUNS = 3;
const MIN_GAP_MS = 2 * 60 * 60 * 1000;

function hasTransientNetworkFailure(record) {
  if (!record || !Array.isArray(record.findings)) return false;
  return record.findings.some((f) => f && NETWORK_AREAS.has(f.area)
    && (f.label === 'FAIL' || f.label === 'BLOCKED') && TRANSIENT.test(String(f.detail || '')));
}

// recordMtimeMs: when the record was written; rerunsDone: how many refreshes already happened today.
function shouldRerunOpsRecord(record, { recordMtimeMs, nowMs, rerunsDone = 0 } = {}) {
  if (rerunsDone >= MAX_RERUNS) return { rerun: false, reason: `already refreshed ${rerunsDone} times today` };
  if (!hasTransientNetworkFailure(record)) return { rerun: false, reason: 'no transient network failure in the record' };
  if (nowMs - recordMtimeMs < MIN_GAP_MS) return { rerun: false, reason: 'record is younger than 2 hours' };
  return { rerun: true, reason: 'record holds transient network failures' };
}

module.exports = { hasTransientNetworkFailure, shouldRerunOpsRecord, MAX_RERUNS, MIN_GAP_MS };
