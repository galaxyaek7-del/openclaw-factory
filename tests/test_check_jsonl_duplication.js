// Regression test for scripts/check_jsonl_duplication.js — the
// Engineering Evolution Mode Level 2 safeguard against the JSONL-reading
// idiom silently reaccumulating across the repo. Runs the real script as
// a subprocess against real temp files, never touching the real repo.
//
//   node --test tests/test_check_jsonl_duplication.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const { countMatches } = require('../scripts/check_jsonl_duplication.js');

function tempJsFile(content) {
  const p = path.join(os.tmpdir(), `test_jsonl_dup_${process.pid}_${Date.now()}_${Math.random().toString(36).slice(2)}.js`);
  fs.writeFileSync(p, content);
  return p;
}

test('countMatches: counts real occurrences of the exact idiom', () => {
  const p = tempJsFile(`
    const a = x.split('\\n').filter(Boolean);
    const b = y.split('\\n').filter(Boolean);
  `);
  try {
    assert.equal(countMatches(p), 2);
  } finally {
    fs.rmSync(p, { force: true });
  }
});

test('countMatches: zero for a file with no occurrence', () => {
  const p = tempJsFile(`const a = 1 + 1;`);
  try {
    assert.equal(countMatches(p), 0);
  } finally {
    fs.rmSync(p, { force: true });
  }
});

test('real script: exits 0 against the real repo as it stands today (no un-recorded duplication)', () => {
  const repoRoot = path.join(__dirname, '..');
  // Must not throw — a non-zero exit from execFileSync throws.
  const out = execFileSync(process.execPath, [path.join(repoRoot, 'scripts', 'check_jsonl_duplication.js')], {
    cwd: repoRoot, encoding: 'utf8',
  });
  assert.match(out, /No new JSONL-read duplication/);
});

test('real script: exits non-zero when a genuinely new occurrence is introduced', () => {
  const repoRoot = path.join(__dirname, '..');
  const scratchPath = path.join(repoRoot, 'test_scratch_jsonl_dup_check.js');
  fs.writeFileSync(scratchPath, `
    const fs = require('fs');
    function readSomething(p) {
      return fs.readFileSync(p, 'utf8').split('\\n').filter(Boolean);
    }
  `);
  try {
    assert.throws(() => {
      execFileSync(process.execPath, [path.join(repoRoot, 'scripts', 'check_jsonl_duplication.js')], {
        cwd: repoRoot, encoding: 'utf8',
      });
    }, /Command failed/);
  } finally {
    fs.rmSync(scratchPath, { force: true });
  }
});
