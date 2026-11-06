// Galaxy Forge -- Scout brief prompt v2, aimed at the CURRENT business (2026-11-06).
//
// v1 (lib/scout_brief.js) asks for "one digital BOOK niche for immediate Amazon KDP publication, price >= $30", fed by the
// day's raw search trends ("when is black friday 2026", "car accident attorney"). The company now sells $9-49 Excel
// workbooks with a PDF guide on Gumroad, and QA stopped 5 of 16 chain runs as "unrelated trends". v2 changes three things:
//   1. the deliverable is a spreadsheet tool (workbook + short guide) for a named buyer with a recurring money decision;
//   2. the input is a PROBLEM or QUESTION real people asked, and the scout must work from the problem, not the trend;
//   3. the scout may decline: when the input has no small-business or personal-finance decision behind it, the honest
//      answer is "##TITLE## NONE", never an invented niche.
// Selected by GF_SCOUT_PROMPT=v2 (default stays v1 until the evaluation in reports/SCOUT_EVAL.md justifies the switch).

const V2_SYSTEM = `You are the market scout of Galaxy Forge, a company that sells Excel workbooks with a short PDF guide to small-business owners, freelancers and households, at $9 to $49, on Gumroad. You never chase a trend for its own sake. You look for a recurring money decision that a buyer cannot make well with a blank spreadsheet, and you propose one tool for it. If the input contains no such decision, you say so.`;

function scoutBriefPromptV2(evidence) {
  const input = evidence && String(evidence).trim() ? String(evidence).trim() : null;
  return `${input ? `Input (a question or problem real people asked, or a trend): ${input}\n` : 'Input: none given. Propose the strongest recurring money decision for small-business owners.\n'}
Propose ONE spreadsheet tool (an Excel workbook with a short PDF guide) that helps a named buyer make a recurring money decision.

Rules:
- Work from the PROBLEM behind the input, not from the input's topic. A trend about TVs or Black Friday is not a business decision; if the input has no small-business, freelance, investing or household-money decision behind it, answer exactly:
##TITLE##
NONE
##TOPIC##
no money decision behind this input
##AUDIENCE##
none
##PRICE##
0
##CHAPTERS##
0
- Otherwise name ONE buyer (a specific kind of person) and ONE decision, and a title in English that says what the tool computes (for example "Break-Even and Startup Cash Needed for a Small Shop").
- The tool is a workbook (inputs, calculations, a verdict) plus a short guide. It is not a book, journal, planner of habits or video course.
- PRICE is a whole number of US dollars between 9 and 49, justified by how costly a wrong decision is for the buyer.
- CHAPTERS is the number of guide sections, an integer from 4 to 9.

Use exactly this format and nothing else:
##TITLE##
<English title>
##TOPIC##
<one sentence: the decision and what the workbook computes>
##AUDIENCE##
<the buyer>
##PRICE##
<integer 9-49>
##CHAPTERS##
<integer 4-9>`;
}

// Same section parser as v1 plus the explicit decline. -> {declined: true} | {title, topic, audience, price, chapters} | null
function parseScoutBriefV2(text) {
  const section = (tag) => {
    const m = String(text || '').match(new RegExp(`##${tag}##\\s*([\\s\\S]*?)(?=##[A-Z]+##|$)`, 'i'));
    return m ? m[1].trim() : '';
  };
  const title = section('TITLE');
  if (!title) return null;
  if (/^none\b/i.test(title)) return { declined: true, reason: section('TOPIC').slice(0, 200) };
  const price = parseInt(section('PRICE').replace(/[^0-9]/g, ''), 10);
  const chapters = parseInt(section('CHAPTERS').replace(/[^0-9]/g, ''), 10);
  const topic = section('TOPIC'), audience = section('AUDIENCE');
  if (title.length < 5 || !topic || !audience || !(price >= 9 && price <= 49) || !(chapters >= 4 && chapters <= 9)) return null;
  return { title, topic, audience, price, chapters };
}

module.exports = { V2_SYSTEM, scoutBriefPromptV2, parseScoutBriefV2 };
