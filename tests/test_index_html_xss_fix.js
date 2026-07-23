// Tests for the real, confirmed XSS fix in index.html (Enterprise
// Upgrade Roadmap finding 2.7, Security Mission Tracker, 2026-07-23):
// updateBooksList() interpolated real, externally-influenced fields
// (Scout/Pioneer's Hacker-News-sourced niche titles, and the manual
// book-title form field) directly into innerHTML with zero escaping.
//
// index.html is UTF-16 LE with BOM (see CLAUDE.md's own note) —
// read with the 'utf16le' encoding, matching that documented
// convention, never assumed UTF-8.
//
//   node --test tests/test_index_html_xss_fix.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

const INDEX_HTML_PATH = path.join(__dirname, '..', 'index.html');

function readIndexHtml() {
  return fs.readFileSync(INDEX_HTML_PATH, 'utf16le');
}

// Extracts the real escapeHtml() function source and evaluates it in
// isolation — proves the ACTUAL shipped implementation escapes
// correctly, not just that some string matching a pattern exists.
function loadRealEscapeHtml(content) {
  const match = content.match(/function escapeHtml\(s\) \{[\s\S]*?\n {8}\}/);
  assert.ok(match, 'escapeHtml() function must exist in index.html');
  // eslint-disable-next-line no-new-func
  return new Function(`${match[0]}; return escapeHtml;`)();
}

test('escapeHtml() exists in index.html', () => {
  const content = readIndexHtml();
  assert.match(content, /function escapeHtml\(s\)/);
});

test('every interpolated field in the real updateBooksList template is escaped', () => {
  const content = readIndexHtml();
  const templateMatch = content.match(/el\.innerHTML = books\.slice\(0, 5\)\.map\(b =>[\s\S]*?\)\.join\(''\);/);
  assert.ok(templateMatch, 'the real updateBooksList template must still exist');
  const template = templateMatch[0];
  for (const field of ['title', 'type', 'theme', 'pages', 'time']) {
    assert.match(
      template, new RegExp(`escapeHtml\\(b\\.${field}\\)`),
      `b.${field} must be passed through escapeHtml() in the real template`,
    );
    assert.doesNotMatch(
      template, new RegExp(`\\$\\{b\\.${field}\\}(?!\\))`),
      `b.${field} must never be interpolated raw (unescaped) into innerHTML`,
    );
  }
});

test('the real, shipped escapeHtml() actually neutralizes a script tag', () => {
  const escapeHtml = loadRealEscapeHtml(readIndexHtml());
  const malicious = '<script>alert(1)</script>';
  const escaped = escapeHtml(malicious);
  assert.doesNotMatch(escaped, /<script>/);
  assert.match(escaped, /&lt;script&gt;/);
});

test('the real, shipped escapeHtml() neutralizes an onerror-image attribute-injection attempt', () => {
  const escapeHtml = loadRealEscapeHtml(readIndexHtml());
  const malicious = '<img src=x onerror=alert(document.cookie)>';
  const escaped = escapeHtml(malicious);
  assert.doesNotMatch(escaped, /<img/);
  assert.match(escaped, /&lt;img/);
});

test('the real, shipped escapeHtml() neutralizes a real quote-breakout attempt on a title-like attribute', () => {
  const escapeHtml = loadRealEscapeHtml(readIndexHtml());
  const malicious = '"><script>alert(1)</script>';
  const escaped = escapeHtml(malicious);
  assert.doesNotMatch(escaped, /"/);
  assert.doesNotMatch(escaped, /</);
});

test('the real, shipped escapeHtml() never throws on null/undefined, matching this codebase\'s existing dashboard.html/mission_control.html implementations', () => {
  const escapeHtml = loadRealEscapeHtml(readIndexHtml());
  assert.equal(escapeHtml(null), '');
  assert.equal(escapeHtml(undefined), '');
});

test('the real, shipped escapeHtml() leaves ordinary real book titles readable', () => {
  const escapeHtml = loadRealEscapeHtml(readIndexHtml());
  assert.equal(escapeHtml('AI Compliance Automation for Accounting Firms'), 'AI Compliance Automation for Accounting Firms');
});

test('clearLog() (an existing, always-empty-string innerHTML assignment) is untouched — not every innerHTML use was a real vulnerability', () => {
  const content = readIndexHtml();
  assert.match(content, /function clearLog\(\) \{ document\.getElementById\('logBox'\)\.innerHTML = ''; \}/);
});
