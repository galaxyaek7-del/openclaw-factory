const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const qa = require('../lib/qa_engine');

function tempFile(content, ext = '.txt') {
  const p = path.join(os.tmpdir(), `qa_test_${Date.now()}_${Math.random().toString(36).slice(2)}${ext}`);
  fs.writeFileSync(p, content, 'utf8');
  return p;
}

test('valid high-quality text content — QA_APPROVED', () => {
  const content = `# Product Title
This is a well structured text product with clear introduction.

Second paragraph explains the value proposition for the target audience. It has enough length and no repetition. Price is $49.

Third paragraph concludes with benefits and audience fit.`;
  const res = qa.evaluate({ content, productType: 'text', contentType: 'text/markdown', classification: 'TEST' });
  assert.equal(res.product_type, 'text');
  assert.ok(res.score >= 80, `expected high score, got ${res.score}`);
  assert.equal(res.verdict, 'QA_APPROVED');
  assert.equal(res.passed, true);
  assert.equal(res.issues.length, 0);
  assert.ok(res.criteria.length >= 6);
  assert.ok(res.evidence);
  assert.equal(res.classification, 'TEST');
});

test('empty content — QA_REJECTED with clear issue', () => {
  const res = qa.evaluate({ content: '   ', productType: 'text', classification: 'TEST' });
  assert.equal(res.verdict, 'QA_REJECTED');
  assert.equal(res.passed, false);
  assert.ok(res.issues.some(i => /empty/i.test(i)), 'should have empty issue');
  assert.ok(res.criteria.find(c => c.name === 'not_empty' && c.passed === false));
  assert.equal(res.score < 50, true);
});

test('repetitive content — detects excessive repetition', () => {
  const rep = Array(30).fill('buy now buy now buy now').join(' ');
  const res = qa.evaluate({ content: rep, productType: 'text', classification: 'TEST' });
  assert.ok(res.issues.some(i => /repetition/i.test(i)) || res.criteria.find(c => c.name === 'no_repetition' && !c.passed));
  assert.equal(res.verdict, 'QA_REJECTED');
});

test('incomplete content — missing required elements for B2B', () => {
  const content = 'Just a short line';
  const res = qa.evaluate({ content, productType: 'b2b', classification: 'TEST' });
  // B2B requires value, audience, pricing — this short line misses them
  assert.ok(res.issues.length > 0);
  assert.equal(res.product_type, 'b2b');
  const reqCrit = res.criteria.find(c => c.name === 'required_elements');
  assert.ok(reqCrit && !reqCrit.passed);
});

test('unsupported content type — UNKNOWN / REVIEW_REQUIRED', () => {
  const res = qa.evaluate({ content: 'hello world', productType: 'unknown_type_xyz', classification: 'TEST' });
  assert.equal(res.verdict, 'QA_REVIEW_REQUIRED');
  assert.equal(res.classification, 'UNKNOWN');
  assert.ok(res.issues[0].includes('Unsupported'));

  const res2 = qa.evaluate({ content: 'test', productType: 'video', classification: 'TEST' });
  assert.equal(res2.verdict, 'QA_REVIEW_REQUIRED');
  assert.equal(res2.classification, 'UNKNOWN');
  assert.ok(res2.issues[0].includes('Video not supported'));
});

test('B2B output — product-type-specific criteria', () => {
  const content = `Value Proposition: We help agencies automate lead enrichment and save 10 hours per week.
Audience: B2B agencies with 10-50 employees who struggle with manual prospecting.
Pricing: $49/month includes CRM sync and dedicated support.

Our solution saves 10 hours per week and provides detailed analytics for every campaign. The value is clear, the audience is defined, and pricing is transparent.`;
  const res = qa.evaluate({ content, productType: 'b2b', classification: 'TEST' });
  assert.equal(res.product_type, 'b2b');
  assert.ok(res.criteria.find(c => c.name === 'structure' && c.passed));
  assert.ok(res.score >= 70);
  // Should not use same criteria as visual
  const visualRes = qa.evaluate({ content, productType: 'visual', filePath: tempFile('dummy'), classification: 'TEST' });
  assert.notEqual(res.criteria.length, visualRes.criteria.length, 'B2B and visual should have different criteria counts');
});

test('digital product output — requires file and structure', () => {
  const tmp = tempFile('dummy image content', '.png');
  const content = `# My Digital Planner
Title: Daily Planner
This digital product has a cover and interior with habit tracker. Price $19.
${'This planner helps you organize goals and track habits daily. '.repeat(20)}`;
  const res = qa.evaluate({ content, productType: 'digital_product', filePath: tmp, classification: 'TEST' });
  assert.equal(res.product_type, 'digital_product');
  assert.ok(res.score >= 60, `expected >=60, got ${res.score} issues:${res.issues.join(';')}`);
  try { fs.unlinkSync(tmp); } catch (_) {}
  // Without filePath, should warn
  const res2 = qa.evaluate({ content, productType: 'digital_product', classification: 'TEST' });
  assert.ok(res2.warnings.length > 0 || res2.issues.length > 0, 'missing file should warn/issue');
});

test('code product — detects TODO and structure', () => {
  const goodCode = `function add(a,b){ return a+b; }\nmodule.exports = {add};`;
  const resGood = qa.evaluate({ content: goodCode, productType: 'code', contentType: 'application/javascript', classification: 'TEST' });
  assert.ok(resGood.passed || resGood.verdict === 'QA_APPROVED' || resGood.verdict === 'QA_REVIEW_REQUIRED');

  const badCode = `// TODO: implement\nfunction foo(){ return undefined; } // undefined left`;
  const resBad = qa.evaluate({ content: badCode, productType: 'code', classification: 'TEST' });
  assert.ok(resBad.warnings.length > 0 || resBad.issues.length > 0, 'should flag TODO');
  assert.equal(resBad.criteria.find(c => c.name === 'no_todo').passed, false);
});

test('regression — improving one dimension should not collapse others (visual vs text)', () => {
  const base = qa.evaluate({ content: '# Title\n' + 'Good content '.repeat(30), productType: 'text', classification: 'TEST' });
  // Simulate improving length but adding repetition
  const rep = 'word '.repeat(50) + 'word '.repeat(50);
  const repRes = qa.evaluate({ content: rep, productType: 'text', classification: 'TEST' });
  // Repetitive should be REJECTED even if length is good
  assert.equal(repRes.verdict, 'QA_REJECTED');
  // Base should not be REJECTED just for length
  assert.ok(base.score > repRes.score, 'repetitive should score lower than good');
});

test('TEST/REAL isolation — temp-path isolation', () => {
  // The engine confines caller paths to the repo root (security hardening), so the REAL-side file must live inside it;
  // an os.tmpdir() file is correctly "not found" there. Removed at the end of the test.
  const tmp1 = path.join(__dirname, '..', `.qa_isolation_${process.pid}_${Date.now()}.md`);
  fs.writeFileSync(tmp1, '# Temp Title\nTemp content for isolation test, enough length to pass. Price $10. Audience test.', 'utf8');
  const tmp2 = tempFile('TODO leftover', '.txt');
  const longContent = `# Real Production Title
Title: Real Digital Product with cover and interior
## Overview
This digital product has a cover and interior designed for productivity. Price $29. It helps professionals organize workflow with structured templates.
## Features
Includes habit tracker, goal setting, and daily planning sheets. The cover is professionally designed and the interior is optimized for printing and clarity.
## Benefits
Users report improved focus and consistent execution across weeks. Built for real users needing tangible results and measurable progress.`;
  const resReal = qa.evaluate({ content: longContent, productType: 'digital_product', filePath: tmp1, classification: 'REAL' });
  const resTest = qa.evaluate({ content: '   ', productType: 'text', filePath: tmp2, classification: 'TEST' });
  assert.equal(resReal.classification, 'REAL');
  assert.equal(resTest.classification, 'TEST');
  assert.notEqual(resReal.verdict, resTest.verdict);
  try { fs.unlinkSync(tmp1); } catch (_) {}
  try { fs.unlinkSync(tmp2); } catch (_) {}
  // Ensure temp files did not pollute real factory files
  assert.equal(fs.existsSync(path.join(__dirname, '..', 'data', 'factory_lock.json')), false, 'real lock should not exist after isolated test');
});

test('issues handling — no nested issues.issues.push bug', () => {
  const res = qa.evaluate({ content: '', productType: 'text', classification: 'TEST' });
  // issues must be flat array, not nested
  assert.ok(Array.isArray(res.issues));
  assert.equal(res.issues.some(i => typeof i === 'object' && i.issues), false, 'should not have nested issues.issues');
  assert.ok(res.warnings && Array.isArray(res.warnings));
  assert.ok(res.strengths && Array.isArray(res.strengths));
  // Ensure no accidental logic like issues.issues.push ?
  assert.equal(typeof res.issues.push, 'function');
});

test('contentType handling correctly', () => {
  const res1 = qa.evaluate({ content: 'hello', productType: 'text', contentType: 'TEXT/PLAIN', classification: 'TEST' });
  assert.equal(res1.contentType, 'text/plain');
  const res2 = qa.evaluate({ content: 'code', productType: 'code', contentType: 'javascript', classification: 'TEST' });
  assert.equal(res2.contentType, 'application/javascript');
  const res3 = qa.evaluate({ content: 'x', productType: 'text', contentType: null, classification: 'TEST' });
  assert.equal(res3.contentType, 'text/plain');
});

test('score not always 100 minus arbitrary — traceable weighted criteria', () => {
  const res = qa.evaluate({ content: '# Title\n' + 'Valid content '.repeat(20), productType: 'text', classification: 'TEST' });
  const totalWeight = res.criteria.reduce((a,c)=>a+c.weight,0);
  const passedWeight = res.criteria.filter(c=>c.passed).reduce((a,c)=>a+c.weight,0);
  const expected = Math.round((passedWeight/totalWeight)*100);
  assert.equal(res.score, expected, 'score must be weighted, not arbitrary');
});

test('UNKNOWN when evidence missing', () => {
  const res = qa.evaluate({ content: null, productType: 'visual', filePath: null, classification: 'TEST' });
  // No file, no content — should be REJECTED or REVIEW_REQUIRED with UNKNOWN evidence
  assert.ok(res.verdict === 'QA_REJECTED' || res.verdict === 'QA_REVIEW_REQUIRED');
  assert.ok(res.evidence.file_exists && res.evidence.file_exists.includes('UNKNOWN') || res.evidence.file_exists === 'no');
});
