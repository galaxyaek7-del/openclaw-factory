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

// Security Mission Tracker finding 2.9 (2026-07-23), real fix: the
// previous implementation only escaped single quotes for the inner
// PowerShell single-quoted string, then concatenated the whole script
// into an outer double-quoted `-Command "..."` shell argument -- a real
// double quote in title/message could terminate that outer argument
// early and let the remainder be parsed as additional commands. Fixed
// via a real temp .ps1 script (never containing title/message) invoked
// with `-File <path> title message` -- PowerShell's own documented
// contract for -File is that everything after the script path is a
// literal script parameter, never re-parsed as PowerShell/shell syntax
// (an `-EncodedCommand`-based attempt was tried first while building
// this fix and real testing found PowerShell.exe itself still
// misinterprets trailing arguments around embedded quotes there -- see
// ADR-099 for the full account). This test proves the shipped fix on
// the real machine, the same way the tests above already do -- not
// mocked, because a Windows toast can't be meaningfully mocked -- with
// a real, executable check: if the injection succeeded, a real marker
// file would exist on disk afterward.
test('sendDesktopNotification: a real double-quote/shell-metacharacter injection attempt never executes', () => {
  const os = require('os');
  const path = require('path');
  const fs = require('fs');
  const marker = path.join(os.tmpdir(), `openclaw_2_9_injection_marker_${Date.now()}_${Math.random().toString(36).slice(2)}.txt`);

  try {
    const maliciousTitle = `x" ; Add-Content -Path "${marker}" -Value "INJECTED" ; "`;
    const maliciousMessage = `y\`; Add-Content -Path '${marker}' -Value 'INJECTED'; "$(Add-Content -Path "${marker}" -Value x)"`;

    const result = sendDesktopNotification(maliciousTitle, maliciousMessage);

    assert.equal(result, true, 'a real notification with dangerous-looking but literal text must still succeed');
    assert.equal(fs.existsSync(marker), false, 'no injected command must ever have actually executed');
  } finally {
    if (fs.existsSync(marker)) fs.rmSync(marker, { force: true });
  }
});

test('sendDesktopNotification: a literal double-quote character alone is treated as inert text, not a shell boundary', () => {
  const result = sendDesktopNotification('Title with a " double quote', 'Message with a " double quote too');
  assert.equal(result, true);
});

test('sendDesktopNotification: the real temp .ps1 script is cleaned up, never left behind', () => {
  const os = require('os');
  const fs = require('fs');
  const before = new Set(fs.readdirSync(os.tmpdir()).filter(f => f.startsWith('openclaw_notify_')));
  sendDesktopNotification('Cleanup check', 'x');
  const after = fs.readdirSync(os.tmpdir()).filter(f => f.startsWith('openclaw_notify_') && !before.has(f));
  assert.deepEqual(after, [], 'the real temp script must be deleted after use, not orphaned');
});
