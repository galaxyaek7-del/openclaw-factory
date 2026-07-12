// Tests for factory_loop.js's pending-review notification (ADR-025 batch,
// HIGH_VALUE_EXECUTION_PLAN.md). Uses Node's built-in test runner
// (node:test) — no new dependency. Every test uses a temp directory/file,
// never the real pending_review/queue/ or NEEDS_REVIEW.md.
//
//   node --test tests/test_pending_review.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const fl = require('../factory_loop.js');

function makeTempQueueDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'pending_review_queue_'));
}

test('countPendingReviewDrafts returns 0 for a missing directory', () => {
  const missing = path.join(os.tmpdir(), 'does-not-exist-xyz-123');
  assert.equal(fl.countPendingReviewDrafts(missing), 0);
});

test('countPendingReviewDrafts counts only .json files', () => {
  const dir = makeTempQueueDir();
  fs.writeFileSync(path.join(dir, 'a.json'), '{}');
  fs.writeFileSync(path.join(dir, 'b.json'), '{}');
  fs.writeFileSync(path.join(dir, 'notes.txt'), 'ignore me');
  assert.equal(fl.countPendingReviewDrafts(dir), 2);
});

test('writeNeedsReview creates a file mentioning the count', () => {
  const tmp = path.join(os.tmpdir(), `NEEDS_REVIEW_test_${Date.now()}.md`);
  fl.writeNeedsReview(3, tmp);
  const content = fs.readFileSync(tmp, 'utf8');
  assert.match(content, /3 مسودة/);
  fs.unlinkSync(tmp);
});

test('clearNeedsReview removes the file if present, never throws if absent', () => {
  const tmp = path.join(os.tmpdir(), `NEEDS_REVIEW_test_${Date.now()}.md`);
  fl.writeNeedsReview(1, tmp);
  assert.ok(fs.existsSync(tmp));
  fl.clearNeedsReview(tmp);
  assert.ok(!fs.existsSync(tmp));
  assert.doesNotThrow(() => fl.clearNeedsReview(tmp));
});

test('checkPendingReview writes the notify file when the queue is non-empty', () => {
  const dir = makeTempQueueDir();
  fs.writeFileSync(path.join(dir, 'draft.json'), '{}');
  const notifyPath = path.join(os.tmpdir(), `NEEDS_REVIEW_test_${Date.now()}.md`);
  const result = fl.checkPendingReview(dir, notifyPath);
  assert.equal(result.action, 'needs_review');
  assert.match(result.detail, /1 مسودة/);
  assert.ok(fs.existsSync(notifyPath));
  fs.unlinkSync(notifyPath);
});

test('checkPendingReview reports none and clears the notify file for an empty queue', () => {
  const dir = makeTempQueueDir();
  const notifyPath = path.join(os.tmpdir(), `NEEDS_REVIEW_test_${Date.now()}.md`);
  fl.writeNeedsReview(1, notifyPath); // simulate a stale notification from a prior tick
  const result = fl.checkPendingReview(dir, notifyPath);
  assert.equal(result.action, 'none');
  assert.ok(!fs.existsSync(notifyPath));
});
