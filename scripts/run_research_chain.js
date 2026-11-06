#!/usr/bin/env node
// Galaxy Forge -- run the research chain once for today (2026-10-23).
//
// Today's Sensing trends (OPPORTUNITIES.md) -> scout brief -> qa review ->
// protected distribute step (blocked unless FACTORY_LIVE_PUBLISH=true; this
// chain never publishes). Task id is research_<date>, so a re-run the same
// day skips finished steps. Prints a JSON summary; never prints the key.
//
//   node scripts/run_research_chain.js [YYYY-MM-DD]

const fs = require('fs');
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
  const taskId = `research_${day}`;
  let r = null, stubError = null;
  try {
    r = await runChain({ taskId, steps: researchSteps(), client: new Groq({ apiKey: key }), initialContext: { trends } });
  } catch (err) {
    // The protected "distribute" step throws by design after scout and qa finished (this chain never publishes). The finished
    // steps are already recorded in data/agent_tasks.jsonl: summarize from there instead of crashing without output.
    stubError = String(err && err.message || err).slice(0, 120);
  }
  if (r) {
    console.log(JSON.stringify({ task_id: r.task_id, status: r.status, trends_used: trends.length, steps: r.steps,
      brief: r.ctx.brief || null, qa: r.ctx.qa_verdict ? { verdict: r.ctx.qa_verdict, reason: r.ctx.qa_reason } : null }, null, 1));
    return;
  }
  const rows = fs.readFileSync(path.join(__dirname, '..', 'data', 'agent_tasks.jsonl'), 'utf8').split(String.fromCharCode(10))
    .filter((l) => l.startsWith('{')).map((l) => { try { return JSON.parse(l); } catch (_) { return null; } })
    .filter((x) => x && x.task_id === taskId);
  const last = (step) => rows.filter((x) => x.step === step && x.status === 'done').pop();
  const sc = last('scout_brief'), qa = last('qa_review');
  console.log(JSON.stringify({ task_id: taskId, status: sc && qa ? 'completed' : 'failed', trends_used: trends.length, stub: stubError,
    brief: sc && sc.output ? sc.output.brief : null, qa: qa && qa.output ? { verdict: qa.output.qa_verdict, reason: qa.output.qa_reason } : null }, null, 1));
}

main();
