// Galaxy Forge -- agent runtime: one invocation path with evidence (2026-10-23).
//
// The six personas in lib/agent_prompts.js were called from three places
// (POST /api/agent/:name, the Scout pipeline's brief, Publisher SEO) and none
// recorded anything: connection_verifier.py could only report them UNKNOWN.
// invokeAgent() is the shared path. Every call appends one JSON line to
// data/agent_executions.jsonl:
//   task_id, correlation_id, agent, source, started_at, duration_ms,
//   outcome (ok | invalid_output | timeout | error), model, output_chars,
//   tokens when the provider returns them, and a sanitized error.
// Never logged: prompts, outputs, API keys, request headers.
//
// The client is injected (Groq SDK shape: client.chat.completions.create),
// so tests use a fake and never reach the network.

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const DEFAULT_LOG = path.join(__dirname, '..', 'data', 'agent_executions.jsonl');
const DEFAULT_MODEL = 'openai/gpt-oss-20b';
const SECRET_PATTERNS = [/gsk_[A-Za-z0-9]{10,}/g, /sk-[A-Za-z0-9_-]{10,}/g, /Bearer\s+[A-Za-z0-9._-]+/gi,
  /pdl_[a-z]+_[A-Za-z0-9_]+/g, /bot\d+:[A-Za-z0-9_-]{20,}/g, /access_token=[^&\s]+/g];

function sanitizeError(err) {
  let msg = String((err && err.message) || err || 'unknown error');
  for (const p of SECRET_PATTERNS) msg = msg.replace(p, '[REDACTED]');
  return msg.slice(0, 300);
}

function newId(prefix) {
  return `${prefix}_${crypto.randomBytes(8).toString('hex')}`;
}

function recordAgentExecution(entry, logPath = process.env.AGENT_EXECUTION_LOG || DEFAULT_LOG) {
  try {
    fs.mkdirSync(path.dirname(logPath), { recursive: true });
    fs.appendFileSync(logPath, JSON.stringify(entry) + '\n');
  } catch (_) { /* telemetry must never break an agent call */ }
}

// Contract: an agent's output is non-empty text within sane bounds.
function validateAgentOutput(content, { minChars = 1, maxChars = 50000 } = {}) {
  if (typeof content !== 'string') return { ok: false, reason: 'output is not text' };
  const t = content.trim();
  if (t.length < minChars) return { ok: false, reason: 'empty output' };
  if (t.length > maxChars) return { ok: false, reason: `output longer than ${maxChars} chars` };
  return { ok: true };
}

function withTimeout(promise, ms) {
  let timer;
  return Promise.race([
    promise,
    new Promise((_, reject) => { timer = setTimeout(() => reject(Object.assign(new Error(`timed out after ${ms} ms`), { timeout: true })), ms); }),
  ]).finally(() => clearTimeout(timer));
}

/**
 * Invoke one agent persona. Never throws: returns
 * { ok, content, error, telemetry }.
 */
async function invokeAgent({ name, config, messages, message, client, systemPrefix = '', model = DEFAULT_MODEL,
  maxTokens = 1024, timeoutMs = 60000, source = 'api', correlationId, taskId, logPath, now = () => Date.now(),
  validate = validateAgentOutput } = {}) {
  const telemetry = {
    task_id: taskId || newId('task'),
    correlation_id: correlationId || newId('corr'),
    agent: name,
    source,
    started_at: new Date(now()).toISOString(),
    model,
  };
  const t0 = now();
  const finish = (fields) => {
    Object.assign(telemetry, fields, { duration_ms: now() - t0 });
    recordAgentExecution(telemetry, logPath);
    return telemetry;
  };
  if (!config || !config.system) {
    return { ok: false, content: null, error: `unknown agent: ${name}`, telemetry: finish({ outcome: 'error', error: `unknown agent: ${name}` }) };
  }
  if (!client) {
    return { ok: false, content: null, error: 'no model client configured', telemetry: finish({ outcome: 'error', error: 'no model client configured' }) };
  }
  const msgs = messages || [
    { role: 'system', content: systemPrefix + config.system },
    { role: 'user', content: message || config.trigger },
  ];
  try {
    const response = await withTimeout(client.chat.completions.create({ model, max_tokens: maxTokens, messages: msgs }), timeoutMs);
    const content = response && response.choices && response.choices[0] && response.choices[0].message
      ? response.choices[0].message.content : null;
    const usage = (response && response.usage) || {};
    const v = validate(content);
    const fields = { output_chars: typeof content === 'string' ? content.length : 0,
      prompt_tokens: usage.prompt_tokens, completion_tokens: usage.completion_tokens };
    if (!v.ok) {
      return { ok: false, content, error: v.reason, telemetry: finish({ ...fields, outcome: 'invalid_output', error: v.reason }) };
    }
    return { ok: true, content, error: null, telemetry: finish({ ...fields, outcome: 'ok' }) };
  } catch (err) {
    const error = sanitizeError(err);
    return { ok: false, content: null, error, telemetry: finish({ outcome: err && err.timeout ? 'timeout' : 'error', error }) };
  }
}

function readAgentExecutions(logPath = process.env.AGENT_EXECUTION_LOG || DEFAULT_LOG) {
  try {
    return fs.readFileSync(logPath, 'utf8').split('\n').filter(Boolean).map((l) => {
      try { return JSON.parse(l); } catch (_) { return null; }
    }).filter(Boolean);
  } catch (_) {
    return [];
  }
}

module.exports = { invokeAgent, recordAgentExecution, readAgentExecutions, validateAgentOutput, sanitizeError, DEFAULT_LOG };
