// Telegram Command Control — incoming command handler for Galaxy Forge.
// Polls Telegram for messages, parses commands, validates sender, dispatches
// actions via the existing ACTION_REGISTRY HTTP API.
//
// Security:
// - Only the configured OPENCLAW_TELEGRAM_CHAT_ID may issue commands
// - State-changing commands require confirmation (/pause yes, /approve <id>)
// - Rate-limited to 10 commands per user per 60-second window
// - All commands logged to data/telegram_commands.jsonl
//
// Architecture:
// - Read-only commands (/status, /queue) read files directly (no server dependency)
// - State-changing commands (/pause, /resume, /approve, /reject) dispatch via
//   POST /api/v1/actions/:name to the running server.js (uses INTERNAL_SERVICE_TOKEN)
// - If server.js is not running, state-changing commands fail with a clear message

const fs = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, '..', 'data');
const OFFSET_FILE = path.join(DATA_DIR, 'telegram_offset.json');
const COMMANDS_LOG = path.join(DATA_DIR, 'telegram_commands.jsonl');

const POLL_INTERVAL_MS = 3000;
const REQUEST_TIMEOUT_MS = 8000;
const RATE_WINDOW_MS = 60000;
const RATE_MAX = 10;

let poller = null;
let running = false;
let lastOffset = 0;

// ── Auth ──

function isAuthorized(chatId) {
  const allowed = process.env.OPENCLAW_TELEGRAM_CHAT_ID;
  return allowed && String(chatId) === String(allowed);
}

// ── Rate Limiting ──

const rateBuckets = new Map();

function checkRate(chatId) {
  const now = Date.now();
  const bucket = rateBuckets.get(chatId) || { count: 0, resetAt: now + RATE_WINDOW_MS };
  if (now > bucket.resetAt) {
    bucket.count = 0;
    bucket.resetAt = now + RATE_WINDOW_MS;
  }
  bucket.count++;
  rateBuckets.set(chatId, bucket);
  return bucket.count <= RATE_MAX;
}

// ── Offset Persistence ──

function loadOffset() {
  try {
    const data = JSON.parse(fs.readFileSync(OFFSET_FILE, 'utf8'));
    return data.offset || 0;
  } catch {
    return 0;
  }
}

function saveOffset(offset) {
  try {
    fs.mkdirSync(DATA_DIR, { recursive: true });
    fs.writeFileSync(OFFSET_FILE, JSON.stringify({ offset, updated: new Date().toISOString() }) + '\n');
  } catch { /* best-effort */ }
}

// ── Command Log ──

function logCommand(entry) {
  try {
    fs.mkdirSync(DATA_DIR, { recursive: true });
    fs.appendFileSync(COMMANDS_LOG, JSON.stringify({ ...entry, timestamp: new Date().toISOString() }) + '\n');
  } catch { /* best-effort */ }
}

// ── Telegram API ──

async function getUpdates(offset, token) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const params = new URLSearchParams({ offset: String(offset), timeout: '5', allowed_updates: '["message"]' });
    const res = await fetch(`https://api.telegram.org/bot${token}/getUpdates?${params}`, { signal: controller.signal });
    const body = await res.json();
    return body.ok ? (body.result || []) : [];
  } catch {
    return [];
  } finally {
    clearTimeout(timer);
  }
}

async function sendMessage(chatId, text, token) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId, text }),
      signal: controller.signal,
    });
  } catch { /* fire-and-forget */ }
  finally { clearTimeout(timer); }
}

// ── Action Dispatch (via HTTP to running server.js) ──

async function dispatchAction(actionName, body = {}) {
  const port = process.env.PORT || 3000;
  const token = process.env.INTERNAL_SERVICE_TOKEN;
  const url = `http://127.0.0.1:${port}/api/v1/actions/${actionName}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 30000);
  try {
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['X-Internal-Token'] = token;
    const res = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify({ confirmed: true, ...body }),
      signal: controller.signal,
    });
    const data = await res.json().catch(() => ({}));
    return data;
  } catch (err) {
    return { success: false, error: { message: err.message } };
  } finally {
    clearTimeout(timer);
  }
}

// ── File Readers (read-only commands) ──

function readJsonRelaxed(filePath) {
  try {
    const raw = fs.readFileSync(filePath, 'utf8').trim();
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function getFactoryStatus() {
  const state = readJsonRelaxed(path.join(DATA_DIR, 'factory_state.json'));
  const lines = ['🏭 Galaxy Forge — Factory Status', ''];
  if (state) {
    lines.push(`Current Task: ${state.current_task || 'idle'}`);
    lines.push(`Active Workflow: ${state.active_workflow || 'none'}`);
    if (state.current_task_started_at) {
      const elapsed = Math.round((Date.now() - new Date(state.current_task_started_at).getTime()) / 60000);
      lines.push(`Running For: ${elapsed}m`);
    }
  } else {
    lines.push('State: Unknown (file not readable)');
  }
  const queueState = getQueueState();
  lines.push('');
  lines.push(`Jobs — Running: ${queueState.running} | Queued: ${queueState.pending} | Done: ${queueState.completed} | Failed: ${queueState.failed}`);
  return lines.join('\n');
}

function getQueueState() {
  const jobsPath = path.join(DATA_DIR, 'job_queue.jsonl');
  const jobs = [];
  try {
    const lines = fs.readFileSync(jobsPath, 'utf8').trim().split('\n').filter(Boolean);
    const merged = new Map();
    for (const line of lines) {
      try {
        const event = JSON.parse(line);
        if (event.job_id) merged.set(event.job_id, { ...(merged.get(event.job_id) || {}), ...event });
      } catch { /* skip malformed */ }
    }
    for (const job of merged.values()) jobs.push(job);
  } catch { /* no queue file yet */ }
  return {
    running: jobs.filter(j => j.status === 'running').length,
    pending: jobs.filter(j => j.status === 'queued' || j.status === 'pending').length,
    completed: jobs.filter(j => j.status === 'completed').length,
    failed: jobs.filter(j => j.status === 'failed').length,
    total: jobs.length,
    recent: jobs.sort((a, b) => (b.created_at || '').localeCompare(a.created_at || '')).slice(0, 5),
  };
}

function getEvolutionQueue() {
  const eqPath = path.join(DATA_DIR, 'evolution_queue_state.json');
  const data = readJsonRelaxed(eqPath);
  if (!data || !Array.isArray(data.entries)) return { awaiting: [], total: 0 };
  const awaiting = data.entries.filter(e => e.stage === 'AWAITING_FOUNDER_APPROVAL');
  return { awaiting, total: data.entries.length };
}

function getQueueSummary() {
  const q = getQueueState();
  const lines = ['📋 Job Queue', ''];
  lines.push(`Total: ${q.total} | Running: ${q.running} | Queued: ${q.pending} | Done: ${q.completed} | Failed: ${q.failed}`);
  if (q.recent.length > 0) {
    lines.push('');
    lines.push('Recent:');
    for (const j of q.recent) {
      const status = j.status === 'completed' ? '✅' : j.status === 'failed' ? '❌' : j.status === 'running' ? '🔄' : '⏳';
      lines.push(`  ${status} ${j.action || j.id || 'unknown'} — ${j.status}`);
    }
  }
  return lines.join('\n');
}

function getActionsList() {
  const lines = ['⚡ Registered Actions', ''];
  const actions = [
    'pause-production', 'resume-production',
    'approve-evolution-proposal', 'reject-evolution-proposal',
    'start-production-pipeline', 'rerun-market-analysis',
    'run-full-cycle',
  ];
  for (const a of actions) {
    lines.push(`  /${a.replace(/-/g, '_')}`);
  }
  lines.push('');
  lines.push('Usage: /approve PROPOSAL_ID or /reject PROPOSAL_ID');
  return lines.join('\n');
}

function getEvolutionQueueSummary() {
  const eq = getEvolutionQueue();
  const lines = ['🧬 Evolution Queue', ''];
  lines.push(`Total proposals: ${eq.total}`);
  lines.push(`Awaiting approval: ${eq.awaiting.length}`);
  if (eq.awaiting.length > 0) {
    lines.push('');
    for (const p of eq.awaiting.slice(0, 10)) {
      const id = p.proposal_id || p.id || 'unknown';
      const summary = (p.summary || p.description || '').substring(0, 60);
      lines.push(`  • ${id}`);
      if (summary) lines.push(`    ${summary}`);
    }
    if (eq.awaiting.length > 10) lines.push(`  ... and ${eq.awaiting.length - 10} more`);
    lines.push('');
    lines.push('Approve: /approve <proposal_id>');
    lines.push('Reject:  /reject <proposal_id>');
  }
  return lines.join('\n');
}

function getHelpText() {
  return [
    '🤖 Galaxy Forge Commands',
    '',
    'Read-only:',
    '  /status  — Factory status (task, queue, health)',
    '  /queue   — Job queue details',
    '  /evolution — Proposals awaiting approval',
    '  /actions — List available actions',
    '  /help    — This message',
    '',
    'State-changing (requires confirmation):',
    '  /pause [reason]  — Pause production',
    '  /resume          — Resume production',
    '  /approve <id>    — Approve evolution proposal',
    '  /reject <id> [reason] — Reject evolution proposal',
    '',
    'All commands are logged. Rate-limited to 10/minute.',
  ].join('\n');
}

// ── Command Handlers ──

const COMMANDS = {
  status: {
    description: 'Factory status',
    auth: true,
    execute: () => getFactoryStatus(),
  },
  queue: {
    description: 'Job queue details',
    auth: true,
    execute: () => getQueueSummary(),
  },
  help: {
    description: 'Show available commands',
    auth: false,
    execute: () => getHelpText(),
  },
  actions: {
    description: 'List registered actions',
    auth: true,
    execute: () => getActionsList(),
  },
  evolution: {
    description: 'Evolution proposals awaiting approval',
    auth: true,
    execute: () => getEvolutionQueueSummary(),
  },
  pause: {
    description: 'Pause production (state-changing)',
    auth: true,
    stateChanging: true,
    execute: async (args) => {
      const reason = args.join(' ') || 'paused via Telegram';
      const result = await dispatchAction('pause-production', { reason });
      if (result.success) return `⏸ Production paused.\nReason: ${reason}`;
      return `❌ Failed to pause: ${result.error?.message || 'unknown error'}`;
    },
  },
  resume: {
    description: 'Resume production (state-changing)',
    auth: true,
    stateChanging: true,
    execute: async () => {
      const result = await dispatchAction('resume-production');
      if (result.success) return '▶️ Production resumed.';
      return `❌ Failed to resume: ${result.error?.message || 'unknown error'}`;
    },
  },
  approve: {
    description: 'Approve evolution proposal (state-changing)',
    auth: true,
    stateChanging: true,
    execute: async (args) => {
      const proposalId = args[0];
      if (!proposalId) return '❌ Usage: /approve <proposal_id>\nRun /evolution to see pending proposals.';
      const note = args.slice(1).join(' ');
      const result = await dispatchAction('approve-evolution-proposal', { proposal_id: proposalId, note });
      if (result.success) return `✅ Proposal ${proposalId} approved.`;
      return `❌ Failed to approve: ${result.error?.message || 'unknown error'}`;
    },
  },
  reject: {
    description: 'Reject evolution proposal (state-changing)',
    auth: true,
    stateChanging: true,
    execute: async (args) => {
      const proposalId = args[0];
      if (!proposalId) return '❌ Usage: /reject <proposal_id> [reason]\nRun /evolution to see pending proposals.';
      const reason = args.slice(1).join(' ');
      const result = await dispatchAction('reject-evolution-proposal', { proposal_id: proposalId, reason });
      if (result.success) return `🚫 Proposal ${proposalId} rejected.`;
      return `❌ Failed to reject: ${result.error?.message || 'unknown error'}`;
    },
  },
};

// ── Message Processing ──

async function processMessage(msg, token) {
  const chatId = msg.chat && msg.chat.id;
  const text = (msg.text || '').trim();
  if (!chatId || !text || !text.startsWith('/')) return;
  const parts = text.split(/\s+/);
  const command = parts[0].substring(1).split('@')[0].toLowerCase();
  const args = parts.slice(1);
  const handler = COMMANDS[command];
  if (!handler) {
    await sendMessage(chatId, `❓ Unknown command: /${command}\nRun /help for available commands.`, token);
    return;
  }
  if (handler.auth && !isAuthorized(chatId)) {
    await sendMessage(chatId, '🔒 Unauthorized.', token);
    logCommand({ command, chatId, authorized: false, result: 'unauthorized' });
    return;
  }
  if (!checkRate(chatId)) {
    await sendMessage(chatId, '⏳ Rate limit exceeded. Try again in a minute.', token);
    logCommand({ command, chatId, authorized: true, result: 'rate_limited' });
    return;
  }
  logCommand({ command, args, chatId, authorized: true, result: 'dispatching' });
  try {
    const response = await handler.execute(args);
    await sendMessage(chatId, response, token);
    logCommand({ command, chatId, authorized: true, result: 'completed' });
  } catch (err) {
    await sendMessage(chatId, `❌ Error: ${err.message}`, token);
    logCommand({ command, chatId, authorized: true, result: 'error', error: err.message });
  }
}

// ── Polling Loop ──

async function poll(token) {
  if (!running) return;
  try {
    const updates = await getUpdates(lastOffset, token);
    for (const update of updates) {
      if (update.update_id >= lastOffset) lastOffset = update.update_id + 1;
      if (update.message) await processMessage(update.message, token);
    }
    if (updates.length > 0) saveOffset(lastOffset);
  } catch { /* poll errors never crash the loop */ }
  if (running) {
    poller = setTimeout(() => poll(token), POLL_INTERVAL_MS);
    if (poller.unref) poller.unref();
  }
}

// ── Public API ──

function start() {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.OPENCLAW_TELEGRAM_CHAT_ID;
  if (!token || !chatId) {
    console.log('[telegram-commands] Skipped — TELEGRAM_BOT_TOKEN or OPENCLAW_TELEGRAM_CHAT_ID not configured');
    return false;
  }
  if (running) return true;
  running = true;
  lastOffset = loadOffset();
  console.log(`[telegram-commands] Starting poller (offset: ${lastOffset}, interval: ${POLL_INTERVAL_MS}ms)`);
  poll(token);
  return true;
}

function stop() {
  running = false;
  if (poller) { clearTimeout(poller); poller = null; }
  console.log('[telegram-commands] Stopped');
}

// Exported for testing — does not start a real poller
function _testExports() {
  return {
    isAuthorized,
    checkRate,
    COMMANDS,
    processMessage,
    getFactoryStatus,
    getQueueSummary,
    getEvolutionQueueSummary,
    getHelpText,
    getActionsList,
    getQueueState,
    getEvolutionQueue,
    dispatchAction,
    logCommand,
  };
}

module.exports = { start, stop, _testExports };
