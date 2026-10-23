// Galaxy Forge -- product chain: all six agents, ending at the founder gate (2026-10-23).
//
// Extends the research chain (lib/research_chain.js) into a complete product
// proposal, one handoff at a time, each step's validated output becoming the
// next step's context:
//   scout_brief      scout writes a brief from today's commercial trends
//   qa_review        qa: PASS continues, REVISE stops the chain (a decision)
//   finance_pricing  finance: price + platform + reason
//   design_brief     design: cover + interior direction
//   builder_outline  builder: chapter outline
//   publisher_listing publisher: listing title, description, tags
//   package          writes drafts/agent_packages/<task_id>.json, status
//                    AWAITING_FOUNDER_REVIEW (internal, reversible)
//   distribute       protected: refused unless FACTORY_LIVE_PUBLISH is true;
//                    even then it does nothing -- publishing stays a separate,
//                    founder-run action.
// Nothing here produces a file for sale, publishes, charges or messages anyone.

const fs = require('fs');
const path = require('path');
const AGENT_PROMPTS = require('./agent_prompts');
const { researchSteps } = require('./research_chain');

const PACKAGES_DIR = path.join(__dirname, '..', 'drafts', 'agent_packages');

function briefText(b) {
  return [`Title: ${b.title}`, `Topic: ${b.topic}`, `Audience: ${b.audience}`, `Suggested price (USD): ${b.price}`,
    `Chapters: ${b.chapters}`].join('\n');
}

function field(content, label) {
  const m = new RegExp(`^\\s*${label}:\\s*(.+)$`, 'im').exec(content || '');
  return m ? m[1].trim() : null;
}

function financeContract(content) {
  const price = Number(String(field(content, 'PRICE_USD') || '').replace(/[^0-9.]/g, ''));
  const platform = (field(content, 'PLATFORM') || '').toLowerCase();
  if (!(price >= 1 && price <= 1000) || !/gumroad|etsy|kdp|payhip/.test(platform)) return null;
  return { pricing: { price_usd: price, platform: platform.match(/gumroad|etsy|kdp|payhip/)[0], reason: (field(content, 'REASON') || '').slice(0, 300) } };
}

function designContract(content) {
  const cover = field(content, 'COVER');
  const interior = field(content, 'INTERIOR');
  if (!cover || !interior) return null;
  return { design: { cover: cover.slice(0, 400), interior: interior.slice(0, 400), palette: (field(content, 'PALETTE') || '').slice(0, 200) } };
}

function outlineContract(content) {
  const chapters = [...String(content || '').matchAll(/^\s*CHAPTER\s*\d+\s*[:.-]\s*(.+)$/gim)].map((m) => m[1].trim().slice(0, 160));
  if (chapters.length < 3) return null;
  return { outline: chapters.slice(0, 20) };
}

function listingContract(content) {
  const title = field(content, 'TITLE');
  const description = field(content, 'DESCRIPTION');
  const tags = (field(content, 'TAGS') || '').split(',').map((t) => t.trim()).filter(Boolean);
  if (!title || !description || tags.length < 3) return null;
  return { listing: { title: title.slice(0, 140), description: description.slice(0, 1000), tags: tags.slice(0, 13) } };
}

const ask = (lines) => lines.join('\n');

function productSteps({ packagesDir = PACKAGES_DIR, now = () => new Date() } = {}) {
  const [scout, qa, distribute] = researchSteps();
  qa.stopIf = (ctx) => (ctx.qa_verdict === 'REVISE' ? `qa REVISE: ${ctx.qa_reason || ''}` : null);
  return [
    scout,
    qa,
    { id: 'finance_pricing', agent: 'finance', config: AGENT_PROMPTS.finance, parse: financeContract,
      buildMessage: (ctx) => ask(['Price this product brief. Reply with exactly three lines:',
        'PRICE_USD: a number', 'PLATFORM: gumroad, etsy, kdp or payhip', 'REASON: one sentence', '', briefText(ctx.brief)]) },
    { id: 'design_brief', agent: 'design', config: AGENT_PROMPTS.design, parse: designContract,
      buildMessage: (ctx) => ask(['Give the design direction for this product. Reply with exactly three lines:',
        'COVER: one sentence', 'INTERIOR: one sentence', 'PALETTE: colors', '', briefText(ctx.brief)]) },
    { id: 'builder_outline', agent: 'builder', config: AGENT_PROMPTS.builder, parse: outlineContract,
      buildMessage: (ctx) => ask([`Write the chapter outline for this product, ${Math.max(3, Math.min(ctx.brief.chapters || 6, 12))} chapters.`,
        'One line per chapter, exactly in the form: CHAPTER 1: <title> - <what the reader gets>', '', briefText(ctx.brief)]) },
    { id: 'publisher_listing', agent: 'publisher', config: AGENT_PROMPTS.publisher, parse: listingContract,
      buildMessage: (ctx) => ask(['Write the store listing in English. Reply with exactly three lines:',
        'TITLE: listing title', 'DESCRIPTION: two or three sentences, no fake urgency, no invented reviews',
        'TAGS: comma-separated, at least five', '', briefText(ctx.brief),
        `Platform: ${ctx.pricing.platform}`, `Price (USD): ${ctx.pricing.price_usd}`]) },
    { id: 'package', local: true, run: (ctx) => {
      fs.mkdirSync(packagesDir, { recursive: true });
      const file = path.join(packagesDir, `${ctx.task_id}.json`);
      const pkg = { task_id: ctx.task_id, created_at: now().toISOString(), status: 'AWAITING_FOUNDER_REVIEW',
        note: 'Agent proposal only. Nothing was produced for sale, published, priced on a store, or sent.',
        trends: ctx.trends || [], brief: ctx.brief, qa: { verdict: ctx.qa_verdict, reason: ctx.qa_reason },
        pricing: ctx.pricing, design: ctx.design, outline: ctx.outline, listing: ctx.listing };
      fs.writeFileSync(file, JSON.stringify(pkg, null, 2));
      return { package_path: path.relative(path.join(__dirname, '..'), file).replace(/\\/g, '/') };
    } },
    distribute,
  ];
}

module.exports = { productSteps, financeContract, designContract, outlineContract, listingContract, PACKAGES_DIR };
