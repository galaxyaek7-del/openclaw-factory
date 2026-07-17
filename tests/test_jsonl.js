// Tests for lib/jsonl.js — the shared JSONL-reading primitive extracted
// from 8+ independently-duplicated copies across the repo (Engineering
// Evolution Mode follow-up). Uses temp files, never real data.
//
//   node --test tests/test_jsonl.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const { readJsonlEntries } = require('../lib/jsonl.js');

function tempPath() {
  return path.join(os.tmpdir(), `test_jsonl_${process.pid}_${Date.now()}_${Math.random().toString(36).slice(2)}.jsonl`);
}

test('readJsonlEntries: missing file -> empty array, never throws', () => {
  const result = readJsonlEntries(tempPath());
  assert.deepEqual(result, []);
});

test('readJsonlEntries: reads every valid entry in order, no limit given', () => {
  const p = tempPath();
  fs.writeFileSync(p, '{"a":1}\n{"a":2}\n{"a":3}\n');
  try {
    const result = readJsonlEntries(p);
    assert.deepEqual(result.map(r => r.a), [1, 2, 3]);
  } finally {
    fs.rmSync(p, { force: true });
  }
});

test('readJsonlEntries: a corrupt line is skipped silently, never throws', () => {
  const p = tempPath();
  fs.writeFileSync(p, '{"a":1}\nNOT VALID JSON\n{"a":3}\n');
  try {
    const result = readJsonlEntries(p);
    assert.deepEqual(result.map(r => r.a), [1, 3]);
  } finally {
    fs.rmSync(p, { force: true });
  }
});

test('readJsonlEntries: limit tails the last N raw lines before parsing', () => {
  const p = tempPath();
  fs.writeFileSync(p, '{"a":1}\n{"a":2}\n{"a":3}\n{"a":4}\n');
  try {
    const result = readJsonlEntries(p, 2);
    assert.deepEqual(result.map(r => r.a), [3, 4]);
  } finally {
    fs.rmSync(p, { force: true });
  }
});

test('readJsonlEntries: empty file -> empty array', () => {
  const p = tempPath();
  fs.writeFileSync(p, '');
  try {
    assert.deepEqual(readJsonlEntries(p), []);
  } finally {
    fs.rmSync(p, { force: true });
  }
});

test('readJsonlEntries: a directory path (unreadable as a file) -> empty array, never throws', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'test_jsonl_dir_'));
  try {
    assert.deepEqual(readJsonlEntries(dir), []);
  } finally {
    fs.rmdirSync(dir);
  }
});
