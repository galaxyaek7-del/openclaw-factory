// Scout prompt v2: parser contract, decline path, and the off-by-default flag (2026-11-06).
const assert = require('assert');
const { scoutBriefPromptV2, parseScoutBriefV2, V2_SYSTEM } = require('../lib/scout_brief_v2');
const good = '##TITLE##\nBreak-Even Calculator for a Small Shop\n##TOPIC##\nComputes monthly break-even sales.\n##AUDIENCE##\nShop owners\n##PRICE##\n$29\n##CHAPTERS##\n6';
const p = parseScoutBriefV2(good);
assert.strictEqual(p.title, 'Break-Even Calculator for a Small Shop'); assert.strictEqual(p.price, 29); assert.strictEqual(p.chapters, 6);
assert.strictEqual(parseScoutBriefV2(good.replace('$29', '$99')), null, 'price outside 9-49 is a contract failure');
assert.strictEqual(parseScoutBriefV2(good.replace('6', '12')), null, 'chapters outside 4-9 is a contract failure');
assert.strictEqual(parseScoutBriefV2('no sections here'), null);
const d = parseScoutBriefV2('##TITLE##\nNONE\n##TOPIC##\nno money decision behind this input\n##AUDIENCE##\nnone\n##PRICE##\n0\n##CHAPTERS##\n0');
assert.strictEqual(d.declined, true);
assert.ok(/NONE/.test(scoutBriefPromptV2('x')) && /Input[^\n]*x/.test(scoutBriefPromptV2('x')));
assert.ok(/Excel workbooks/.test(V2_SYSTEM));

const rc = (v) => { delete require.cache[require.resolve('../lib/research_chain')]; if (v === undefined) delete process.env.GF_SCOUT_PROMPT; else process.env.GF_SCOUT_PROMPT = v; return require('../lib/research_chain'); };
let c = rc(undefined);
assert.ok(c.researchSteps()[0].config.system.includes('كتب') || !c.researchSteps()[0].config.system.includes('Excel workbooks'), 'default is v1');
assert.ok(c.scoutContract(good.replace('$29', '$99')), 'v1 contract is unchanged: it accepts a $99 brief that v2 refuses');
c = rc('v2');
assert.ok(c.researchSteps()[0].config.system.includes('Excel workbooks'), 'flag selects v2 system prompt');
assert.ok(c.scoutContract(good).brief.price === 29);
assert.ok(c.researchSteps()[1].config.system.includes('BRIEF'), 'flag also selects the matched QA reviewer');
assert.strictEqual(c.scoutContract('##TITLE##\nNONE\n##TOPIC##\nx'), null, 'a decline never becomes a brief');
rc(undefined);
console.log('test_scout_brief_v2: ok');
