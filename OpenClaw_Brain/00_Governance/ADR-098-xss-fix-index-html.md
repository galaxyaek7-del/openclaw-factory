# ADR-098 — XSS Fix: index.html's updateBooksList()

**Date:** 2026-07-23
**Status:** Adopted. Closes Security Mission Tracker finding 2.7 (High), the Security Architecture sub-phase's own explicitly-named next step after the route-authentication fixes (2.1/2.6/2.13).

---

## The finding

Real, confirmed XSS (Phase 1 Security Audit, ADR-094's report): `index.html`'s `updateBooksList()` interpolated `${b.title}`, and (found again during this fix, expanding the audit's own scope by one field) `${b.type}`/`${b.theme}`/`${b.pages}`/`${b.time}`, directly into `el.innerHTML` with zero escaping. Reachable via two real paths: the manual `#bookTitle` form field (self-contained, lower real risk) and, more seriously, Scout's `d.brief.title`/`d.brief.topic` — real text sourced from Hacker News via `POST /api/scout/run`'s market-brief pipeline, which is attacker-postable by anyone who can submit a Show HN post matching the scout's search terms.

## What a real search found

`dashboard.html` and `mission_control.html` already carry an identical, already-shipped `escapeHtml()` helper (standard `&`/`<`/`>`/`"`/`'` entity escaping, `&` replaced first to avoid double-escaping). `index.html` — a separate, single-file vanilla-JS page with no shared JS module system between the three (per this factory's own stack description) — never had one. Reused the exact same implementation verbatim rather than inventing a new one, consistent with this codebase's existing precedent for this specific class of duplication (a tiny, self-contained utility copied across independent static HTML files, not extracted into a shared module, since none exists).

## What was built

- `index.html`: added `escapeHtml()` (byte-for-byte the same implementation already in `dashboard.html`/`mission_control.html`). `updateBooksList()`'s template now wraps every interpolated field — `b.title`, `b.type`, `b.theme`, `b.pages`, `b.time` — in `escapeHtml(...)`. `type`/`theme` for manually-generated books come from fixed `<select>` values (low real risk today), but `theme` for Scout-sourced books is `d.brief.topic` — also externally influenced — so all five fields were escaped defensively rather than selectively, the same "escape by default" posture the two sibling files already established.
- `clearLog()`'s pre-existing `innerHTML = ''` assignment (always a literal empty string, never interpolated) was confirmed real and left untouched — not every `innerHTML` use in the file was a real vulnerability, and the fix is scoped to the one genuinely unescaped, externally-influenced template.
- File encoding preserved: `index.html` is UTF-16 LE with BOM (CLAUDE.md's own documented note). The edit was made via a UTF-16-aware read/write (not the general-purpose file-edit tooling, which does not decode this file correctly) and the BOM was verified byte-for-byte intact afterward.

## Verification

8 new tests (`tests/test_index_html_xss_fix.js`) — reads the real, shipped `index.html` (UTF-16 LE-aware), confirms every interpolated field in the real template is wrapped in `escapeHtml(...)` and none remain raw, and — the strongest evidence — extracts the **actual shipped `escapeHtml()` function source** and executes it directly (not a reimplementation) against a real `<script>alert(1)</script>` payload, a real `<img src=x onerror=...>` payload, and a real quote-breakout attempt, confirming each is neutralized to inert escaped text. Also confirms ordinary real titles render unchanged (no double-escaping regression) and that `clearLog()`'s unrelated `innerHTML` use is untouched.

**Live-browser DOM confirmation was attempted and could not be completed** — the Claude-in-Chrome browser extension was not connected in this environment (3 attempts, consistent "extension not connected" failure). The executable test above (running the actual shipped function in a real JS engine, not a browser DOM) is real, non-visual proof of the escaping behavior; it does not by itself prove browser-DOM rendering semantics, though standard `innerHTML`/HTML-entity behavior is not implementation-specific in a way that would change this result. Recommend a manual live check (`node server.js`, open `index.html`, run the same injection via devtools console) before or shortly after this ships, to close that last gap honestly rather than silently.

Full regression check: `tests/test_index_html_xss_fix.js` (8/8), `tests/test_trust_center.js` + `tests/test_check_jsonl_duplication.js` (10/10, unaffected), `tests/test_api_contract.js` (23/23, server.js itself untouched by this change), full Python suite (1141/1141, unaffected — this is a pure front-end fix).

## What's next

Per the Security Architecture Mission Tracker's own stated order: 2.9 (`factory_loop.js`'s `sendDesktopNotification()` shell-escaping boundary) is next, then 2.8/2.3/2.11/2.12.
