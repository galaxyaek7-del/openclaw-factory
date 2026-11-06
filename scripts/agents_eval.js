// Offline A/B of the four production agents (finance, design, builder, publisher): v1 (KDP/Etsy personas) vs v2 (workbook business).
// Inputs: the briefs Scout v2 produced that QA passed (data/scout_eval.json). Nothing is published; costs cents.
//   node scripts/agents_eval.js  -> data/agents_eval.json
const fs = require('fs'), path = require('path');
require('dotenv').config({ path: path.join(__dirname, '..', '.env'), quiet: true });
const Groq = require('groq-sdk');
const AGENT_PROMPTS = require('../lib/agent_prompts');
const { PERSONAS_V2 } = require('../lib/agent_personas_v2');
const pc = require('../lib/product_chain');
const root = path.join(__dirname, '..');
const key = process.env.GROQ_KEY || process.env.GROQ_API_KEY;
const client = new Groq({ apiKey: key });
const MODEL = 'openai/gpt-oss-20b';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function call(system, user) {
  let last;
  for (let k = 0; k < 3; k++) {
    try {
      const r = await client.chat.completions.create({ model: MODEL, max_tokens: 3000, messages: [{ role: 'system', content: system }, { role: 'user', content: user }] });
      const t = r.choices[0].message.content; if (t && t.trim()) return t;
    } catch (e) { last = e; }
    await sleep(4000 * (k + 1));
  }
  throw last || new Error('empty');
}
const briefText = (b) => [`Title: ${b.title}`, `Topic: ${b.topic}`, `Audience: ${b.audience}`, `Suggested price (USD): ${b.price}`, `Chapters: ${b.chapters}`].join('\n');
const BOOKISH = /\b(kdp|amazon|etsy|kindle|paperback|hardcover|book|novel|ebook|e-book|isbn)\b/i;
async function runVariant(v, b) {
  const sys = (n) => (v === 'B' ? PERSONAS_V2[n] : AGENT_PROMPTS[n].system);
  const out = { variant: v, id: b.id, checks: {} };
  const fin = pc.financeContract(await call(sys('finance'), ['Price this product brief. Reply with exactly three lines:', 'PRICE_USD: a number', 'PLATFORM: gumroad, etsy, kdp or payhip', 'REASON: one sentence', '', briefText(b)].join('\n')));
  out.checks.finance_contract = !!fin; out.checks.finance_gumroad = !!fin && fin.pricing.platform === 'gumroad';
  out.checks.finance_price_in_range = !!fin && fin.pricing.price_usd >= 9 && fin.pricing.price_usd <= 49;
  const des = pc.designContract(await call(sys('design'), ['Give the design direction for this product. Reply with exactly three lines:', 'COVER: one sentence', 'INTERIOR: one sentence', 'PALETTE: colors', '', briefText(b)].join('\n')));
  out.checks.design_contract = !!des; out.checks.design_not_bookish = !!des && !BOOKISH.test(des.design.cover + ' ' + des.design.interior);
  const n = Math.max(3, Math.min(b.chapters || 6, 12));
  const ol = pc.outlineContract(await call(sys('builder'), [`Write the chapter outline for this product, ${n} chapters.`, 'One line per chapter, exactly in the form: CHAPTER 1: <title> - <what the reader gets>', '', briefText(b)].join('\n')));
  out.checks.outline_contract = !!ol; out.checks.outline_count_ok = !!ol && ol.outline.length >= n - 1 && ol.outline.length <= n + 1;
  out.checks.outline_not_bookish = !!ol && !BOOKISH.test(ol.outline.join(' '));
  const plat = fin ? fin.pricing.platform : 'gumroad', price = fin ? fin.pricing.price_usd : b.price;
  const li = pc.listingContract(await call(sys('publisher'), ['Write the store listing in English. Reply with exactly three lines:', 'TITLE: listing title', 'DESCRIPTION: two or three sentences, no fake urgency, no invented reviews', 'TAGS: comma-separated, at least five', '', briefText(b), `Platform: ${plat}`, `Price (USD): ${price}`].join('\n')));
  out.checks.listing_contract = !!li; out.checks.listing_not_bookish = !!li && !BOOKISH.test(li.listing.title + ' ' + li.listing.description + ' ' + li.listing.tags.join(' '));
  out.checks.listing_mentions_xlsx = !!li && /xlsx|excel|spreadsheet|workbook/i.test(li.listing.description);
  return out;
}
(async () => {
  const ev = JSON.parse(fs.readFileSync(path.join(root, 'data', 'scout_eval.json'), 'utf8')).rows.filter((r) => r.verdict === 'PASS' && r.variant !== 'A');
  const briefs = ev.slice(0, 6).map((r) => ({ id: r.id, title: r.title, price: r.price, topic: `A workbook that computes the decision behind: ${r.title}`, audience: 'small-business owners, freelancers and households', chapters: 6 }));
  const rows = [];
  for (const b of briefs) for (const v of ['A', 'B']) { try { rows.push(await runVariant(v, b)); } catch (e) { rows.push({ variant: v, id: b.id, error: String(e.message || e).slice(0, 80) }); } }
  const sum = {};
  for (const v of ['A', 'B']) {
    const rs = rows.filter((r) => r.variant === v && r.checks); const t = {};
    for (const r of rs) for (const [k, val] of Object.entries(r.checks)) { t[k] = (t[k] || 0) + (val ? 1 : 0); }
    sum[v] = { briefs: rs.length, errors: rows.filter((r) => r.variant === v && r.error).length, passes: t };
  }
  fs.writeFileSync(path.join(root, 'data', 'agents_eval.json'), JSON.stringify({ at: new Date().toISOString(), summary: sum, rows }, null, 1));
  console.log(JSON.stringify(sum));
})();
