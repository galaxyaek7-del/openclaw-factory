// Tests for services/umrah_assistant/validate_agency.js and build_demo.js (personalised demo for a prospect).
//
//   node --test tests/test_umrah_agency.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { validate, validateFile } = require('../services/umrah_assistant/validate_agency.js');
const { build } = require('../services/umrah_assistant/build_demo.js');
const A = require('../services/umrah_assistant/engine.js');

const DIR = path.join(__dirname, '..', 'services', 'umrah_assistant');
const clone = (o) => JSON.parse(JSON.stringify(o));
const EXAMPLE = JSON.parse(fs.readFileSync(path.join(DIR, 'agency_example.json'), 'utf8'));

function realAgency() {
  const a = clone(EXAMPLE);
  a._status = 'REAL';
  a._note = 'data given by the agency';
  a.name = { ar: 'وكالة الأمل للعمرة', fr: 'Agence El Amel Omra' };
  a.phone = '0661 00 11 22';
  a.packages = a.packages.slice(0, 2);
  a.packages[0].price_dzd = 199000;
  a.departures = [{ date: '2099-03-01', packages: [a.packages[0].id, a.packages[1].id] }];
  return a;
}

test('the fictional example is usable and flagged SIMULATION', () => {
  const r = validate(EXAMPLE);
  assert.equal(r.ok, true, r.errors.join('; '));
  assert.equal(r.status, 'SIMULATION');
  assert.ok(r.warnings.some((w) => /SIMULATION/.test(w)));
});

test('the blank template is refused, with every unfilled field named', () => {
  const r = validateFile(path.join(DIR, 'agency_template.json'));
  assert.equal(r.ok, false);
  assert.ok(r.errors.some((e) => /unfilled placeholder at name\.ar/.test(e)));
  assert.ok(r.errors.some((e) => /price_dzd/.test(e)));
});

test('a real agency with real values passes', () => {
  const r = validate(realAgency());
  assert.equal(r.ok, true, r.errors.join('; '));
  assert.equal(r.status, 'REAL');
});

test('status must be REAL or SIMULATION', () => {
  const a = realAgency(); delete a._status;
  assert.equal(validate(a).ok, false);
  a._status = 'maybe';
  assert.equal(validate(a).ok, false);
});

test('a REAL file that still says example/fictional is refused', () => {
  const a = realAgency(); a.name.fr = 'Agence Ennour (exemple)';
  assert.ok(validate(a).errors.some((e) => /fictional|example/.test(e)));
});

test('placeholders: error for REAL data, only a warning for simulation data', () => {
  const real = realAgency(); real.phone = '05 XX XX XX XX';
  assert.equal(validate(real).ok, false);
  assert.equal(validate(EXAMPLE).ok, true);
});

test('prices, deposit, days and stars are checked', () => {
  for (const [mutate, re] of [
    [(a) => { a.packages[0].price_dzd = 0; }, /price_dzd/],
    [(a) => { a.packages[0].price_dzd = 285000.5; }, /price_dzd/],
    [(a) => { a.packages[0].days = -3; }, /days/],
    [(a) => { a.packages[0].makkah.stars = 7; }, /stars/],
    [(a) => { a.packages[0].madinah.distance_m = -1; }, /distance_m/],
    [(a) => { a.deposit_dzd = 999999; }, /deposit_dzd must be lower/],
    [(a) => { a.balance_days_before = 0; }, /balance_days_before/],
  ]) {
    const a = realAgency(); mutate(a);
    const r = validate(a);
    assert.equal(r.ok, false, String(re));
    assert.ok(r.errors.some((e) => re.test(e)), String(re) + ' -> ' + r.errors.join('; '));
  }
});

test('an implausible price is a warning (typo guard), not an error', () => {
  const a = realAgency(); a.packages[0].price_dzd = 28500; a.deposit_dzd = 10000;
  const r = validate(a);
  assert.equal(r.ok, true);
  assert.ok(r.warnings.some((w) => /too low/.test(w)));
});

test('packages and departures must be consistent', () => {
  let a = realAgency(); a.packages[1].id = a.packages[0].id;
  assert.ok(validate(a).errors.some((e) => /duplicated/.test(e)));
  a = realAgency(); a.departures[0].packages = ['does-not-exist'];
  assert.ok(validate(a).errors.some((e) => /unknown package id/.test(e)));
  a = realAgency(); a.departures[0].date = '01/03/2099';
  assert.ok(validate(a).errors.some((e) => /YYYY-MM-DD/.test(e)));
  a = realAgency(); a.departures = [];
  assert.equal(validate(a).ok, false);
});

test('a past departure is only a warning', () => {
  const a = realAgency(); a.departures[0].date = '2020-01-01';
  const r = validate(a);
  assert.equal(r.ok, true);
  assert.ok(r.warnings.some((w) => /in the past/.test(w)));
});

test('lists must be non-empty in both languages; different lengths only warn', () => {
  let a = realAgency(); a.documents.fr = [];
  assert.equal(validate(a).ok, false);
  a = realAgency(); a.documents.fr = a.documents.fr.slice(0, 2);
  const r = validate(a);
  assert.equal(r.ok, true);
  assert.ok(r.warnings.some((w) => /documents: Arabic has/.test(w)));
});

test('building refuses unusable data and leaves no output', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'umrah-'));
  const file = path.join(dir, 'bad.json');
  fs.writeFileSync(file, fs.readFileSync(path.join(DIR, 'agency_template.json')));
  assert.throws(() => build({ agencyFile: file, outDir: path.join(dir, 'out') }), /agency data not usable/);
  assert.equal(fs.existsSync(path.join(dir, 'out', 'index.html')), false);
});

test('a real agency gets its own demo: its name and prices, an honest banner, no leftover markers', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'umrah-'));
  const file = path.join(dir, 'amel.json');
  const a = realAgency();
  fs.writeFileSync(file, JSON.stringify(a));
  const r = build({ agencyFile: file, outDir: path.join(dir, 'out') });
  const html = fs.readFileSync(r.out, 'utf8');
  assert.equal(r.status, 'REAL');
  assert.ok(html.includes('وكالة الأمل للعمرة'));
  assert.ok(html.includes('199000'));
  assert.ok(html.includes("_status === 'REAL'"), 'the page switches to the real-agency banner');
  assert.ok(html.includes('لوكالتكم'));
  assert.ok(!html.includes('/*AGENCY_JSON*/') && !html.includes('/*ENGINE_JS*/'));
});

test('agency text can never break out of the page script', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'umrah-'));
  const file = path.join(dir, 'x.json');
  const a = realAgency();
  a.name.fr = 'Agence </script><script>alert(1)</script> Omra';
  fs.writeFileSync(file, JSON.stringify(a));
  const html = fs.readFileSync(build({ agencyFile: file, outDir: path.join(dir, 'out') }).out, 'utf8');
  assert.ok(!html.includes('</script><script>alert(1)'));
  assert.ok(html.includes('\\u003c/script'));
});

test('the assistant answers with the prospect\'s own numbers, not the example\'s', () => {
  const a = realAgency();
  const s = A.newSession();
  const price = A.respond(a, s, 'Quel est le prix ?').text;
  assert.match(price, /199 000 DA/);
  assert.doesNotMatch(price, /285 000/);
  assert.match(A.respond(a, s, 'Quand partir ?').text, /1 mars 2099/);
  assert.doesNotMatch(A.respond(a, s, 'Quand partir ?').text, /2026|2027/);
  const booking = ['Je veux réserver', a.packages[0].names.fr, '2', 'Sami', '0661234567'];
  let last;
  for (const m of booking) last = A.respond(a, s, m);
  assert.equal(last.handoff.estimate_dzd, 199000 * 2);
  assert.match(last.text, /0661234567/);
});

test('the committed example demo is up to date with its sources', () => {
  const html = fs.readFileSync(path.join(DIR, 'demo', 'index.html'), 'utf8');
  const engine = fs.readFileSync(path.join(DIR, 'engine.js'), 'utf8');
  assert.ok(html.includes(engine), 'run: node services/umrah_assistant/build_demo.js');
  assert.ok(html.includes(JSON.stringify(EXAMPLE).replace(/</g, '\\u003c')), 'run: node services/umrah_assistant/build_demo.js');
});
