// Customer Experience & Brand DNA (ADR-170, 2026-08-05): drift guard for
// server.js's COMPANY_PERSONALITY_PREAMBLE against brand_dna.py's real
// canonical COMPANY_PERSONALITY definition. Deliberately NOT a live Python
// call at request time (would add real startup-time coupling for a static
// string that basically never changes, against this ADR's own "do not
// overengineer" instruction) -- instead, this test spawns Python once,
// offline, to fetch the real trait keys and cross-checks that server.js's
// hand-authored Arabic preamble still mentions the concept behind each one.
//
//   node tests/test_brand_dna_preamble_consistency.js

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const SERVER_JS = path.join(__dirname, '..', 'server.js');

// Arabic (or transliteration-safe) keyword expected in the preamble for
// each real brand_dna.py trait -- maintained by hand alongside the
// preamble text itself; a missing trait here is the real drift signal.
const EXPECTED_KEYWORDS = {
  professional: 'احترافي',
  honest: 'صادق',
  respectful: 'محترم',
  calm: 'هادئ',
  helpful: 'متعاون',
  transparent: 'شفّاف',
  intelligent: 'ذكي',
  premium: 'متميز',
  human_like_without_pretending_to_be_human: 'التظاهر بأنك إنسان',
};

function extractPreamble() {
  const src = fs.readFileSync(SERVER_JS, 'utf-8');
  const m = src.match(/const COMPANY_PERSONALITY_PREAMBLE = `([\s\S]*?)`;/);
  assert.ok(m, 'COMPANY_PERSONALITY_PREAMBLE constant not found in server.js');
  return m[1];
}

function realTraitNames() {
  const out = execFileSync('python', ['-c', 'import json, brand_dna; print(json.dumps(list(brand_dna.COMPANY_PERSONALITY.keys())))'], {
    cwd: path.join(__dirname, '..'),
    encoding: 'utf-8',
  });
  return JSON.parse(out);
}

let passed = 0;
function test(name, fn) {
  try {
    fn();
    console.log(`ok - ${name}`);
    passed++;
  } catch (err) {
    console.error(`FAIL - ${name}`);
    console.error(err);
    process.exitCode = 1;
  }
}

test('COMPANY_PERSONALITY_PREAMBLE exists in server.js', () => {
  const preamble = extractPreamble();
  assert.ok(preamble.length > 20);
});

test('every real brand_dna.py trait has a matching keyword in the JS preamble', () => {
  const preamble = extractPreamble();
  const traits = realTraitNames();
  for (const trait of traits) {
    const keyword = EXPECTED_KEYWORDS[trait];
    assert.ok(keyword, `no expected keyword registered in this test for trait ${trait} -- update EXPECTED_KEYWORDS`);
    assert.ok(preamble.includes(keyword), `preamble missing keyword "${keyword}" for trait ${trait}`);
  }
});

test('EXPECTED_KEYWORDS has no stale entries for traits that no longer exist', () => {
  const traits = new Set(realTraitNames());
  for (const key of Object.keys(EXPECTED_KEYWORDS)) {
    assert.ok(traits.has(key), `EXPECTED_KEYWORDS has a stale trait "${key}" not present in brand_dna.py anymore`);
  }
});

console.log(`\n${passed} passed`);
