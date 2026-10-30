# Founder actions (updated 2026-10-29)

Everything below is prepared and tested. Each step needs you because it writes
to an external account, creates an account, or touches data only you may
decide on. Run the commands from `C:\openclaw-dasgboard` (in Claude Code,
prefix with `!`).

## 1. Publish the last three batch-16 products (approvals renewed, valid until 2026-11-01 20:56 UTC)

```
python scripts/publish_batch14.py --batch batch16 --live --approvals data/publication_approvals.json --only B16-008 B16-009 B16-010
```

Gumroad's 24-hour limit has room for exactly these three (7 created today).
The command refuses on its own if the window, approval, revision or auth
freshness does not hold. Success: each product prints `PASS` with a URL.
After the approvals expire, new ones are needed (the dry run lists what is missing).

### Making publishing automatic (one-time)

Add `GF_AUTO_PUBLISH_APPROVED=true` to `.env`. From then on the factory loop publishes,
every tick, each product you have approved, as soon as Gumroad's 24-hour window has
room (`scripts/publish_approved_daily.py`). Approving is then your only step:

```
python scripts/approve_products.py --batch batch16 --only B16-008 B16-009 B16-010 --reference "approved by founder, chat 2026-10-30"          # preview
python scripts/approve_products.py --batch batch16 --only B16-008 B16-009 B16-010 --reference "approved by founder, chat 2026-10-30" --yes    # record
```

Each approval is bound to the product's exact files, listing text, price and currency
and expires (72 h by default); any later change needs a new approval. Without the
switch the loop only reports approved products as ready.

## 2. Repair the live listings that deliver less than they describe

```
python scripts/apply_listing_repairs_20261029.py          # dry run: shows every change
python scripts/apply_listing_repairs_20261029.py --live   # applies them
```

- Trademark DIY Filing Action Kit ($69, vkqogv): attaches the promised XLSX tracker
  (fee sheet rebuilt on the USPTO schedule) and the guide with a dated fee-correction
  page (statement of use $150 and extension $125 per class; the guide said $200-250 and $225).
- GPSR EU Seller Action Kit ($79, fetmu): attaches the promised cost-planner workbook.
- EU Late Payment Recovery Kit ($59), Etsy Ads ROI Playbook + Calculator ($39), Diminished
  Value Claim Kit ($59): each guide refers to its tracker/workbook, which exists and recalculates
  with 0 errors but was never attached. Bundled with the exact PDF buyers get today.
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
| A free analytics receiver: Cloudflare Web Analytics, manual setup (no DNS change), in your name; then `python scripts/set_cloudflare_analytics.py --token <site token> --apply` and push (`--remove --apply` undoes it) | the only way to know whether anyone visits; without it the funnel diagnosis stays "A or B or C" | B6 BLOCKED; command ready and tested |
| A public inquiry receiver (free form service forwarding to your inbox, or a free serverless endpoint writing to the queue) | all three phase-3 demonstrations and three earlier offers wait on it; the local queue (`inquiry_intake.py` + site-form signals) is ready | BLOCKED |
| Approve fixing our own accessibility warnings on the public site: `python scripts/fix_site_accessibility_20261030.py --check` shows 22 -> 6 warnings on a copy; `--apply` writes 16 attribute edits on 8 pages; then commit and push. The 6 left are heading structure (3 pages without h1, 3 skipped levels) and need a person | proof for the accessibility quick-check offer; a public-site change | PREPARED and tested |
| Approve EXP-B16-007-LI-01 and post its two LinkedIn texts a week apart | first two-arm experiment on a free channel you can use today | PENDING_APPROVAL, see `EXPERIMENT_EXP-B16-007-LI-01.md` |
| Create the Pinterest board "Small Business Finance Tools" | 86 product pins wait only for it | B18 BLOCKED |
| New Paddle API key | second checkout path; current key returns 403 | B12 BLOCKED |

## 7. When an inquiry arrives by e-mail

The site already links your address on 38 pages, and the three new offer drafts use the same link. To put an
e-mail inquiry in the review queue (the dashboard counts it; the address is never shown there):

```
python inquiry_intake.py record-email --arm micro_b2b --email sender@example.com --offer feed-preflight --received-at 2026-10-30T09:15:00Z --message "the text of their e-mail"
python inquiry_intake.py queue
python inquiry_intake.py review INQ-xxxxxxxxxxxx REPLIED --note "sent scope and price"
```

Arms: micro_b2b, research_data_services, ai_operations, productized_ai_services, digital_products,
content_distribution, childrens_media_studio, affiliate_intelligence. Outcomes: REPLIED, QUALIFIED, NOT_A_FIT, SPAM, CLOSED.

## 8. Children's channel on YouTube (automatic once these are done)

The pipeline (checks, upload marked made for kids, Arabic subtitles, upload log) runs in the loop; see
`kids_studio/publishing/README.md`. Today both episodes pass every check except these two:

1. Once: create the YouTube API credentials in your own Google Cloud project (YouTube Data API v3, OAuth client
   "Desktop app"), then `python scripts/youtube_oauth_setup.py client_secret.json`, and add
   `GF_ALLOW_KIDS_VIDEO_UPLOAD=true` to `.env`.
2. Per episode, after watching it and having the Arabic reviewed:
   `python scripts/approve_kids_episode.py --episode ep01_nunu_little_bridge --privacy unlisted --child-safety-reviewed --arabic-reviewed`

The two cuts are animatics without voices. Start with `unlisted` if you want to watch the uploaded version
before making it public.

## What runs without you

Every ~10 minutes (supervised): health and recovery, n8n watchdog and missed-run catch-up,
demand sensing, the six-agent product chain, site publication, IndexNow.
Daily: product registry rebuild and listing checks, arm states, storefront catalogue,
site pages for newly published tools (published on the next tick), distribution exposure
reading (Telegraph), experiment cycle, commercial readiness. Sunday: weekly report.
Sales are polled every 4 hours by n8n. The dashboard's "القمع والتجارب" tab shows the
funnel, what buyers receive and experiment exposure.
