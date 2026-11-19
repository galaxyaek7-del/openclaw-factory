# GF MCP — Read-Only Factory Interface

Status: **IMPLEMENTED (2026-11-18)** — 12 tools, unit-tested, verified over a real
stdio session. No write tool exists and none is planned here.

## Decision: extend, do not duplicate

`mcp_pilot/gf_readonly_server.py` already existed, was already registered in
`opencode.json` and `mcp_pilot/mcp.json`, already enforced a no-write boundary,
and already had tests pinning that boundary. The five requested tools overlapped
with none of its seven, so they were added in place. A second Node server would
have duplicated the transport, the sanitizer and the registration, and would have
created two places to audit.

The founder's Step 2 asked for Node.js with the official MCP SDK. That was not
followed, deliberately, and this is the reason: the repository rule "search for
an existing module that does the same job and extend it" outranks the language
preference here, and the Python server already speaks the same JSON-RPC 2.0 over
stdio that the SDK produces. Nothing about the five tools needs the SDK. If the
founder wants a Node server regardless, it is a rewrite of an audited, working
boundary for no capability gain — recorded as an open option, not a defect.

## Transport and registration

- STDIO, newline-delimited JSON-RPC 2.0. No network listener.
- Launch: `python -E -P mcp_pilot/gf_readonly_server.py`
- Registered as `gf_readonly` (enabled) in `opencode.json`; also in
  `mcp_pilot/mcp.json`. `gf_local` remains disabled and untouched.
- Every call is appended to `logs/mcp_readonly_calls.jsonl` (`GF_MCP_CALL_LOG`).
  The log records name, size and duration — never arguments or results.

## Read-only boundary

- No write tool, no shell, no `eval`/`exec`, no caller-supplied path.
- `.env` is never opened. `tests/test_mcp_readonly_server.py` spies on
  `builtins.open` to prove it.
- All output passes `sanitize_text`; a value from `.env` never appears in any
  tool output (pinned by `tests/test_gf_mcp_tools.py`).
- No credentials, no tokens, no fingerprints. `write_gate_status` reports a
  status and an age, never a secret.

## Tools

### `factory_status` — no arguments
Sources: `supervisor.log` (tail), `data/factory_state.json`, a bounded 2 s
loopback `GET /health`.

Returns: `status` (`OK` when the state file is younger than 20 minutes and
recovery is not interrupted, else `DEGRADED`), `loop` (state age, current
task/step, last checkpoint stage, `interrupted`, pending retries),
`supervisor` (last event per target, crashes in 24 h, log size), `server_health`
(`OBSERVED` / `UNREACHABLE` / `NOT_MEASURED`).

Rules: the health probe only talks to a loopback host; no redirect is followed;
a timeout is reported as `UNREACHABLE`, never guessed. `GF_MCP_PROBE_HEALTH=0`
disables it (used by tests).

### `tasks_status` — no arguments
Sources: `TASKS.md`, `WORKLOG.md`.

Returns: checkbox counts (done/pending), sections, `blocked_items`, the items
themselves, and the last five worklog entries. A missing file yields
`status: UNKNOWN` with zero counts — not `OK`.

### `test_status` — no arguments
Source: `data/regression_status.json` (written by `scripts/factory_regression.py`).

Returns: the recorded result with its age and `PASS` / `FAILED` / `STALE` /
`UNKNOWN`. A record older than 36 hours is `STALE`, never `PASS`. This tool
**never runs a test** — that distinction is in its description, because an agent
must not be able to trigger a suite by reading status.

### `revenue_evidence` — no arguments
Sources: `data/verified_transactions.jsonl`, `data/product_registry.json`,
`finance_data.json`.

Returns: `verified` (state, rows, sum, unparseable line count), `registry`
(units, USD, age) and the finance file's own totals, kept separate on purpose.
Rows flagged `simulation` or `test` are excluded. An absent ledger returns
`state: NO_VERIFIED_TRANSACTION_RECORD` with `0`, so zero is always explained.
Page views, clicks, drafts and listed prices are never revenue.

### `recent_logs` — `{source, lines}`
Sources (whitelist, fixed paths): `factory_loop`, `supervisor`,
`server_crashes`, `server_errors`. `lines` is 1–200 (default 40).

Reads at most the last 256 KiB and drops a partial first line. Any line shaped
like an env assignment (`KEY=…`) is dropped entirely, not redacted; remaining
lines are truncated to 500 chars and passed through `sanitize_text`. A caller
path is refused by schema and by an explicit unexpected-argument check.

## Honest limits

- **NOT IMPLEMENTED:** any write, publish, approve, send, start or stop action.
- **NOT IMPLEMENTED:** a caller-chosen log path or a caller-chosen file.
- **NOT MEASURED:** marketing, traffic, conversion. No tool reports them.
- **UNKNOWN:** whether a Node implementation is wanted (see decision above).
- `recent_logs` cannot guarantee redaction of a secret echoed in an unusual
  shape; it guarantees dropping env-style lines and redacting known token
  shapes. Log producers should not print secrets.

## Verification

```
python -m pytest tests/test_gf_mcp_tools.py tests/test_mcp_readonly_server.py -q
# 41 passed, 1 skipped (junction test, Windows-only path already covered)
```

Live stdio session (2026-11-18): 12 tools listed; `factory_status: OK`,
`tasks_status: 20 items / 1 blocked`, `test_status: PASS` (448 Python, 9 Node),
`revenue_evidence: NO_VERIFIED_TRANSACTION_RECORD / 0`, `recent_logs` 3 clean
lines from a 905 KB log.
