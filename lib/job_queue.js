// Galaxy Forge — Persisted Job Queue (Phase 1, Execution Fabric Unification).
//
// Append-only JSONL record of every ACTION_REGISTRY job lifecycle event.
// Each line is one event; current state is rebuilt by replaying events
// in order. Survives process/application/machine restart because it is
// disk-persisted. Follows the same atomic-write pattern as factory_state.js
// and channels/ledger.py.
//
// Phase 1 scope: persistence layer only. No Telegram, no event bus,
// no orchestrator integration, no new execution paths.
//
// Usage:
//   const jobQueue = require('./job_queue');
//   const job = jobQueue.createJob('rerun-market-analysis', { provenance: 'mission_control' });
//   jobQueue.completeJob(job.job_id, { result: 'success' });
//   const all = jobQueue.loadAllJobs();

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const DEFAULT_QUEUE_PATH = path.join(__dirname, '..', 'data', 'job_queue.jsonl');

// --- Schema ---
// Each JSONL line (event):
//   event:       'created' | 'running' | 'completed' | 'failed' | 'awaiting_approval'
//   job_id:      string (deterministic or random)
//   task_id:     string | null (remediation plan field)
//   operation_id:string | null (remediation plan field)
//   action:      string (ACTION_REGISTRY action name)
//   status:      string (current status after this event)
//   created_at:  string (ISO timestamp)
//   updated_at:  string (ISO timestamp)
//   finished_at: string | null
//   attempt:     number (1-indexed)
//   payload:     object | null (action arguments)
//   result:      object | null
//   error:       string | null
//   provenance:  string ('mission_control' | 'factory_tick' | 'orchestrator' | 'telegram')
//   risk:        string ('read_only' | 'automation_safe' | 'founder_gate' | 'external')
//   authorization: string | null ('pending' | 'approved' | 'rejected')
//   dependencies: string[] (job_ids this depends on)
//   evidence:    object[] (evidence references)
//   next_action: string | null (auto-chain target)

function makeJobId(action) {
  const ts = Date.now().toString(36);
  const rand = crypto.randomBytes(4).toString('hex');
  return `job_${action}_${ts}_${rand}`;
}

function classifyRisk(actionName) {
  // READ_ONLY actions: no side effects, always safe
  const READ_ONLY_PATTERNS = [
    'status', 'report', 'score', 'dashboard', 'list', 'view', 'show',
    'executive', 'department', 'resilience', 'truth-registry', 'company-state',
    'ceo-home', 'search', 'summary', 'growth-stage', 'market-intelligence-source',
    'evidence', 'brand-dna', 'gfos', 'engineering-cost', 'capital-decisions',
    'launch-readiness', 'product-lifecycle', 'company-pulse', 'dependency-matrix',
    'executive-analytics', 'if-i-were-the-ceo', 'engine-registry', 'autonomous-ops',
    'strategic-intelligence', 'gox', 'customer-returns', 'reality-audit',
    'commercial-kits', 'affiliate-commerce', 'pricing-review', 'intelligence',
    'market-domination', 'evolution-queue', 'goos', 'product-concept',
  ];
  const FOUNDER_GATE_PATTERNS = [
    'approve', 'reject', 'mark-', 'pause', 'resume', 'emergency',
    'clear-subsystem', 'mark-subsystem', 'deploy', 'publish',
    'create-', 'update-', 'delete-',
  ];
  const EXTERNAL_PATTERNS = [
    'paddle', 'gumroad', 'affiliate-click', 'upwork', 'whatsapp',
    'send-', 'submit-', 'post-',
  ];

  const lower = actionName.toLowerCase();
  if (EXTERNAL_PATTERNS.some(p => lower.includes(p))) return 'external';
  if (FOUNDER_GATE_PATTERNS.some(p => lower.includes(p))) return 'founder_gate';
  if (READ_ONLY_PATTERNS.some(p => lower.includes(p))) return 'read_only';
  return 'automation_safe';
}

// --- Atomic append ---

function appendEvent(event, queuePath = DEFAULT_QUEUE_PATH) {
  try {
    fs.mkdirSync(path.dirname(queuePath), { recursive: true });
    const line = JSON.stringify(event) + '\n';
    const tmpPath = `${queuePath}.tmp-${process.pid}`;
    // For append: read existing + append new line, write atomically
    let existing = '';
    if (fs.existsSync(queuePath)) {
      existing = fs.readFileSync(queuePath, 'utf8');
    }
    fs.writeFileSync(tmpPath, existing + line);
    fs.renameSync(tmpPath, queuePath);
    return true;
  } catch (err) {
    console.error('[job_queue] appendEvent failed:', err.message);
    return false;
  }
}

// --- Create a new job ---

function createJob(action, options = {}, queuePath = DEFAULT_QUEUE_PATH) {
  const now = new Date().toISOString();
  const job = {
    job_id: options.job_id || makeJobId(action),
    task_id: options.task_id || null,
    operation_id: options.operation_id || null,
    action,
    status: 'created',
    created_at: now,
    updated_at: now,
    finished_at: null,
    attempt: 1,
    payload: options.payload || null,
    result: null,
    error: null,
    provenance: options.provenance || 'mission_control',
    risk: options.risk || classifyRisk(action),
    authorization: options.authorization || null,
    dependencies: options.dependencies || [],
    evidence: options.evidence || [],
    next_action: options.next_action || null,
  };

  const event = { event: 'created', ...job };
  appendEvent(event, queuePath);
  return job;
}

// --- Update job status ---

function updateJob(jobId, updates, queuePath = DEFAULT_QUEUE_PATH) {
  const now = new Date().toISOString();
  const event = {
    event: updates.status || 'updated',
    job_id: jobId,
    updated_at: now,
    ...updates,
  };
  appendEvent(event, queuePath);
}

// --- Complete a job ---

function completeJob(jobId, result = null, queuePath = DEFAULT_QUEUE_PATH) {
  const now = new Date().toISOString();
  const event = {
    event: 'completed',
    job_id: jobId,
    status: 'completed',
    finished_at: now,
    updated_at: now,
    result,
  };
  appendEvent(event, queuePath);
}

// --- Fail a job ---

function failJob(jobId, error, queuePath = DEFAULT_QUEUE_PATH) {
  const now = new Date().toISOString();
  const event = {
    event: 'failed',
    job_id: jobId,
    status: 'failed',
    finished_at: now,
    updated_at: now,
    error: typeof error === 'string' ? error : (error && error.message ? error.message : String(error)),
  };
  appendEvent(event, queuePath);
}

// --- Load all jobs, rebuild current state from event log ---

function loadAllJobs(queuePath = DEFAULT_QUEUE_PATH) {
  if (!fs.existsSync(queuePath)) return [];
  let raw;
  try {
    raw = fs.readFileSync(queuePath, 'utf8');
  } catch {
    return [];
  }
  if (!raw.trim()) return [];

  const jobs = new Map();
  const lines = raw.split('\n');
  for (const line of lines) {
    if (!line.trim()) continue;
    let event;
    try {
      event = JSON.parse(line);
    } catch {
      // Malformed line: skip (fail-closed — never crash on bad data)
      continue;
    }
    if (!event || typeof event !== 'object' || !event.job_id) continue;

    const existing = jobs.get(event.job_id);
    if (!existing) {
      // First event for this job — build initial state
      jobs.set(event.job_id, {
        job_id: event.job_id,
        task_id: event.task_id || null,
        operation_id: event.operation_id || null,
        action: event.action || 'unknown',
        status: event.status || 'created',
        created_at: event.created_at || event.updated_at || new Date().toISOString(),
        updated_at: event.updated_at || event.created_at || new Date().toISOString(),
        finished_at: event.finished_at || null,
        attempt: event.attempt || 1,
        payload: event.payload || null,
        result: event.result || null,
        error: event.error || null,
        provenance: event.provenance || null,
        risk: event.risk || null,
        authorization: event.authorization || null,
        dependencies: event.dependencies || [],
        evidence: event.evidence || [],
        next_action: event.next_action || null,
      });
    } else {
      // Subsequent event — merge into existing state
      if (event.status) existing.status = event.status;
      if (event.updated_at) existing.updated_at = event.updated_at;
      if (event.finished_at) existing.finished_at = event.finished_at;
      if (event.result !== undefined) existing.result = event.result;
      if (event.error !== undefined) existing.error = event.error;
      if (event.attempt) existing.attempt = event.attempt;
      if (event.payload !== undefined) existing.payload = event.payload;
      if (event.provenance) existing.provenance = event.provenance;
      if (event.risk) existing.risk = event.risk;
      if (event.authorization !== undefined) existing.authorization = event.authorization;
      if (event.dependencies) existing.dependencies = event.dependencies;
      if (event.evidence) existing.evidence = event.evidence;
      if (event.next_action !== undefined) existing.next_action = event.next_action;
    }
  }
  return [...jobs.values()];
}

// --- Get a single job by ID ---

function getJob(jobId, queuePath = DEFAULT_QUEUE_PATH) {
  return loadAllJobs(queuePath).find(j => j.job_id === jobId) || null;
}

// --- Get jobs by status ---

function getJobsByStatus(status, queuePath = DEFAULT_QUEUE_PATH) {
  return loadAllJobs(queuePath).filter(j => j.status === status);
}

// --- Check if an action is already running (dedup) ---

function isActionRunning(actionName, queuePath = DEFAULT_QUEUE_PATH) {
  return loadAllJobs(queuePath).find(j => j.action === actionName && j.status === 'running') || null;
}

// --- Enqueue retry (failure → queued_for_retry) ---

function enqueueRetry(jobId, queuePath = DEFAULT_QUEUE_PATH) {
  const job = getJob(jobId, queuePath);
  if (!job) return null;
  updateJob(jobId, {
    status: 'queued_for_retry',
    attempt: (job.attempt || 1) + 1,
  }, queuePath);
  return getJob(jobId, queuePath);
}

// --- Summary stats ---

function queueStats(queuePath = DEFAULT_QUEUE_PATH) {
  const jobs = loadAllJobs(queuePath);
  return {
    total: jobs.length,
    created: jobs.filter(j => j.status === 'created').length,
    running: jobs.filter(j => j.status === 'running').length,
    completed: jobs.filter(j => j.status === 'completed').length,
    failed: jobs.filter(j => j.status === 'failed').length,
    awaiting_approval: jobs.filter(j => j.status === 'awaiting_approval').length,
    queued_for_retry: jobs.filter(j => j.status === 'queued_for_retry').length,
  };
}

module.exports = {
  DEFAULT_QUEUE_PATH,
  makeJobId,
  classifyRisk,
  appendEvent,
  createJob,
  updateJob,
  completeJob,
  failJob,
  loadAllJobs,
  getJob,
  getJobsByStatus,
  isActionRunning,
  enqueueRetry,
  queueStats,
};
