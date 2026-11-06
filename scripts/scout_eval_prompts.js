// Emits the exact Scout/QA prompts for the A/B/C evaluation as JSON (consumed by scripts/scout_eval.py).
// usage: node scripts/scout_eval_prompts.js <input-json-file>   input: [{id, variant, input}]
const fs = require('fs');
const path = require('path');
const root = path.join(__dirname, '..');
const AGENT_PROMPTS = require(path.join(root, 'lib', 'agent_prompts.js'));
const { scoutBriefPrompt, parseScoutBrief } = require(path.join(root, 'lib', 'scout_brief.js'));
const { scoutBriefPromptV2, V2_SYSTEM, parseScoutBriefV2 } = require(path.join(root, 'lib', 'scout_brief_v2.js'));
const { qaMessage, qaContract, scoutContract } = require(path.join(root, 'lib', 'research_chain.js'));
const cmd = process.argv[2];
if (cmd === 'prompts') {
  const rows = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
  const out = rows.map((r) => r.variant === 'A'
    ? { ...r, system: (AGENT_PROMPTS.scout.system || AGENT_PROMPTS.scout.systemPrompt || ''), user: scoutBriefPrompt(r.input) }
    : { ...r, system: V2_SYSTEM, user: scoutBriefPromptV2(r.input) });
  process.stdout.write(JSON.stringify({ rows: out, qa_system: AGENT_PROMPTS.qa.system || AGENT_PROMPTS.qa.systemPrompt || '' }));
} else if (cmd === 'parse') {
  const rows = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
  const out = rows.map((r) => {
    let brief = null, declined = false;
    if (r.variant === 'A') { const c = scoutContract(r.text); brief = c ? c.brief : null; }
    else { const p = parseScoutBriefV2(r.text); if (p && p.declined) declined = true; else brief = p; }
    return { id: r.id, brief, declined, qa_user: brief ? qaMessage({ brief, trends: [] }) : null, qa_parse: r.qa_text ? qaContract(r.qa_text) : null };
  });
  process.stdout.write(JSON.stringify(out));
}
