// Tests for lib/job_queue.js (Phase 1 — Persisted Job Queue).
// Never touches the real data/job_queue.jsonl — every test uses a temp path.
//
//   node --test tests/test_job_queue.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const jobQueue = require('../lib/job_queue.js');

function tempPath() {
  return path.join(os.tmpdir(), `job_queue_test_${Date.now()}_${Math.random().toString(36).slice(2)}.jsonl`);
}

function cleanup(p) {
  if (fs.existsSync(p)) fs.unlinkSync(p);
  const dir = path.dirname(p);
  const base = path.basename(p);
  for (const entry of fs.readdirSync(dir)) {
    if (entry.startsWith(`${base}.tmp-`)) fs.unlinkSync(path.join(dir, entry));
  }
}

// --- Test 1: Missing file reads as empty ---
test('missing file reads as empty array', () => {
  const p = tempPath();
  try {
    const jobs = jobQueue.loadAllJobs(p);
    assert.deepEqual(jobs, []);
  } finally {
    cleanup(p);
  }
});

// --- Test 2: Create a job ---
test('createJob returns a job with correct fields', () => {
  const p = tempPath();
  try {
    const job = jobQueue.createJob('rerun-market-analysis', {
      provenance: 'mission_control',
    }, p);
    assert.equal(job.action, 'rerun-market-analysis');
    assert.equal(job.status, 'created');
    assert.equal(job.provenance, 'mission_control');
    assert.ok(job.job_id.startsWith('job_rerun-market-analysis_'));
    assert.ok(job.created_at);
    assert.equal(job.finished_at, null);
    assert.equal(job.result, null);
    assert.equal(job.error, null);
    assert.equal(job.attempt, 1);
  } finally {
    cleanup(p);
  }
});

// --- Test 3: Job persists to disk ---
test('createJob persists to disk', () => {
  const p = tempPath();
  try {
    jobQueue.createJob('test-action', {}, p);
    assert.ok(fs.existsSync(p));
    const content = fs.readFileSync(p, 'utf8');
    const lines = content.trim().split('\n');
    assert.equal(lines.length, 1);
    const event = JSON.parse(lines[0]);
    assert.equal(event.event, 'created');
    assert.equal(event.action, 'test-action');
  } finally {
    cleanup(p);
  }
});

// --- Test 4: LoadAllJobs rebuilds state from events ---
test('loadAllJobs rebuilds current state from event log', () => {
  const p = tempPath();
  try {
    const job = jobQueue.createJob('test-action', { job_id: 'test-001' }, p);
    jobQueue.completeJob('test-001', { success: true }, p);

    const jobs = jobQueue.loadAllJobs(p);
    assert.equal(jobs.length, 1);
    assert.equal(jobs[0].job_id, 'test-001');
    assert.equal(jobs[0].status, 'completed');
    assert.deepEqual(jobs[0].result, { success: true });
    assert.ok(jobs[0].finished_at);
  } finally {
    cleanup(p);
  }
});

// --- Test 5: Recovery after simulated restart ---
test('jobs survive simulated restart (read after write)', () => {
  const p = tempPath();
  try {
    // Simulate process 1: create and complete jobs
    jobQueue.createJob('action-a', { job_id: 'j1' }, p);
    jobQueue.completeJob('j1', { data: 1 }, p);
    jobQueue.createJob('action-b', { job_id: 'j2' }, p);
    jobQueue.failJob('j2', 'something went wrong', p);

    // Simulate process restart: read the same file
    const jobs = jobQueue.loadAllJobs(p);
    assert.equal(jobs.length, 2);

    const j1 = jobs.find(j => j.job_id === 'j1');
    assert.equal(j1.status, 'completed');
    assert.deepEqual(j1.result, { data: 1 });

    const j2 = jobs.find(j => j.job_id === 'j2');
    assert.equal(j2.status, 'failed');
    assert.equal(j2.error, 'something went wrong');
  } finally {
    cleanup(p);
  }
});

// --- Test 6: Malformed lines are skipped (fail-closed) ---
test('malformed lines are skipped, never crash', () => {
  const p = tempPath();
  try {
    // Write a mix of valid and invalid lines
    fs.writeFileSync(p, 'not json\n{"event":"created","job_id":"j1","action":"test","status":"created","created_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:00:00Z"}\n{broken\n{"event":"completed","job_id":"j1","status":"completed","updated_at":"2026-01-01T00:01:00Z","finished_at":"2026-01-01T00:01:00Z"}\n');

    const jobs = jobQueue.loadAllJobs(p);
    assert.equal(jobs.length, 1);
    assert.equal(jobs[0].job_id, 'j1');
    assert.equal(jobs[0].status, 'completed');
  } finally {
    cleanup(p);
  }
});

// --- Test 7: Duplicate job_id handling (idempotent) ---
test('duplicate job_id events are merged, not duplicated', () => {
  const p = tempPath();
  try {
    jobQueue.createJob('test-action', { job_id: 'dup-001' }, p);
    jobQueue.createJob('test-action', { job_id: 'dup-001' }, p); // duplicate
    jobQueue.completeJob('dup-001', { ok: true }, p);

    const jobs = jobQueue.loadAllJobs(p);
    // Should have exactly 1 job (not 2) because job_id is the same
    assert.equal(jobs.length, 1);
    assert.equal(jobs[0].status, 'completed');
  } finally {
    cleanup(p);
  }
});

// --- Test 8: Failure state is preserved ---
test('failed job preserves error details', () => {
  const p = tempPath();
  try {
    jobQueue.createJob('failing-action', { job_id: 'fail-001' }, p);
    jobQueue.updateJob('fail-001', { status: 'running' }, p);
    jobQueue.failJob('fail-001', 'groq rate limit exceeded', p);

    const jobs = jobQueue.loadAllJobs(p);
    assert.equal(jobs.length, 1);
    assert.equal(jobs[0].status, 'failed');
    assert.equal(jobs[0].error, 'groq rate limit exceeded');
    assert.ok(jobs[0].finished_at);
  } finally {
    cleanup(p);
  }
});

// --- Test 9: classifyRisk returns correct categories ---
test('classifyRisk categorizes actions correctly', () => {
  assert.equal(jobQueue.classifyRisk('executive-score'), 'read_only');
  assert.equal(jobQueue.classifyRisk('rerun-market-analysis'), 'automation_safe');
  assert.equal(jobQueue.classifyRisk('approve-evolution-proposal'), 'founder_gate');
  assert.equal(jobQueue.classifyRisk('paddle-checkout-notification'), 'external');
  assert.equal(jobQueue.classifyRisk('create-paddle-product'), 'external');
  assert.equal(jobQueue.classifyRisk('pause-production'), 'founder_gate');
  assert.equal(jobQueue.classifyRisk('company-state'), 'read_only');
});

// --- Test 10: getJob returns single job ---
test('getJob returns correct job or null', () => {
  const p = tempPath();
  try {
    jobQueue.createJob('test-action', { job_id: 'get-001' }, p);
    jobQueue.createJob('other-action', { job_id: 'get-002' }, p);

    const found = jobQueue.getJob('get-001', p);
    assert.equal(found.job_id, 'get-001');
    assert.equal(found.action, 'test-action');

    const notFound = jobQueue.getJob('nonexistent', p);
    assert.equal(notFound, null);
  } finally {
    cleanup(p);
  }
});

// --- Test 11: getJobsByStatus filters correctly ---
test('getJobsByStatus returns only matching jobs', () => {
  const p = tempPath();
  try {
    jobQueue.createJob('a', { job_id: 's1' }, p);
    jobQueue.createJob('b', { job_id: 's2' }, p);
    jobQueue.completeJob('s1', null, p);

    const completed = jobQueue.getJobsByStatus('completed', p);
    assert.equal(completed.length, 1);
    assert.equal(completed[0].job_id, 's1');

    const created = jobQueue.getJobsByStatus('created', p);
    assert.equal(created.length, 1);
    assert.equal(created[0].job_id, 's2');
  } finally {
    cleanup(p);
  }
});

// --- Test 12: queueStats returns correct counts ---
test('queueStats counts all statuses', () => {
  const p = tempPath();
  try {
    jobQueue.createJob('a', { job_id: 'q1' }, p);
    jobQueue.createJob('b', { job_id: 'q2' }, p);
    jobQueue.createJob('c', { job_id: 'q3' }, p);
    jobQueue.completeJob('q1', null, p);
    jobQueue.failJob('q2', 'error', p);

    const stats = jobQueue.queueStats(p);
    assert.equal(stats.total, 3);
    assert.equal(stats.completed, 1);
    assert.equal(stats.failed, 1);
    assert.equal(stats.created, 1);
  } finally {
    cleanup(p);
  }
});

// --- Test 13: Enqueue retry increments attempt ---
test('enqueueRetry increments attempt count', () => {
  const p = tempPath();
  try {
    jobQueue.createJob('retry-action', { job_id: 'retry-001' }, p);
    jobQueue.failJob('retry-001', 'first failure', p);
    jobQueue.enqueueRetry('retry-001', p);

    const job = jobQueue.getJob('retry-001', p);
    assert.equal(job.status, 'queued_for_retry');
    assert.equal(job.attempt, 2);
  } finally {
    cleanup(p);
  }
});

// --- Test 14: isActionRunning detects running action ---
test('isActionRunning finds running actions', () => {
  const p = tempPath();
  try {
    jobQueue.createJob('running-action', { job_id: 'run-001' }, p);
    jobQueue.updateJob('run-001', { status: 'running' }, p);

    const running = jobQueue.isActionRunning('running-action', p);
    assert.ok(running);
    assert.equal(running.job_id, 'run-001');

    const notRunning = jobQueue.isActionRunning('other-action', p);
    assert.equal(notRunning, null);
  } finally {
    cleanup(p);
  }
});

// --- Test 15: Empty file reads as empty ---
test('empty file reads as empty array', () => {
  const p = tempPath();
  try {
    fs.writeFileSync(p, '');
    const jobs = jobQueue.loadAllJobs(p);
    assert.deepEqual(jobs, []);
  } finally {
    cleanup(p);
  }
});

// --- Test 16: Line with no job_id is skipped ---
test('event with no job_id is skipped', () => {
  const p = tempPath();
  try {
    fs.writeFileSync(p, '{"event":"created","action":"test"}\n');
    const jobs = jobQueue.loadAllJobs(p);
    assert.deepEqual(jobs, []);
  } finally {
    cleanup(p);
  }
});

// --- Test 17: Multiple events per job, latest wins ---
test('latest event for a job_id takes precedence', () => {
  const p = tempPath();
  try {
    jobQueue.createJob('multi', { job_id: 'm1' }, p);
    jobQueue.updateJob('m1', { status: 'running' }, p);
    jobQueue.updateJob('m1', { status: 'completed', result: { v: 2 } }, p);

    const jobs = jobQueue.loadAllJobs(p);
    assert.equal(jobs.length, 1);
    assert.equal(jobs[0].status, 'completed');
    assert.deepEqual(jobs[0].result, { v: 2 });
  } finally {
    cleanup(p);
  }
});

// --- Test 18: Protected files are NOT modified ---
test('job_queue does not modify protected files', () => {
  const realityPath = path.join(__dirname, '..', 'config', 'reality.json');
  const financePath = path.join(__dirname, '..', 'finance_data.json');
  const salesPath = path.join(__dirname, '..', 'sales_ledger.jsonl');

  // Record checksums before
  const shaBefore = (p) => fs.existsSync(p) ? require('crypto').createHash('md5').update(fs.readFileSync(p)).digest('hex') : 'missing';
  const realityHash = shaBefore(realityPath);
  const financeHash = shaBefore(financePath);
  const salesHash = shaBefore(salesPath);

  // Run some job queue operations
  const p = tempPath();
  try {
    jobQueue.createJob('test', { job_id: 'protect-001' }, p);
    jobQueue.completeJob('protect-001', null, p);
    jobQueue.loadAllJobs(p);
  } finally {
    cleanup(p);
  }

  // Verify checksums unchanged
  assert.equal(shaBefore(realityPath), realityHash, 'config/reality.json was modified');
  assert.equal(shaBefore(financePath), financeHash, 'finance_data.json was modified');
  assert.equal(shaBefore(salesPath), salesHash, 'sales_ledger.jsonl was modified');
});
