# Founder actions (updated 2026-10-29)

Everything below is prepared and tested. Each step needs you because it writes
to an external account, creates an account, or touches data only you may
decide on. Run the commands from `C:\openclaw-dasgboard` (in Claude Code,
prefix with `!`).

## 1. Publish the last three batch-16 products (approvals expire 2026-10-29 23:58 UTC)

```
python scripts/publish_batch14.py --batch batch16 --live --approvals data/publication_approvals.json --only B16-008 B16-009 B16-010
```

Gumroad's 24-hour limit has room for exactly these three (7 created today).
The command refuses on its own if the window, approval, revision or auth
freshness does not hold. Success: each product prints `PASS` with a URL.
After the approvals expire, new ones are needed (the dry run lists what is missing).

## 2. Repair the live listings that deliver less than they describe

```
python scripts/apply_listing_repairs_20261029.py          # dry run: shows every change
python scripts/apply_listing_repairs_20261029.py --live   # applies them
```

- Trademark DIY Filing Action Kit ($69, vkqogv): attaches the promised XLSX tracker
  (fee sheet rebuilt on the USPTO schedule) and the guide with a dated fee-correction
  page (statement of use $150 and extension $125 per class; the guide said $200-250 and $225).
- GPSR EU Seller Action Kit ($79, fetmu): attaches the promised cost-planner workbook.
- 27 listings say "... and this guide." on the listing page; fixed to "and a PDF guide."

Result per listing: `data/listing_repairs_20261029.json` (PASS / FAILED with the reason).
Remaining after this: 21 thin listings (decision: improve, reprice or unpublish), and
the duplicate "5-Minute Context Reset Playbook" listing. Unpublishing is a Gumroad
dashboard action only; the API ignores it.

## 3. Free disk space (urgent)

C: had 4.64 GB free on 2026-10-29 17:00 UTC. `%USERPROFILE%\.local\share\opencode\opencode.db`
is 127.5 GB. Below 2 GB the factory stops generating; at 0 the machine stops.
Back it up or compact it, your call; nothing in the factory reads it.

## 4. Keep the factory running after a reboot

```
powershell -ExecutionPolicy Bypass -File scripts\install_factory_autostart.ps1
```

Registers the supervised server and loop at log-on. Today they were started by hand.

## 5. Alerts on your phone

Open Telegram, send `/start` to the factory bot. The bot token works; it has no chat
to deliver to until you write to it once (`connection_verifier.py` shows `telegram DEGRADED`).
Then `python scripts/n8n_notification_selfcheck.py` lists the chat id under
`discoverable_chat_ids`; set it as `OPENCLAW_TELEGRAM_CHAT_ID` in `.env` (or tell Claude to),
and restart the server so the command handler (`lib/telegram_commands.js`) accepts it.

## 6. Decisions that unlock measurement and reach

| Decision | Why | Status today |
|---|---|---|
| A free analytics receiver (e.g. Cloudflare Web Analytics, needs your account) | the only way to know whether anyone visits; without it the funnel diagnosis stays "A or B or C" | B6 BLOCKED |
| Approve EXP-B16-007-LI-01 and post its two LinkedIn texts a week apart | first two-arm experiment on a free channel you can use today | PENDING_APPROVAL, see `EXPERIMENT_EXP-B16-007-LI-01.md` |
| Create the Pinterest board "Small Business Finance Tools" | 86 product pins wait only for it | B18 BLOCKED |
| New Paddle API key | second checkout path; current key returns 403 | B12 BLOCKED |

## What runs without you

Every ~10 minutes (supervised): health and recovery, n8n watchdog and missed-run catch-up,
demand sensing, the six-agent product chain, site publication, IndexNow.
Daily: product registry rebuild and listing checks, arm states, distribution exposure
reading (Telegraph), experiment cycle, commercial readiness. Sunday: weekly report.
Sales are polled every 4 hours by n8n. The dashboard's "القمع والتجارب" tab shows the
funnel, what buyers receive and experiment exposure.
