# Incident: drive C: near-full (2026-10-22)

## What was observed

`factory_loop.log` health diagnoses on 2026-10-22 report the `disk` check as
`critical` on most ticks. Free space swung between about 12 GB and
**1.0 GB (0.4%)** on a 255 GB volume. The same log shows `network` critical
on 21 ticks (groq/telegram/github unreachable) and one `memory` degraded
reading. No alert reached the founder, because Telegram delivery is
unconfigured (`OPENCLAW_TELEGRAM_CHAT_ID` is unset; see
`n8n_workflows/env_to_credentials_2026-10-22/README.md`).

A near-full disk can make atomic JSON writes fail and corrupt the factory's
state files. It may also have contributed to today's background-process
memory kill. That second link is INFERRED, not proven.

## Root cause (measured read-only)

| Location | Size |
|---|---|
| `~/.local/share/opencode/opencode.db` (OpenCode's session DB) | **111.4 GB** |
| `%LOCALAPPDATA%\npm-cache\_cacache` | 10.0 GB (cleared, see below) |
| `%APPDATA%\npm` (global packages) | 3.3 GB |
| `%LOCALAPPDATA%\Temp` | 2.6 GB |
| the repository itself | 0.9 GB |

Inside `opencode.db` (SQLite, opened `mode=ro`):
- page count 29,214,562 × 4 KB = 119.7 GB, with **0 free pages**. It is real
  data, so `VACUUM` alone reclaims nothing.
- `event` table: 704,296 rows. 478,585 of them are `message.part.updated.1`.
  An even sample averages about 95 KB per row, with some rows over 20 MB, for
  an estimated **~69 GB**.
- `message` table: 47,813 rows, about 155 KB average, estimated ~7.6 GB.
- 302 sessions in total.

OpenCode stores a full payload for every streamed update of every message and
never compacts it.

## Actions taken

- **npm download cache cleared** (founder-approved): `npm cache clean
  --force`. Free space went from 8.3 GB to 18.4 GB. `_npx` (0.4 GB, used by the
  running MCP servers) was not touched.
- `opencode.db` was **not touched**. It is the parallel agent's history,
  outside the project, and open by a running process. The founder chose to
  handle it.

## Founder instructions for opencode.db

1. Finish or pause the OpenCode session, then close OpenCode completely.
   Check Task Manager: no `opencode.exe` should be running.
2. **Keep the history.** Move `opencode.db`, `opencode.db-wal` and
   `opencode.db-shm` from `C:\Users\Dell\.local\share\opencode\` to an
   external drive. OpenCode starts with an empty history next time; settings
   and login (`auth.json`) are separate files and stay.
3. **Or discard the history:** delete those three files instead. This frees
   about 112 GB and cannot be undone.
4. Start OpenCode again and confirm it works.

Whether OpenCode has a built-in retention or cleanup setting was not checked.
It is UNKNOWN, not assumed.

## Still open

- The factory's own disk check works and fires, but nothing delivers it.
  That is fixed only once the Telegram chat id is configured.
