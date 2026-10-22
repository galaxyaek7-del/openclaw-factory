# External-write safety audit (2026-10-22)

Status: **PASS for every catalog/social publishing path found; HOLD on the items listed under Gaps.** No live action was taken, and `FACTORY_LIVE_PUBLISH` stays false.

## Root cause (OBSERVED)

`FACTORY_LIVE_PUBLISH` was enforced in exactly one place: `channels/write_gate.py`, called only by `channels/gumroad_publisher.py`. Every other platform mutation was unguarded:

- Paddle product, price and checkout;
- Etsy listing;
- X post;
- Telegraph page create/edit;
- IndexNow submission;
- third-party contact forms;
- freelancer.com bids;
- a direct Gumroad PUT script that bypassed the publisher.

`distributor.distribute(dry_run=False)` reached the Paddle, Etsy and X arms with no global flag check. The only thing standing in front of a live Paddle push through `POST /api/distribute` was the `commercial_reality` index gate.

## Design

One boundary in `channels/write_gate.py`, enforced **inside each mutation function**, so every caller is covered, direct or indirect (arms, distributor, scripts, Mission Control, the customer flow):

| Class | Requires | Why separate |
|---|---|---|
| Catalog / social / search submission | `FACTORY_LIVE_PUBLISH=true` | existing convention |
| Checkout transaction (buyer payment link) | `FACTORY_LIVE_PUBLISH` or `GF_ALLOW_CHECKOUT_TRANSACTIONS=true` | lets the founder open the purchase path without making the catalog writable |
| Outbound message to a third party (contact forms, bids) | `GF_ALLOW_OUTBOUND_MESSAGES=true` | permission to publish is not permission to contact people; `FACTORY_LIVE_PUBLISH` does not cover it |

- Gumroad keeps its stronger existing check: flag or single-use scope, plus a VERIFIED, fresh credential state. The new function never relaxes it.
- Junk and contradictory values (`maybe`, `0`, `TRUE-ish`) deny.
- The gate runs before any network I/O.

## Coverage (VERIFIED by tests; nothing reached the network)

| Path | Before | Now |
|---|---|---|
| `paddle_publisher.create_product / update_product / create_price` | open | gated (catalog) |
| `paddle_publisher.create_checkout_transaction` | open | gated (checkout) |
| `etsy_publisher.create_product` | open | gated (catalog) |
| `x_arm.XArm.publish(dry_run=False)` | open | gated; returns a blocked result without tripping the circuit breaker |
| `PaddleArm.publish(dry_run=False)` (indirect, the distributor path) | open | refused inside `create_product` |
| `lib/telegraph_safe_edit.append_paragraph` (editPage) | open | gated |
| 13 tracked `scripts/publish_telegraph_*.py` (module-level createPage) | open | refuse at import, before any request (VERIFIED by running one) |
| `scripts/submit_indexnow_round2.py`, `submit_indexnow.py` | open | gated (VERIFIED by running) |
| `scripts/upgrade_thin_descriptions.py` (direct Gumroad PUT) | **bypassed the Gumroad gate** | same Gumroad check as the publisher |
| `scripts/direct_customer_outreach.py` (contact forms) | open; **sent for real on 2026-10-02** | gated (message); never overwrites the 2026-10-02 record |
| `oauth_cascade.py` (freelancer.com bids, manual) | open | gated (message) |

**Regression guard.** `tests/test_platform_write_gate.py::TestCoverageInventory` scans every tracked `.py` file. Any file that sends a write to a known platform host must reference the write gate, or appear in an explicit exemption list with its reason. On its first run it found three paths that the manual inventory missed: `freelancer_resume.py`, the root `submit_indexnow.py`, and `scripts/integrated_platform_test.py`.

**Exemptions (documented in the test):**

| File | Reason |
|---|---|
| `scripts/run_campaign_review.py` | reads only |
| `scripts/integrated_platform_test.py` | writes to localhost only |
| `channels/gumroad_publisher.py` | stronger Gumroad gate |
| `channels/linkedin_publisher.py` | untracked parallel work; defaults to dry run |
| `freelancer_resume.py` | see Gaps |

**Not publishing, not gated:**

- **Telegram** (`lib/telegram_direct.js`, `lib/telegram_commands.js`, `telegram_direct.py`): messages to the founder's own chat.
- **Groq and TypeSafe** (`book_generator.py`, `audit_seed.py`, `jev_adapter.py`): AI computation calls. `jev_adapter.py` targets a third-party AI API; any cost there is UNKNOWN.

## Gaps and founder decisions (HOLD)

1. **`freelancer_resume.py` runs on every factory_loop tick** (2,276 ticks, all no-op).
   - When a Freelancer OAuth token appears, it will place one real bid on project 40742370.
   - This executes an explicit **founder order dated 2026-10-01**, so it was **not** gated: overriding an explicit approval is the founder's call.
   - Decision needed: keep the standing order, or put it behind `GF_ALLOW_OUTBOUND_MESSAGES`.
2. **The 2026-10-02 contact-form send** to EaseCert used `partnerships@galaxyforge.com`. Ownership of that address is unverified; any reply may be unreadable or go to a third party. Decision needed: confirm the address.
3. **Untracked parallel files not edited:**
   - `channels/linkedin_publisher.py` (defaults to dry run);
   - `scripts/publish_telegraph_dv.py` and `scripts/publish_telegraph_restaurant.py` (module-level createPage, **ungated**).

   They should get the same guard when they are committed.
4. **The distributor itself still has no global flag check.** Live writes are now refused inside every gated publisher. A distributor-level check would be defense in depth, but it touches 14 test files that exercise live distribution with mocks. Proposed, not applied.

## Closed in the follow-up round (same day)

**Distributor-level gate (former gap 4).** `distributor.distribute(dry_run=False)` now checks `check_platform_write(<arm>, "distribute")` before any arm is attempted. A refusal is recorded as `skip_reason: "blocked by write gate: ..."`.

- The 13 test classes that exercise mocked live distribution now opt in for their own duration (`@patch.dict(os.environ, {"FACTORY_LIVE_PUBLISH": "true"})`).
- `tests/test_platform_write_gate.py` proves that refusal is the default.
- One remaining failure, `test_exp_c81_utm_regression::test_unconfigured_default_now_consults_the_gate`, is the parallel session's uncommitted rewrite. It expects a "mandatory central Quality Gate" that the committed `distributor.py` does not implement. The committed version of that test passes.

**Former gap 3, now gated** (all three are untracked parallel files; only the guard was added):

- `channels/linkedin_publisher.create_post` (live branch);
- `scripts/publish_telegraph_dv.py`;
- `scripts/publish_telegraph_restaurant.py`.

The LinkedIn exemption was removed from the coverage test.

**Kept, by founder order.** `freelancer_resume.py` is unchanged and remains a documented exemption.

## Gate consequences (DERIVED)

**Raising `commercial_reality.highest_verified_index` to 1 or more** would open `POST /api/distribute`. With this change:

- Paddle, Etsy and X live writes are still refused unless `FACTORY_LIVE_PUBLISH=true`;
- Gumroad still needs the flag or a scope, plus verified credentials.

This removes the specific risk that made opening the distribute gate unsafe. Opening it remains a founder decision (`SIGNAL_RECEIVED`).

## Tests

- `tests/test_platform_write_gate.py`: 11 passed.
- Mocked live-path tests that now opt in explicitly with `FACTORY_LIVE_PUBLISH=true` for their own duration: `tests/test_paddle_arm.py`, `tests/test_x_arm.py`, `tests/test_telegraph_safe_edit.py`. Result: 90 passed.
- The broader run across every test file touching the gated modules is recorded below.
