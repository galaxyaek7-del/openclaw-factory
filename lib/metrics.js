// Unified Service Layer observability (Phase 10A — Production Stability).
//
// Pure, framework-free — no Express/http dependency, mirroring
// lib/dashboard_data.js's own convention (see that file's header comment)
// so this is unit-testable in isolation without booting a real server.
//
// Three responsibilities:
//   1. In-memory request/error/latency counters (createMetricsRegistry +
//      recordRequest), keyed by method+route+status.
//   2. Prometheus text-exposition rendering (renderPrometheusText) —
//      standard HELP/TYPE comments, counter/gauge/histogram types.
//   3. Service-health aggregation (aggregateHealth) — turns a list of
//      per-service health results into one overall verdict, reused by
//      both GET /api/v1/health and the health gauge inside /api/v1/metrics.

const LATENCY_BUCKETS_MS = [50, 100, 250, 500, 1000, 2500, 5000, 10000, Infinity];

function createMetricsRegistry() {
  return {
    requestsTotal: new Map(),   // `${method}|${route}|${status}` -> count
    errorsTotal: new Map(),     // `${method}|${route}` -> count (status >= 400)
    latencySumMs: new Map(),    // `${method}|${route}` -> sum of durations
    latencyCount: new Map(),    // `${method}|${route}` -> count of durations
    latencyBuckets: new Map(),  // `${method}|${route}|${le}` -> cumulative count
    // Autonomous Company Runtime (ADR-157, 2026-07-31): real "last
    // successful/failed execution" per route -- Objective 6's Health
    // Monitoring ask. Pure additive extension of the same real
    // recordRequest() call site every other counter above already uses;
    // no new instrumentation, no new system.
    lastSuccessAt: new Map(),   // `${method}|${route}` -> ISO timestamp of the last status<400 request
    lastFailureAt: new Map(),   // `${method}|${route}` -> ISO timestamp of the last status>=400 request
  };
}

function incMap(map, key, by = 1) {
  map.set(key, (map.get(key) || 0) + by);
}

function recordRequest(registry, { method, route, status, durationMs }) {
  const key = `${method}|${route}`;
  incMap(registry.requestsTotal, `${key}|${status}`);
  incMap(registry.latencySumMs, key, durationMs);
  incMap(registry.latencyCount, key);
  if (status >= 400) {
    incMap(registry.errorsTotal, key);
    registry.lastFailureAt.set(key, new Date().toISOString());
  } else {
    registry.lastSuccessAt.set(key, new Date().toISOString());
  }
  for (const bucket of LATENCY_BUCKETS_MS) {
    if (durationMs <= bucket) incMap(registry.latencyBuckets, `${key}|${bucket}`);
  }
}

function aggregateHealth(results) {
  const total = results.length;
  const healthy = results.filter(r => r.status === 'ok').length;
  const overall = total === 0 ? 'unknown' : (healthy === total ? 'healthy' : (healthy === 0 ? 'unhealthy' : 'degraded'));
  return { overall, healthy_count: healthy, total_count: total };
}

function renderPrometheusText(registry, { uptimeSeconds = 0, serviceHealth = [] } = {}) {
  const lines = [];

  lines.push('# HELP galaxy_forge_uptime_seconds Service uptime in seconds.');
  lines.push('# TYPE galaxy_forge_uptime_seconds gauge');
  lines.push(`galaxy_forge_uptime_seconds ${Number(uptimeSeconds).toFixed(3)}`);

  lines.push('# HELP galaxy_forge_http_requests_total Total HTTP requests to the Unified Service Layer, by method, route, and status.');
  lines.push('# TYPE galaxy_forge_http_requests_total counter');
  for (const [key, count] of registry.requestsTotal) {
    const [method, route, status] = key.split('|');
    lines.push(`galaxy_forge_http_requests_total{method="${method}",route="${route}",status="${status}"} ${count}`);
  }

  lines.push('# HELP galaxy_forge_http_errors_total Total HTTP requests with status >= 400, by method and route.');
  lines.push('# TYPE galaxy_forge_http_errors_total counter');
  for (const [key, count] of registry.errorsTotal) {
    const [method, route] = key.split('|');
    lines.push(`galaxy_forge_http_errors_total{method="${method}",route="${route}"} ${count}`);
  }

  lines.push('# HELP galaxy_forge_http_request_duration_ms_sum Sum of request durations in milliseconds, by method and route.');
  lines.push('# TYPE galaxy_forge_http_request_duration_ms_sum counter');
  for (const [key, sum] of registry.latencySumMs) {
    const [method, route] = key.split('|');
    lines.push(`galaxy_forge_http_request_duration_ms_sum{method="${method}",route="${route}"} ${sum.toFixed(3)}`);
  }

  lines.push('# HELP galaxy_forge_http_request_duration_ms_count Count of requests measured for duration, by method and route.');
  lines.push('# TYPE galaxy_forge_http_request_duration_ms_count counter');
  for (const [key, count] of registry.latencyCount) {
    const [method, route] = key.split('|');
    lines.push(`galaxy_forge_http_request_duration_ms_count{method="${method}",route="${route}"} ${count}`);
  }

  lines.push('# HELP galaxy_forge_http_request_duration_ms_bucket Cumulative request duration histogram in milliseconds, by method and route.');
  lines.push('# TYPE galaxy_forge_http_request_duration_ms_bucket histogram');
  for (const routeKey of registry.latencyCount.keys()) {
    const [method, route] = routeKey.split('|');
    for (const bucket of LATENCY_BUCKETS_MS) {
      const count = registry.latencyBuckets.get(`${routeKey}|${bucket}`) || 0;
      const le = bucket === Infinity ? '+Inf' : String(bucket);
      lines.push(`galaxy_forge_http_request_duration_ms_bucket{method="${method}",route="${route}",le="${le}"} ${count}`);
    }
  }

  lines.push('# HELP galaxy_forge_service_health Health check result per registered service (1 = ok, 0 = not ok).');
  lines.push('# TYPE galaxy_forge_service_health gauge');
  for (const s of serviceHealth) {
    lines.push(`galaxy_forge_service_health{service="${s.name}"} ${s.status === 'ok' ? 1 : 0}`);
  }

  return lines.join('\n') + '\n';
}

// Executive Mission Control V3 (ADR-151, 2026-07-30): a second, JSON-
// shaped view of the exact same real counters recordRequest() already
// fills for renderPrometheusText() above -- no new instrumentation, no
// second measurement system. Keyed by route (e.g. "/ai-doctor") so the
// dashboard can match it against a SERVICE_REGISTRY entry's own name by
// prefixing "/". Honestly omits a route with zero real recorded
// requests rather than inventing a zero-filled row for every possible
// route.
function summarizeRoutes(registry) {
  // requestsTotal is keyed "method|route|status" (recordRequest() appends
  // status to the method|route key); every other map is keyed just
  // "method|route" -- aggregated across HTTP methods per route since
  // every real SERVICE_REGISTRY route this feeds is GET-only anyway.
  const byRoute = new Map();
  const bump = (route, field, by) => {
    if (!byRoute.has(route)) byRoute.set(route, { count: 0, errors: 0, sumMs: 0, latencyCount: 0 });
    byRoute.get(route)[field] += by;
  };
  for (const [key, count] of registry.requestsTotal) {
    const parts = key.split('|');
    const route = parts[1];
    bump(route, 'count', count);
  }
  for (const [key, count] of registry.errorsTotal) {
    const route = key.split('|')[1];
    bump(route, 'errors', count);
  }
  for (const [key, sumMs] of registry.latencySumMs) {
    const route = key.split('|')[1];
    bump(route, 'sumMs', sumMs);
  }
  for (const [key, count] of registry.latencyCount) {
    const route = key.split('|')[1];
    bump(route, 'latencyCount', count);
  }
  // Autonomous Company Runtime (ADR-157, 2026-07-31): real "last
  // successful/failed execution" per route, aggregated the same
  // most-recent-wins way across HTTP methods as every other field here
  // (every real route this feeds is GET-only in practice).
  const lastSuccessByRoute = new Map();
  for (const [key, iso] of registry.lastSuccessAt) {
    const route = key.split('|')[1];
    const prev = lastSuccessByRoute.get(route);
    if (!prev || iso > prev) lastSuccessByRoute.set(route, iso);
  }
  const lastFailureByRoute = new Map();
  for (const [key, iso] of registry.lastFailureAt) {
    const route = key.split('|')[1];
    const prev = lastFailureByRoute.get(route);
    if (!prev || iso > prev) lastFailureByRoute.set(route, iso);
  }
  const result = {};
  for (const [route, stats] of byRoute) {
    result[route] = {
      count: stats.count,
      errors: stats.errors,
      error_rate_pct: stats.count > 0 ? Math.round((stats.errors / stats.count) * 1000) / 10 : null,
      avg_latency_ms: stats.latencyCount > 0 ? Math.round((stats.sumMs / stats.latencyCount) * 10) / 10 : null,
      last_success_at: lastSuccessByRoute.get(route) || null,
      last_failure_at: lastFailureByRoute.get(route) || null,
    };
  }
  return result;
}

module.exports = {
  LATENCY_BUCKETS_MS,
  createMetricsRegistry,
  recordRequest,
  aggregateHealth,
  renderPrometheusText,
  summarizeRoutes,
};
