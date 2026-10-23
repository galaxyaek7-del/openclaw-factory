// Galaxy Forge -- research chain: Sensing trends -> scout brief -> qa review (2026-10-23).
//
// The first real multi-agent handoff path. Input: trend items that today's
// Openclaw_Sensing_Engine run delivered (OPPORTUNITIES.md). Steps:
//   1. scout writes a product brief from the trends (lib/scout_brief.js prompt
//      and parser, the same ones the Scout pipeline uses);
//   2. qa reviews that exact brief and returns VERDICT: PASS|REVISE + reason;
//   3. a protected "distribute" step, which is refused unless live writes are
//      authorized -- this chain never produces or publishes anything.

const fs = require('fs');
const path = require('path');
const AGENT_PROMPTS = require('./agent_prompts');
const { scoutBriefPrompt, parseScoutBrief } = require('./scout_brief');

const OPPORTUNITIES = path.join(__dirname, '..', 'OPPORTUNITIES.md');

function todaysTrends(day, file = OPPORTUNITIES, limit = 10) {
  let text = '';
  try { text = fs.readFileSync(file, 'utf8'); } catch (_) { return []; }
  const out = [];
  for (const m of text.matchAll(/^- \[(\d{4}-\d{2}-\d{2})T[^\]]*\] (.+?) — /gm)) {
    if (m[1] === day) out.push(m[2].trim());
  }
  return [...new Set(out)].slice(0, limit);
}

function scoutContract(content) {
  const b = parseScoutBrief(content || '');
  if (!b.title || b.title.length < 5 || !b.topic || !(b.price >= 1)) return null;
  return { brief: b };
}

function qaMessage(ctx) {
  const b = ctx.brief;
  return [
    'Review this product brief produced by the scout agent. Reply with exactly two lines:',
    'VERDICT: PASS or VERDICT: REVISE',
    'REASON: one sentence',
    '',
    `Title: ${b.title}`, `Topic: ${b.topic}`, `Audience: ${b.audience}`, `Price (USD): ${b.price}`, `Chapters: ${b.chapters}`,
    ctx.trends && ctx.trends.length ? `Trends it was based on: ${ctx.trends.join(', ')}` : '',
  ].join('\n');
}

function qaContract(content) {
  const v = /VERDICT:\s*(PASS|REVISE)/i.exec(content || '');
  if (!v) return null;
  const r = /REASON:\s*(.+)/i.exec(content);
  return { qa_verdict: v[1].toUpperCase(), qa_reason: r ? r[1].trim().slice(0, 300) : '' };
}

function researchSteps() {
  return [
    { id: 'scout_brief', agent: 'scout', config: AGENT_PROMPTS.scout,
      buildMessage: (ctx) => scoutBriefPrompt(ctx.trends && ctx.trends.length ? ctx.trends.join('، ') : null),
      parse: (content) => scoutContract(content) },
    { id: 'qa_review', agent: 'qa', config: AGENT_PROMPTS.qa,
      buildMessage: (ctx) => qaMessage(ctx), parse: (content) => qaContract(content) },
    { id: 'distribute', protected: true, run: async () => { throw new Error('not implemented: research chain never publishes'); } },
  ];
}

module.exports = { researchSteps, todaysTrends, scoutContract, qaContract, qaMessage };
