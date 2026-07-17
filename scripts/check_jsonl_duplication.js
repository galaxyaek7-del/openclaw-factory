// Engineering Evolution Mode — Level 2 permanent safeguard.
//
// Level 1 (the actual bug) was: 17+ independent reimplementations of the
// same JSONL-read-with-corrupt-line-skip idiom scattered across the repo.
// Level 2 (why it was possible): the canonical version
// (lib/dashboard_data.js's readJsonlTail) existed for a while before this
// was even noticed, because it lived inside a file named for a different
// purpose — nothing signalled "reusable" to whoever wrote the next one,
// and nothing would have caught the count quietly growing to 18, 19, 20.
//
// This script is the fix for THAT: it counts the raw
// `.split('\n').filter(Boolean)` line-parsing idiom per file (a strong,
// simple signature for this exact pattern) and fails if any file's count
// EXCEEDS what's recorded in config/jsonl_duplication_baseline.json — the
// known, already-accepted occurrences as of when lib/jsonl.js was
// created. A brand-new copy introduced anywhere fails CI immediately,
// with a message pointing at lib/jsonl.js's readJsonlEntries() instead of
// silently becoming the 22nd copy someone has to notice in a future audit.
//
// This is deliberately a blunt, simple, low-maintenance check (a
// substring count, not an AST-aware analysis) — proportionate to the
// actual risk (a slow, silent accumulation over months), not an attempt
// to perfectly classify every match's semantics. One accepted false
// positive is already documented in the baseline file itself
// (scripts/generate_release_notes.js splits git output, not a JSONL
// log) — the check's job is to catch growth, not to be semantically
// perfect.
//
//   node scripts/check_jsonl_duplication.js       (used by CI; exits 1 on a real regression)

const fs = require('fs');
const path = require('path');

const REPO_ROOT = path.join(__dirname, '..');
const PATTERN = /\.split\('\\n'\)\.filter\(Boolean\)/;
const EXCLUDE_DIRS = new Set(['node_modules', '.git', 'tests']);
// Neither of these is a real occurrence of the duplicated idiom: jsonl.js
// is the one canonical implementation, and this checker's own source
// contains the pattern string literally (inside its own regex/comments).
const SELF_EXCLUDED_FILES = new Set(['lib/jsonl.js', 'scripts/check_jsonl_duplication.js']);

function listJsFiles(dir, out = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (EXCLUDE_DIRS.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      listJsFiles(full, out);
    } else if (entry.isFile() && entry.name.endsWith('.js')) {
      out.push(full);
    }
  }
  return out;
}

function countMatches(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const matches = content.match(new RegExp(PATTERN, 'g'));
  return matches ? matches.length : 0;
}

function run() {
  const baselinePath = path.join(REPO_ROOT, 'config', 'jsonl_duplication_baseline.json');
  const baseline = JSON.parse(fs.readFileSync(baselinePath, 'utf8'));

  const files = listJsFiles(REPO_ROOT);
  const violations = [];
  const current = {};

  for (const absPath of files) {
    const relPath = path.relative(REPO_ROOT, absPath).split(path.sep).join('/');
    if (SELF_EXCLUDED_FILES.has(relPath)) continue;
    const count = countMatches(absPath);
    if (count === 0) continue;
    current[relPath] = count;
    const allowed = baseline[relPath] || 0;
    if (count > allowed) {
      violations.push({ file: relPath, count, allowed });
    }
  }

  if (violations.length) {
    console.error('❌ New JSONL-read duplication found (Engineering Evolution Mode safeguard):\n');
    for (const v of violations) {
      console.error(`  ${v.file}: ${v.count} occurrence(s), baseline allows ${v.allowed}`);
    }
    console.error('\nUse lib/jsonl.js\'s readJsonlEntries() instead of a new manual .split(\'\\n\').filter(Boolean) loop.');
    console.error('If this is a deliberate, different, non-JSONL use, update config/jsonl_duplication_baseline.json with a comment explaining why.');
    process.exitCode = 1;
    return;
  }

  console.log('✔ No new JSONL-read duplication beyond the recorded baseline.');
  for (const [file, count] of Object.entries(current)) {
    const allowed = baseline[file] || 0;
    if (count < allowed) {
      console.log(`  note: ${file} now has ${count} (baseline ${allowed}) — some were migrated to lib/jsonl.js; consider lowering the baseline.`);
    }
  }
}

run();

module.exports = { countMatches, listJsFiles };
