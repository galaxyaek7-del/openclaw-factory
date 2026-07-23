// Tests for trust/ (Global Commercial Readiness Mission, 2026-07-23,
// Customer Trust System). Boots the real server.js, same pattern as
// tests/test_api_contract.js — these pages are served by the
// already-existing static-file middleware (no new routes were added),
// so this proves that real integration, not just that the files exist
// on disk.
//
//   node --test tests/test_trust_center.js

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const PORT = 3299;
const BASE_URL = `http://localhost:${PORT}`;
const REPO_ROOT = path.join(__dirname, '..');
const TRUST_DIR = path.join(REPO_ROOT, 'trust');

const PAGES = [
  'index.html', 'security-policy.html', 'responsible-ai-policy.html',
  'incident-disclosure-policy.html', 'privacy-policy.html',
  'terms-of-service.html', 'refund-policy.html',
];
const DRAFT_PAGES = ['privacy-policy.html', 'terms-of-service.html', 'refund-policy.html'];

let serverProcess;

async function waitForServer(timeoutMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(`${BASE_URL}/trust/index.html`);
      if (res.status) return;
    } catch { /* not up yet */ }
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error('server did not become ready in time');
}

test.before(async () => {
  serverProcess = spawn(process.execPath, ['server.js'], {
    cwd: REPO_ROOT,
    env: { ...process.env, PORT: String(PORT), MISSION_CONTROL_PASSWORD: 'trust-center-test-password' },
  });
  await waitForServer();
});

test.after(() => {
  if (serverProcess) serverProcess.kill();
});

test('every real trust page exists on disk', () => {
  for (const page of PAGES) {
    assert.ok(fs.existsSync(path.join(TRUST_DIR, page)), `${page} must exist`);
  }
});

test('every trust page is reachable, unauthenticated, via the existing static file middleware', async () => {
  for (const page of PAGES) {
    const res = await fetch(`${BASE_URL}/trust/${page}`);
    assert.equal(res.status, 200, `${page} should be publicly reachable with no auth`);
    const body = await res.text();
    assert.match(body, /<title>/, `${page} should be a real HTML page, not an error page`);
  }
});

test('every internal /trust/*.html link on every page points at a real, existing page', () => {
  const linkPattern = /href="\/trust\/([a-z0-9.-]+\.html)"/g;
  for (const page of PAGES) {
    const content = fs.readFileSync(path.join(TRUST_DIR, page), 'utf8');
    let m;
    while ((m = linkPattern.exec(content))) {
      assert.ok(PAGES.includes(m[1]), `${page} links to /trust/${m[1]}, which is not one of the real pages`);
    }
  }
});

test('draft (legal) pages are clearly labeled as drafts pending lawyer review', () => {
  for (const page of DRAFT_PAGES) {
    const content = fs.readFileSync(path.join(TRUST_DIR, page), 'utf8');
    assert.match(content, /has not been reviewed by a lawyer/i, `${page} must carry the draft/lawyer-review warning`);
  }
});

test('non-draft policy pages (Security, Responsible AI, Incident Disclosure) do NOT carry the draft warning', () => {
  const nonDraft = ['security-policy.html', 'responsible-ai-policy.html', 'incident-disclosure-policy.html'];
  for (const page of nonDraft) {
    const content = fs.readFileSync(path.join(TRUST_DIR, page), 'utf8');
    assert.doesNotMatch(content, /has not been reviewed by a lawyer/i, `${page} is an honest engineering disclosure, not a legal draft — it should not carry the legal-draft warning`);
  }
});

test('the Trust Center hub links to every one of the 6 real policy pages', () => {
  const hub = fs.readFileSync(path.join(TRUST_DIR, 'index.html'), 'utf8');
  for (const page of PAGES) {
    if (page === 'index.html') continue;
    assert.match(hub, new RegExp(`href="/trust/${page.replace('.', '\\.')}"`), `hub must link to ${page}`);
  }
});
