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
  if (status >= 400) incMap(registry.errorsTotal, key);
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

  lines.push('# HELP openclaw_uptime_seconds Service uptime in seconds.');
  lines.push('# TYPE openclaw_uptime_seconds gauge');
  lines.push(`openclaw_uptime_seconds ${Number(uptimeSeconds).toFixed(3)}`);

  lines.push('# HELP openclaw_http_requests_total Total HTTP requests to the Unified Service Layer, by method, route, and status.');
  lines.push('# TYPE openclaw_http_requests_total counter');
  for (const [key, count] of registry.requestsTotal) {
    const [method, route, status] = key.split('|');
    lines.push(`openclaw_http_requests_total{method="${method}",route="${route}",status="${status}"} ${count}`);
  }

  lines.push('# HELP openclaw_http_errors_total Total HTTP requests with status >= 400, by method and route.');
  lines.push('# TYPE openclaw_http_errors_total counter');
  for (const [key, count] of registry.errorsTotal) {
    const [method, route] = key.split('|');
    lines.push(`openclaw_http_errors_total{method="${method}",route="${route}"} ${count}`);
  }

  lines.push('# HELP openclaw_http_request_duration_ms_sum Sum of request durations in milliseconds, by method and route.');
  lines.push('# TYPE openclaw_http_request_duration_ms_sum counter');
  for (const [key, sum] of registry.latencySumMs) {
    const [method, route] = key.split('|');
    lines.push(`openclaw_http_request_duration_ms_sum{method="${method}",route="${route}"} ${sum.toFixed(3)}`);
  }

  lines.push('# HELP openclaw_http_request_duration_ms_count Count of requests measured for duration, by method and route.');
  lines.push('# TYPE openclaw_http_request_duration_ms_count counter');
  for (const [key, count] of registry.latencyCount) {
    const [method, route] = key.split('|');
    lines.push(`openclaw_http_request_duration_ms_count{method="${method}",route="${route}"} ${count}`);
  }

  lines.push('# HELP openclaw_http_request_duration_ms_bucket Cumulative request duration histogram in milliseconds, by method and route.');
  lines.push('# TYPE openclaw_http_request_duration_ms_bucket histogram');
  for (const routeKey of registry.latencyCount.keys()) {
    const [method, route] = routeKey.split('|');
    for (const bucket of LATENCY_BUCKETS_MS) {
      const count = registry.latencyBuckets.get(`${routeKey}|${bucket}`) || 0;
      const le = bucket === Infinity ? '+Inf' : String(bucket);
      lines.push(`openclaw_http_request_duration_ms_bucket{method="${method}",route="${route}",le="${le}"} ${count}`);
    }
  }

  lines.push('# HELP openclaw_service_health Health check result per registered service (1 = ok, 0 = not ok).');
  lines.push('# TYPE openclaw_service_health gauge');
  for (const s of serviceHealth) {
    lines.push(`openclaw_service_health{service="${s.name}"} ${s.status === 'ok' ? 1 : 0}`);
  }

  return lines.join('\n') + '\n';
}

module.exports = {
  LATENCY_BUCKETS_MS,
  createMetricsRegistry,
  recordRequest,
  aggregateHealth,
  renderPrometheusText,
};
