// Galaxy Forge -- commercial-intent check for Sensing trends (2026-10-23).
//
// Google Trends' daily feed is mostly people and news events ("khloe
// kardashian", "adrian mannarino"). book_generator.py's quality_gate() only
// checks that a niche is non-empty and a cover theme exists, so every one of
// them reached OPPORTUNITIES.md as "passed all quality checks", and the
// research chain's qa agent then rejected the scout brief built on them.
//
// The scout agent now classifies each trend before it is written: is it a
// recurring problem a buyer would pay a digital product to solve, or a
// person/event/news item? One call per trend, through lib/agent_runtime.js
// (source "sensing_trends", so each call is recorded). Any failure -- timeout,
// API error, or an answer outside the contract -- fails closed: the trend is
// not written and the reason says why.

const AGENT_PROMPTS = require('./agent_prompts');
const agentRuntime = require('./agent_runtime');

const CONTRACT = /COMMERCIAL:\s*(YES|NO)\b/i;

function classifierMessage(niche, title) {
  return [
    'Classify one Google Trends search term for a digital-products business.',
    `Term: ${niche}`,
    title && title !== niche ? `Headline: ${title}` : '',
    '',
    'Answer YES only if the term names a recurring problem, task, hobby, profession or',
    'need that MANY people face again and again, and that a ready-made guide, template,',
    'checklist, calculator or tool could solve for all of them.',
    'Answer NO for a person, celebrity, athlete, team, match, film/show/game release,',
    'product launch, news event, or anything whose interest ends with the news cycle.',
    'Answer NO for one person\'s unique situation, a single bug or error message in one',
    'product, a definition or general-knowledge question, or career/personal advice that',
    'depends on the asker\'s circumstances.',
    '',
    'Reply with exactly two lines:',
    'COMMERCIAL: YES or COMMERCIAL: NO',
    'REASON: one short sentence',
  ].filter((l) => l !== '').join('\n');
}

function parseClassification(content) {
  const m = CONTRACT.exec(content || '');
  if (!m) return null;
  const r = /REASON:\s*(.+)/i.exec(content);
  return { commercial: m[1].toUpperCase() === 'YES', reason: r ? r[1].trim().slice(0, 200) : '' };
}

async function classifyTrend({ niche, title, client, invoke = agentRuntime.invokeAgent, logPath, timeoutMs = 30000 } = {}) {
  const result = await invoke({
    name: 'scout', config: AGENT_PROMPTS.scout, client, source: 'sensing_trends', timeoutMs, logPath,
    message: classifierMessage(niche, title),
    validate: (content) => (parseClassification(content) ? { ok: true } : { ok: false, reason: 'answer outside the COMMERCIAL: YES|NO contract' }),
  });
  const task_id = result.telemetry && result.telemetry.task_id;
  if (!result.ok) return { commercial: false, failed: true, reason: `classifier_unavailable: ${result.error}`, task_id };
  return { ...parseClassification(result.content), failed: false, task_id };
}

module.exports = { classifyTrend, classifierMessage, parseClassification };
