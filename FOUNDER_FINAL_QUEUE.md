# FOUNDER FINAL QUEUE

> Galaxy Forge — after the complete CTO+COO factory audit (2026-08-15).
> All software-side gaps are CLOSED. Every item below is a **true human gate** — something only the founder can do (an account, a credential, an onboarding step, a platform approval). The factory verifies completion automatically wherever possible.
> Ordered by: fastest path to first verified revenue, then highest potential, then lowest effort.

---

## 1. Gumroad — connect a payment method and enable the product (FASTEST path to $155 sale)

- **ACTION:** Log into `aekraft.gumroad.com` → open the product `pzTmMb4v8cih3nbWTj5TeA==` (short URL `https://aekraft.gumroad.com/l/iaiyt`) → complete Gumroad's payment-method onboarding → click **Enable product**.
- **WHY:** The product is real and DRAFT. $0 of real revenue exists today. This is the single lowest-effort action that unlocks an actual purchasable product. The factory's revenue-integrity gate, tracking and reporting are already tested and waiting.
- **EXACT STEPS:**
  1. Open `https://aekraft.gumroad.com/l/iaiyt` while logged in.
  2. In the product editor, finish the payout/payment-method setup Gumroad prompts for.
  3. Set the product live (Enable). Price is already $155.
  4. Nothing to change in code — the factory reads the live product state directly from Gumroad's API.
- **EXPECTED RESULT:** Product status becomes `published`; a buyer can now purchase; purchases flow into `sales_ledger` / the revenue path.
- **HOW THE FACTORY VERIFIES:** Next automated `arm_publish`/Gumroad status check will read `published` (not DRAFT). `data/publish_protection_state.json` will record `has_ever_published_successfully: true` on the first verified publish.

## 2. Paddle — set `PADDLE_WEBHOOK_SECRET` and configure the webhook destination

- **ACTION:** Set `PADDLE_WEBHOOK_SECRET` in `.env` (gitignored), then configure the webhook destination in `vendors.paddle.com`.
- **WHY:** The Paddle checkout URL is currently blocked on account-level onboarding (`transaction_checkout_not_enabled`), and the webhook endpoint is fail-closed (`MISSING_SECRET`) until the secret exists. Both are human steps on the payment provider side.
- **EXACT STEPS:**
  1. In Paddle dashboard → Developer tools → Webhooks → add `https://<your-host>/webhooks/paddle`.
  2. Generate a webhook secret and add `PADDLE_WEBHOOK_SECRET=<secret>` to `.env` (alongside the existing `PADDLE_API_KEY`).
  3. Restart the factory so the running process picks up the new env var.
- **EXPECTED RESULT:** Paddle webhook events stop returning `MISSING_SECRET`; verified events flow into the revenue path.
- **HOW THE FACTORY VERIFIES:** `GET /api/v1/health` (or the paddle arm status) reports the webhook as configured; a real checkout event is recorded in `data/paddle_webhook_events.jsonl`. If a REJECTED event arrives before this is done, the factory now sends a throttled Telegram alert (once/hour) instead of silently absorbing it.

## 3. Paddle — complete seller onboarding to unblock checkout (transaction_checkout_not_enabled)

- **ACTION:** In `vendors.paddle.com`, complete the remaining seller-onboarding steps (business/payout details, tax questionnaire) that gate checkout-URL creation.
- **WHY:** 6 real products exist in `data/paddle_products.json` with real prices (e.g. "AI-Powered Compliance Automation System for Accounting Firms" at $388) but checkout cannot be created until this account-level flag clears.
- **EXACT STEPS:** Paddle dashboard → onboarding checklist → complete all remaining required fields.
- **EXPECTED RESULT:** `check_paddle_checkout_status.py` no longer reports `transaction_checkout_not_enabled`; checkout URLs can be created.
- **HOW THE FACTORY VERIFIES:** `commercial_operations`/paddle arm readiness reports checkout-capable; a checkout URL is actually creatable via the API.

## 4. Awin — apply to the DigitalOcean affiliate program (TOMORROW per plan; adds the first real affiliate link)

- **ACTION:** Apply to the DigitalOcean affiliate program via the Awin network (merchant profile `123996`).
- **WHY:** The entire affiliate chain is software-verified and waiting: portfolio 17 opportunities / 12 verified, launch-prep 5 content pieces, tracking IDs configured, click/conversion funnel live. The ONLY missing piece is a real affiliate link, which requires this application.
- **EXACT STEPS:**
  1. Apply/join the DigitalOcean program on Awin (payout via the configured Payoneer path).
  2. Once approved, paste the issued affiliate link/ID into the factory's launch-prep record (`affiliate_launch_prep`).
- **EXPECTED RESULT:** `affiliate_chain_readiness` reports `link_status: CONFIGURED`; 18 real clicks recorded to date become attributable; first commission becomes recordable (and the revenue-integrity gate requires REAL evidence + transaction id before it ever counts).
- **HOW THE FACTORY VERIFIES:** `GET /api/v1/affiliate-chain-readiness` (new this audit) shows the link status flip from `NOT_CONFIGURED` to `CONFIGURED`, and the launch-prep record now carries a real tracking ID.

## 5. Authorize at least one social platform (6 channels are content-only HUMAN_GATEs)

- **ACTION:** Authorize one social account (Pinterest, TikTok, YouTube, X, Facebook or LinkedIn) so the distribution-prep engine can publish.
- **WHY:** All six exist only as content-generation assets + `HUMAN_GATE` declarations; publishing requires platform OAuth/authorization the factory cannot perform itself.
- **EXACT STEPS:** Create/authorize an app token or connect the platform account; add the credential to `.env`; the repurposing engine + distribution-prep content is already ready.
- **EXPECTED RESULT:** A distribution channel stops reporting `HUMAN_GATE` and becomes publish-capable behind the existing publish-safety protection.
- **HOW THE FACTORY VERIFIES:** `distribution_capability_matrix` / channel adapters report a non-`HUMAN_GATE` state for the platform.

## 6. Save one Amazon niche research report (seed for the discovery layer)

- **ACTION:** Save a real Amazon research/niche report into `data/niche_reports/` (the directory is currently empty by design — a human-gated research input).
- **WHY:** The discovery layer's niche pipeline is intentionally gated on a real report; without it the niche engine has no source input.
- **EXACT STEPS:** Place the report file in `data/niche_reports/`.
- **EXPECTED RESULT:** The discovery pipeline picks up real niche data.
- **HOW THE FACTORY VERIFIES:** `niche_reports/` is non-empty on the next discovery scan.

## 7. Optional / deferred (NOT required for first revenue)

- **Etsy / Payhip credentials** — arms exist and report `UNAVAILABLE` cleanly; only needed once multi-storefront distribution is wanted.
- **Offsite/encrypted/scheduled backups + an automated `restore_from_snapshot()`** — deliberately deferred (see `BACKUP_AND_RESTORE.md`): premature at $0 revenue, and restore semantics need the founder's explicit sign-off. Today backups are event-triggered `.bak` snapshots of the 9 real state files, manual restore.
- **Awin activation was explicitly deferred to tomorrow** (this audit ran without it per plan) — it is item 4 above for when the time comes.

---

## After the queue is cleared (what runs automatically)

- Daily `commission_opportunity_scan` → `rank_commission_shortlist()` picks the best live opportunity.
- `affiliate_chain_readiness` monitor reflects the live link state; `commercial_link_monitor` (dry-run safe) watches active links.
- `treasury_status` reports real verified/pending from the ledger — a real confirmed commission will now actually count (the hardcoded-`0.0` bug is fixed).
- `health_monitor` asserts data-freshness of the real output files and alerts on staleness transitions.
- A Paddle REJECTED webhook (if any) now alerts via Telegram (throttled 1/hour) instead of a silent blanket-200.
- Stale unreplayable retries auto-expire after 7 days with an audit trail in `data/recovery_actions.jsonl` (5 old `arm_publish:gumroad:*` entries expire ~2026-08-19/20 automatically).