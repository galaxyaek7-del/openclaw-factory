#!/usr/bin/env node
/**
 * Run a group of JS test files and report failures as GitHub Actions
 * annotations.
 *
 * Why (2026-10-04): the Python side got this via scripts/run_python_group.py,
 * and without it a red CI build only ever said "JavaScript tests failed" --
 * the job log needs auth to read. This is the same capability for Node.
 *
 * Usage:
 *   node scripts/run_js_group.js tests/test_a.js tests/test_b.js
 *
 * Test selection and exit-code semantics are identical to running
 * `node --test <files>` directly; the only addition is annotation output.
 */
'use strict';

const { spawnSync } = require('child_process');

const files = process.argv.slice(2);
if (files.length === 0) {
  console.error('usage: node scripts/run_js_group.js <test files...>');
  process.exit(2);
}

// TAP keeps the output stable and parseable across Node versions.
// Everything is guarded: if the spawn itself fails (bad flag, E2BIG, missing
// binary) the wrapper must still emit an annotation, otherwise the step dies
// in silence with nothing but "Process completed with exit code 1".
//
// --test-concurrency=1 is load-bearing, not cosmetic. The runner otherwise
// fans every file out in parallel, and the 61-file step was killed by the
// CI runner after 9 seconds with no output at all -- a SIGKILL, not a test
// failure (a crashing wrapper annotates, and it did not). Suites here boot
// real servers and real Python subprocesses, so peak memory scales with
// fan-out. One file at a time is slower and actually completes.
const args = ['--test', '--test-concurrency=1', '--test-reporter=tap', ...files];

let res;
try {
  res = spawnSync(process.execPath, args, {
    encoding: 'utf8',
    maxBuffer: 64 * 1024 * 1024,
  });
} catch (err) {
  console.log(`::error::could not start node --test: ${err && err.message}`);
  if (err && err.code) console.log(`::error::code=${err.code}`);
  process.exit(1);
}

if (res.error) {
  console.log(`::error::node --test failed to run: ${res.error.message}`);
  if (res.error.code) console.log(`::error::code=${res.error.code}`);
  process.exit(1);
}

const out = (res.stdout || '') + (res.stderr || '');
process.stdout.write(out);

// Workflow commands are only parsed at the START of a line. TAP output does not
// guarantee a trailing newline, so without this the ::group:: below gets
// concatenated onto the last TAP line and GitHub silently drops every
// annotation -- which is exactly what happened: a real failure producing no
// annotations at all.
if (out.length && !out.endsWith('\n')) process.stdout.write('\n');

if (res.status === 0) {
  process.exit(0);
}

// On any failure, annotate with whatever detail exists. A TAP parse alone is
// not enough: if the run is killed mid-way (a test calling process.exit, a
// spawn failure, an unhandled rejection) there are no `not ok` lines at all,
// and the step would otherwise fail with no explanation whatsoever.
const lines = out.split('\n');
const failures = lines.filter((l) => /^not ok \d+ - /.test(l));
console.log(`::group::failure details (${failures.length} parsed, exit ${res.status})`);
for (const line of failures.slice(0, 40)) {
  const name = line.replace(/^not ok \d+ - /, '').trim();
  console.log(`::error::${name.replace(/\s+/g, ' ').slice(0, 600)}`);
}
if (failures.length === 0) {
  console.log(`::error::run exited ${res.status} with no parsable test failure`);
  console.log(`::error::signal=${res.signal || 'none'}`);
  const tail = lines.map((l) => l.trim()).filter((l) => l && !l.startsWith('#')).slice(-12);
  for (const line of tail) {
    console.log(`::error::output: ${line.replace(/\s+/g, ' ').slice(0, 500)}`);
  }
} else if (failures.length > 40) {
  console.log(`::error::...and ${failures.length - 40} more`);
}
console.log('::endgroup::');

process.exit(res.status === null ? 1 : res.status);