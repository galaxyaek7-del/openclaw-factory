#!/usr/bin/env node
// Galaxy Forge -- run the research chain once for today (2026-10-23).
//
// Today's Sensing trends (OPPORTUNITIES.md) -> scout brief -> qa review ->
// protected distribute step (blocked unless FACTORY_LIVE_PUBLISH=true; this
// chain never publishes). Task id is research_<date>, so a re-run the same
// day skips finished steps. Prints a JSON summary; never prints the key.
//
//   node scripts/run_research_chain.js [YYYY-MM-DD]

const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '..', '.env'), quiet: true });
const Groq = require('groq-sdk');
const { runChain } = require('../lib/agent_chain');
const { researchSteps, todaysTrends } = require('../lib/research_chain');

async function main() {
  const day = process.argv[2] || new Date().toISOString().slice(0, 10);
  const trends = todaysTrends(day);
  const key = process.env.GROQ_KEY || process.env.GROQ_API_KEY;
  if (!key) {
    console.log(JSON.stringify({ ok: false, error: 'GROQ_KEY not configured' }));
    process.exit(1);
  }
  const r = await runChain({ taskId: `research_${day}`, steps: researchSteps(), client: new Groq({ apiKey: key }),
    initialContext: { trends } });
  console.log(JSON.stringify({ task_id: r.task_id, status: r.status, trends_used: trends.length, steps: r.steps,
    brief: r.ctx.brief || null, qa: r.ctx.qa_verdict ? { verdict: r.ctx.qa_verdict, reason: r.ctx.qa_reason } : null }, null, 1));
}

main();
