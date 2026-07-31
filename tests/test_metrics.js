// Tests for lib/metrics.js (Phase 10A — Production Stability).
// Uses Node's built-in test runner (node:test), same convention as
// tests/test_dashboard_data.js. Pure module, no server/HTTP involved.
//
//   node --test tests/test_metrics.js

const test = require('node:test');
const assert = require('node:assert/strict');

const metrics = require('../lib/metrics.js');

test('recordRequest: counts a single request under the right keys', () => {
  const registry = metrics.createMetricsRegistry();
  metrics.recordRequest(registry, { method: 'GET', route: '/company-health', status: 200, durationMs: 12 });
  assert.equal(registry.requestsTotal.get('GET|/company-health|200'), 1);
  assert.equal(registry.latencyCount.get('GET|/company-health'), 1);
  assert.equal(registry.latencySumMs.get('GET|/company-health'), 12);
  assert.equal(registry.errorsTotal.get('GET|/company-health'), undefined);
});

test('recordRequest: status >= 400 increments the error counter, < 400 does not', () => {
  const registry = metrics.createMetricsRegistry();
  metrics.recordRequest(registry, { method: 'GET', route: '/x', status: 200, durationMs: 1 });
  metrics.recordRequest(registry, { method: 'GET', route: '/x', status: 404, durationMs: 1 });
  metrics.recordRequest(registry, { method: 'GET', route: '/x', status: 500, durationMs: 1 });
  assert.equal(registry.errorsTotal.get('GET|/x'), 2);
  assert.equal(registry.requestsTotal.get('GET|/x|200'), 1);
  assert.equal(registry.requestsTotal.get('GET|/x|404'), 1);
  assert.equal(registry.requestsTotal.get('GET|/x|500'), 1);
});

test('recordRequest: multiple calls accumulate, never overwrite', () => {
  const registry = metrics.createMetricsRegistry();
  for (let i = 0; i < 5; i++) {
    metrics.recordRequest(registry, { method: 'POST', route: '/actions/:name', status: 200, durationMs: 10 });
  }
  assert.equal(registry.requestsTotal.get('POST|/actions/:name|200'), 5);
  assert.equal(registry.latencyCount.get('POST|/actions/:name'), 5);
  assert.equal(registry.latencySumMs.get('POST|/actions/:name'), 50);
});

test('recordRequest: a real success updates lastSuccessAt and never lastFailureAt', () => {
  const registry = metrics.createMetricsRegistry();
  metrics.recordRequest(registry, { method: 'GET', route: '/x', status: 200, durationMs: 1 });
  assert.ok(registry.lastSuccessAt.get('GET|/x'));
  assert.equal(registry.lastFailureAt.get('GET|/x'), undefined);
});

test('recordRequest: a real failure updates lastFailureAt and never lastSuccessAt', () => {
  const registry = metrics.createMetricsRegistry();
  metrics.recordRequest(registry, { method: 'GET', route: '/x', status: 500, durationMs: 1 });
  assert.ok(registry.lastFailureAt.get('GET|/x'));
  assert.equal(registry.lastSuccessAt.get('GET|/x'), undefined);
});

test('recordRequest: latency buckets are cumulative (a fast request counts in every bucket >= its duration)', () => {
  const registry = metrics.createMetricsRegistry();
  metrics.recordRequest(registry, { method: 'GET', route: '/y', status: 200, durationMs: 30 });
  const key = 'GET|/y';
  for (const bucket of metrics.LATENCY_BUCKETS_MS) {
    assert.equal(registry.latencyBuckets.get(`${key}|${bucket}`), 1, `expected bucket ${bucket} to include a 30ms request`);
  }
});

test('recordRequest: a slow request only counts in buckets at or above its duration', () => {
  const registry = metrics.createMetricsRegistry();
  metrics.recordRequest(registry, { method: 'GET', route: '/z', status: 200, durationMs: 300 });
  const key = 'GET|/z';
  assert.equal(registry.latencyBuckets.get(`${key}|50`), undefined);
  assert.equal(registry.latencyBuckets.get(`${key}|100`), undefined);
  assert.equal(registry.latencyBuckets.get(`${key}|250`), undefined);
  assert.equal(registry.latencyBuckets.get(`${key}|500`), 1);
  assert.equal(registry.latencyBuckets.get(`${key}|Infinity`), 1);
});

test('aggregateHealth: all ok -> healthy', () => {
  const result = metrics.aggregateHealth([{ name: 'a', status: 'ok' }, { name: 'b', status: 'ok' }]);
  assert.deepEqual(result, { overall: 'healthy', healthy_count: 2, total_count: 2 });
});

test('aggregateHealth: some failing -> degraded', () => {
  const result = metrics.aggregateHealth([{ name: 'a', status: 'ok' }, { name: 'b', status: 'error' }]);
  assert.deepEqual(result, { overall: 'degraded', healthy_count: 1, total_count: 2 });
});

test('aggregateHealth: all failing -> unhealthy', () => {
  const result = metrics.aggregateHealth([{ name: 'a', status: 'error' }, { name: 'b', status: 'error' }]);
  assert.deepEqual(result, { overall: 'unhealthy', healthy_count: 0, total_count: 2 });
});

test('aggregateHealth: no services registered -> unknown, never throws', () => {
  const result = metrics.aggregateHealth([]);
  assert.deepEqual(result, { overall: 'unknown', healthy_count: 0, total_count: 0 });
});

test('renderPrometheusText: includes required HELP/TYPE lines and is well-formed', () => {
  const registry = metrics.createMetricsRegistry();
  metrics.recordRequest(registry, { method: 'GET', route: '/company-health', status: 200, durationMs: 15 });
  const text = metrics.renderPrometheusText(registry, { uptimeSeconds: 123.456, serviceHealth: [{ name: 'company-health', status: 'ok' }] });

  const lines = text.split('\n');
  assert.ok(text.endsWith('\n'), 'must end with a trailing newline (Prometheus exposition format requirement)');

  const metricNames = ['galaxy_forge_uptime_seconds', 'galaxy_forge_http_requests_total', 'galaxy_forge_http_errors_total',
    'galaxy_forge_http_request_duration_ms_sum', 'galaxy_forge_http_request_duration_ms_count',
    'galaxy_forge_http_request_duration_ms_bucket', 'galaxy_forge_service_health'];
  for (const name of metricNames) {
    assert.ok(lines.some(l => l.startsWith(`# HELP ${name} `)), `missing # HELP for ${name}`);
    assert.ok(lines.some(l => l.startsWith(`# TYPE ${name} `)), `missing # TYPE for ${name}`);
  }

  assert.ok(text.includes('galaxy_forge_uptime_seconds 123.456'));
  assert.ok(text.includes('galaxy_forge_http_requests_total{method="GET",route="/company-health",status="200"} 1'));
  assert.ok(text.includes('galaxy_forge_service_health{service="company-health"} 1'));
});

test('renderPrometheusText: every non-comment, non-empty line matches the Prometheus exposition shape', () => {
  const registry = metrics.createMetricsRegistry();
  metrics.recordRequest(registry, { method: 'GET', route: '/x', status: 200, durationMs: 5 });
  metrics.recordRequest(registry, { method: 'GET', route: '/x', status: 500, durationMs: 6000 });
  const text = metrics.renderPrometheusText(registry, { uptimeSeconds: 1, serviceHealth: [{ name: 'x', status: 'error' }] });

  const sampleLine = /^[a-zA-Z_:][a-zA-Z0-9_:]*(\{[^}]*\})? -?[0-9.]+(e[+-]?[0-9]+)?$/;
  for (const line of text.split('\n')) {
    if (!line || line.startsWith('#')) continue;
    assert.match(line, sampleLine, `line does not match Prometheus sample syntax: ${line}`);
  }
});

test('renderPrometheusText: a failing service renders as 0, not fabricated as healthy', () => {
  const registry = metrics.createMetricsRegistry();
  const text = metrics.renderPrometheusText(registry, { serviceHealth: [{ name: 'broken-service', status: 'error' }] });
  assert.ok(text.includes('galaxy_forge_service_health{service="broken-service"} 0'));
});

// Autonomous Company Runtime (ADR-157, 2026-07-31): summarizeRoutes()
// had zero test coverage before this round despite existing since
// ADR-151 -- closing that real gap alongside the new error_rate_pct/
// last_success_at/last_failure_at fields, per this round's own "every
// thing must be testable" hard rule.
test('summarizeRoutes: aggregates count/errors/avg_latency_ms per route', () => {
  const registry = metrics.createMetricsRegistry();
  metrics.recordRequest(registry, { method: 'GET', route: '/x', status: 200, durationMs: 10 });
  metrics.recordRequest(registry, { method: 'GET', route: '/x', status: 200, durationMs: 20 });
  metrics.recordRequest(registry, { method: 'GET', route: '/x', status: 500, durationMs: 30 });
  const summary = metrics.summarizeRoutes(registry);
  assert.equal(summary['/x'].count, 3);
  assert.equal(summary['/x'].errors, 1);
  assert.equal(summary['/x'].avg_latency_ms, 20);
});

test('summarizeRoutes: error_rate_pct is real errors/count, never fabricated when count is 0', () => {
  const registry = metrics.createMetricsRegistry();
  metrics.recordRequest(registry, { method: 'GET', route: '/x', status: 200, durationMs: 1 });
  metrics.recordRequest(registry, { method: 'GET', route: '/x', status: 500, durationMs: 1 });
  metrics.recordRequest(registry, { method: 'GET', route: '/x', status: 500, durationMs: 1 });
  const summary = metrics.summarizeRoutes(registry);
  assert.equal(summary['/x'].error_rate_pct, 66.7);
});

test('summarizeRoutes: last_success_at/last_failure_at are honestly null until a real request of that kind occurs', () => {
  const registry = metrics.createMetricsRegistry();
  metrics.recordRequest(registry, { method: 'GET', route: '/only-success', status: 200, durationMs: 1 });
  const summary = metrics.summarizeRoutes(registry);
  assert.ok(summary['/only-success'].last_success_at);
  assert.equal(summary['/only-success'].last_failure_at, null);
});

test('summarizeRoutes: a route with zero real requests never appears (never a fabricated zero-filled row)', () => {
  const registry = metrics.createMetricsRegistry();
  metrics.recordRequest(registry, { method: 'GET', route: '/x', status: 200, durationMs: 1 });
  const summary = metrics.summarizeRoutes(registry);
  assert.equal(summary['/never-called'], undefined);
});
