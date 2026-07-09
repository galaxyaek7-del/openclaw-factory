# 🛡️ Niche Safety Filter v1

## Not to be confused with

**"Butter Compliance"** (`self_awareness.js`'s `getButterCompliance()`, `CONSTITUTION.md` §16) is an **UNRELATED** pricing metric — it measures what % of recently generated books cleared the $30 "Butter Principle" price floor. It has nothing to do with content safety.

This document is about **content safety only**: the filter that blocks scam/trademark/medical/adult/financial niches from ever reaching a spawned book, a dashboard, or a publish call. The two systems briefly shared the name "Butter Compliance" (Tasks 1–9); that collision was resolved in Task 10 by renaming this filter to **Niche Safety Filter**. If you're looking for the pricing metric, see `self_awareness.js` and `CONSTITUTION.md` §16 instead — this document doesn't cover it.

## Purpose

Blocks niches that would get the KDP/Etsy/Redbubble account banned or poison the brand: scam wording, trademark violations, unlicensed financial/medical advice, adult content. It runs *before* any book is generated, any niche is shown to a human, or any trend is recorded — never after.

## The Five Gate Points

| Route | server.js line (`runSafetyCheck()` call) | What it protects |
|---|---|---|
| `POST /generate-book` | 103 | Blocks PDF creation — the original gate (Task 2) |
| `POST /api/market-analyze` | 921 | Filters niche recommendations before they reach the user (Task 3) |
| `POST /api/scout/run` | 696 | Blocks Scout's own Groq-invented brief, pre-spawn — Scout ignores the caller's payload entirely and picks its own topic, so the gate runs on the finalized brief, not on `req.body` (Task 8) |
| `POST /api/trends` | 867 | Blocks poisoned n8n trends from ever reaching `OPPORTUNITIES.md`, a human-facing dashboard file (Task 8) |
| `POST /api/safety/check` | 87 | The filter's own standalone endpoint — lets any caller test a payload directly, and is what this document's own test examples use |

`runSafetyCheck()` itself is defined at `server.js:27`; `safety_filter.py` is spawned from `server.js:47`.

## Severity Model

From `safety_filter.py`'s `BLOCKLISTS` dict (lines 19–59):

| Category | Level | Severity | Blocks? |
|---|---|---|---|
| `brand_poison` | blocked | 100 | yes |
| `trademark` | blocked | 100 | yes |
| `adult` | blocked | 100 | yes |
| `financial` | high | 50 | yes |
| `medical` | high | 50 | yes |

> **Note:** if you've seen severity 70 quoted for `financial`/`medical` elsewhere, that's wrong — the actual shipped value in `safety_filter.py` is **50**. This table reflects the real code, verified directly against the file at the time of writing.

```
score = 100 - max_severity_found_across_all_matched_categories
allowed = risk_level NOT IN [blocked, high]
```
`risk_level` is the level of whichever matched category had the highest severity (ties resolve toward `blocked`). No matches → `risk_level: "low"`, `score: 100`, `allowed: true`.

## The Fail-Safe Rule (non-negotiable)

**Filter failure → REJECT. Never fail-open.**

Triggers that count as failure:
- Python spawn error
- 5-second timeout (`runSafetyCheck(payload, timeoutMs = 5000)`)
- JSON parse error on stdout
- Non-zero exit code
- A response missing a boolean `allowed` field (malformed result)

Response returned on any of these, verbatim (`server.js:28-33`):
```json
{
  "allowed": false,
  "score": 0,
  "risk_level": "blocked",
  "reasons": [{ "category": "filter_error", "level": "blocked", "reason": "safety filter unavailable — failing safe" }]
}
```

## Contract (do not break)

```
safety_filter.py stdin  → { niche, title, subtitle, description, type }
safety_filter.py stdout → { allowed, score, risk_level, reasons[] }
```
Exit code is **always 0** — the decision travels entirely in the JSON body, never in the process exit code. `server.js` still treats a non-zero exit as a failure (fail-safe), but `safety_filter.py` itself never intentionally exits non-zero.

**Windows note:** stdin/stdout are forced to UTF-8 explicitly (`sys.stdin.buffer.read().decode('utf-8')` / raw bytes on stdout) — Python defaults `sys.stdin`/`sys.stdout` to the platform codepage (`cp1252` on this machine), which silently corrupted the Arabic blocklist keywords being piped through before this fix. This was a real bug found and fixed during Task 1's initial build, not a theoretical concern — verify it hasn't regressed if this file is ever touched again.

## How to Gate a New Route (contributor guide)

1. Find the risky action in the route (a `spawn()` call, a file write, a platform publish step).
2. Immediately before it, call: `const r = await runSafetyCheck({ niche, title, subtitle, description, type })`.
3. If `!r.allowed` → return the standard blocked response shape. Copy it from `/generate-book` (`server.js:111-121`): `{ success: false, blocked: true, reason: 'safety_rejected', risk_level: r.risk_level, score: r.score, reasons: r.reasons, message: '...' }`.
4. If `r.allowed` → proceed unchanged, no other behavior change.
5. Wrap the `runSafetyCheck()` call in `try/catch` — a throw must be treated as blocked, same fail-safe object as above. Never let a thrown error fall through to "allowed."
6. Add two tests: one clean payload (expect `allowed:true`), one payload built from `safety_filter.py`'s own keyword list (expect `allowed:false`).

## Testing Trap (learned in Task 8)

`/api/scout/run` **ignores `req.body` entirely**. It always generates its own brief via Groq (`scoutBriefPrompt()`), falling back to a fixed, always-safe `fallbackScoutBrief()` if `GROQ_KEY` is missing or Groq fails. **Payload-based tests cannot force a block on this specific route** — posting a scam-worded `niche`/`title` has zero effect on what Scout actually attempts to generate.

Correct method to verify this route's gate:
- **Prove the filter itself works:** `POST /api/safety/check` with a synthetic poisoned payload (e.g. `{"niche":"forex trading scam","title":"Get Rich Quick"}`) and confirm `allowed:false`.
- **Prove the gate is actually wired into the route:** `findstr /n "runSafetyCheck" server.js` (or `grep -n`) and confirm the route's line number appears among the call sites.

This same trap does *not* apply to `/generate-book`, `/api/market-analyze`, or `/api/trends` — all three read their niche/title directly from the request, so payload-based tests work normally there.

## Known Limitations (v1)

- **Blocklists are hardcoded in `safety_filter.py`**, not a JSON/config file — changing a keyword requires a code edit and deploy, not a config update.
- **No audit log** — there is no persistent record of what was blocked, when, or why. A block happens, a response is returned, and nothing is written to disk about it.
- **No metrics** — block rate and top triggering categories are unknown; nobody can currently answer "how often does this actually fire, and on what?" without grepping server logs by hand.
- **AR/EN parity gap, deliberate for now:** e.g. `"استثمار"` (investment) is blocked but the English word `"investment"` is not — this is intentional, not an oversight: `"Investment Portfolio Tracker"` is a legitimate, existing product niche (see `market_analyzer.py`'s own trending-niches list), while `"أسرار الاستثمار"` ("investment secrets") reads as get-rich-quick advice. Blocking the bare English word would have false-positived a real product category; the Arabic phrase carries the advice-y framing more specifically in current usage. Revisit if this proves wrong in practice.
- **Keyword matching only — no semantic understanding.** A cleverly-phrased scam niche that avoids every listed keyword slips through entirely. This is a substring match over a normalized string, nothing more.
- **Subprocess-per-check will not scale to Redbubble volumes.** Every check spawns a fresh Python process (~tens of ms overhead each); fine at book-factory scale (a handful of checks per Scout run), not fine at art-marketplace scale (potentially thousands of listings).
- **Trademark list has ~15 entries** (`disney, marvel, pokemon, nintendo, harry potter, nike`); Redbubble alone actively enforces against thousands of registered trademarks. This list is a starting deterrent, not real trademark coverage.

## Git History

Chronological (`git log --oneline --grep="compliance" --grep="safety" --all -i`, oldest → newest):

| Hash | Message |
|---|---|
| `94c3607` | feat(compliance): add Butter Compliance filter + gate /generate-book and /api/market-analyze |
| `0348875` | fix(compliance): close /api/scout/run bypass — real book path was ungated |
| `4a5e036` | fix(compliance): close /api/scout/run AND /api/trends bypasses |
| `5ea8715` | refactor: rename content filter to Niche Safety Filter — resolves naming collision with Butter Compliance pricing metric |
