#!/usr/bin/env node
// Galaxy Forge -- bounded live probe of the six agent personas (2026-10-23).
//
// Calls each persona once through lib/agent_runtime.js (the same path as
// POST /api/agent/:name) with a one-sentence task and the route's own
// max_tokens (1024). 200 was too few: gpt-oss spends tokens on reasoning first,
// and scout/finance returned empty text at 200. Every call is recorded in data/agent_executions.jsonl with
// source "probe". Prints a JSON summary; never prints the key, prompts or outputs.
//
//   node scripts/agent_probe.js [agent ...]

const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '..', '.env'), quiet: true });
const Groq = require('groq-sdk');
const AGENT_PROMPTS = require('../lib/agent_prompts');
const { invokeAgent } = require('../lib/agent_runtime');

const TASK = 'In one sentence: state your role and one concrete output you produce for Galaxy Forge.';

async function main() {
  const key = process.env.GROQ_KEY || process.env.GROQ_API_KEY;
  if (!key) {
    console.log(JSON.stringify({ ok: false, error: 'GROQ_KEY not configured' }));
    process.exit(1);
  }
  const client = new Groq({ apiKey: key });
  const names = process.argv.slice(2).length ? process.argv.slice(2) : Object.keys(AGENT_PROMPTS);
  const correlationId = `probe_${Date.now().toString(36)}`;
  const results = [];
  for (const name of names) {
    const r = await invokeAgent({ name, config: AGENT_PROMPTS[name], client, message: TASK, maxTokens: Number(process.env.AGENT_PROBE_MAX_TOKENS || 1024),
      timeoutMs: 45000, source: 'probe', correlationId });
    results.push({ agent: name, ok: r.ok, outcome: r.telemetry.outcome, duration_ms: r.telemetry.duration_ms,
      output_chars: r.telemetry.output_chars || 0, error: r.error || undefined });
  }
  console.log(JSON.stringify({ correlation_id: correlationId, results }, null, 1));
  process.exit(results.every((x) => x.ok) ? 0 : 1);
}

main();
