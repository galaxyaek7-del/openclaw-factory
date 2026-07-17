// OpenClaw Factory — shared JSONL-reading primitive.
//
// Engineering Evolution Mode follow-up (Level 2 system analysis): this
// exact 5-line "read file, split on newline, parse each line, skip a
// corrupt one silently" pattern was independently reimplemented in at
// least 8 places across the repo (factory_loop.js, self_awareness.js,
// lib/recovery_log.js, and lib/dashboard_data.js's own internal
// readJsonlTail()) before this module existed. The root cause wasn't
// missing code — lib/dashboard_data.js already had a correct version —
// it was missing DISCOVERABILITY: that version lived inside a file named
// for a different purpose, so nothing signalled "reusable" to whoever
// wrote the next JSONL-reading function. This is the canonical, findable
// home for it now. scripts/check_jsonl_duplication.js is the permanent
// safeguard that stops the count from silently growing again — see that
// script's own header for how it works and how to update its baseline
// when a genuinely different behavior (not just another copy of this
// one) is needed.
//
// Two real, different behaviors are deliberately NOT handled here and
// should not be forced into this function via a mode flag: (1) a few
// server.js routes keep a corrupt line as `{ raw: line }` instead of
// discarding it, so a caller can see something was there and malformed;
// (2) scripts/ops_daily_checks.js counts corruption without consuming
// the parsed data at all (an integrity check, not a data read). Forcing
// either into this function's API would turn "one shared primitive"
// into a small configuration DSL — the actual complexity would move,
// not disappear. Both stay their own small, explicit, commented code.

const fs = require('fs');

// Reads a JSONL file, silently skipping any line that fails to parse —
// a corrupt/partial line (e.g. from a crash mid-write) must never make
// the whole read throw. Returns [] if the file doesn't exist or can't be
// read at all. `limit` (default: read everything) tails the LAST N raw
// lines before parsing, not after — cheap even against a large file when
// only recent entries are needed; pass Infinity for the full history.
function readJsonlEntries(filePath, limit = Infinity) {
  if (!fs.existsSync(filePath)) return [];
  try {
    const lines = fs.readFileSync(filePath, 'utf8').split('\n').filter(Boolean);
    return lines.slice(-limit).map(line => {
      try { return JSON.parse(line); } catch (_) { return null; }
    }).filter(Boolean);
  } catch (_) {
    return [];
  }
}

module.exports = { readJsonlEntries };
