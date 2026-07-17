// Regression test for the Prove-the-Company follow-up (Master Roadmap
// "Important" item M4): NEEDS_ATTENTION.md/NEEDS_REVIEW.md were written
// correctly but nothing pushed them to a human -- a real, verified gap
// between "the system detected a problem" and "a human found out".
// sendDesktopNotification() fires a real Windows toast (System.Windows.
// Forms.NotifyIcon) -- zero new dependencies, zero cloud service.
//
// This test runs the REAL function on the real machine (there is no safe
// way to mock a Windows toast notification meaningfully) -- it verifies
// the call succeeds and, critically, that single-quote escaping in the
// title/message doesn't break the PowerShell invocation (a real
// correctness concern for arbitrary reasons/messages, not just "does it
// throw"). A manual visual check (a real toast was observed) was also
// done once outside this automated suite -- this test proves the
// mechanism runs cleanly, not that a human necessarily saw it, which is
// disclosed here rather than silently assumed.
//
//   node --test tests/test_factory_loop_notification.js

const test = require('node:test');
const assert = require('node:assert/strict');
const { sendDesktopNotification } = require('../factory_loop.js');

test('sendDesktopNotification: a real, plain message succeeds', () => {
  const result = sendDesktopNotification('Test Title', 'Test message, no special characters.');
  assert.equal(result, true);
});

test('sendDesktopNotification: a message containing single quotes does not break the PowerShell call', () => {
  // A real, realistic case: attentionReasons/messages elsewhere in this
  // file are free-form Arabic/English text that could legitimately
  // contain an apostrophe or quoted phrase.
  const result = sendDesktopNotification("OpenClaw's Status", "It's flagged: 'opportunity_score_below_floor'");
  assert.equal(result, true);
});

test('sendDesktopNotification: never throws, even with empty strings', () => {
  assert.doesNotThrow(() => sendDesktopNotification('', ''));
});

test('sendDesktopNotification: never throws with a very long message', () => {
  const longMessage = 'x'.repeat(2000);
  assert.doesNotThrow(() => sendDesktopNotification('Title', longMessage));
});
