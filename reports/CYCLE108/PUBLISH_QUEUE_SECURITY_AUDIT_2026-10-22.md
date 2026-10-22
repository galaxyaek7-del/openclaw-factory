# Publish Queue Security Audit - 2026-10-22 (Cycle 108, Phase 3)

Read-only audit. No product, queue, credential, price, listing, or financial
record was changed. No publish was attempted.

## Target

`affiliate/publish_queue.py` - untracked parallel-owned file.

- 81 lines, 3,904 bytes, mtime `2026-09-23 18:34`.
- `data/publish_queue.json` is also untracked and currently holds 4
  `PENDING_CAP` items.
- No importer exists: a repository-wide search found only string references
  (`executive_orchestrator.py`, `factory_loop.js`, `founder_alert.js`,
  `n8n_notify.js`), never an `import` or a subprocess call.
- `scripts/first_sale_orchestrator.py:1416` already labels it
  "parallel-owned".

## Capability

`retry_queue()` performs, per pending item:

1. `gp.load_token()` (reads the credential before any item is processed),
2. `gp.create_product(...)`,
3. `gp.enable_product(...)`,
4. `gp.update_product(..., {"tags": ...})`,
5. `gp.get_product(...)` plus price/URL assertions,
6. `save_queue(...)`.

This is a create-then-enable publication path.

## The central write gate holds

`channels/gumroad_publisher.py` enforces the centralized, fail-closed write
gate as the first statement of every mutating function:

- `create_product` line 452: `_require_write_authorization("create_product")`
- `enable_product` line 888: `_require_write_authorization("enable_product")`
- also `update_product` (674/944) and `update_product_file` (803)

Direct probe in this environment (`FACTORY_LIVE_PUBLISH` unset):

```
check_write_authorization('create_product')
  -> allowed=False
     reason='no scoped authorization and FACTORY_LIVE_PUBLISH is not true;
             live mutation is disabled'
     state='NOT_CHECKED', live_publish_flag=False

gumroad_publisher.create_product('x', {...})
  -> WriteNotAuthorized: BLOCKED live Gumroad mutation 'create_product': ...
```

The gate runs **before any validation or network call**. Therefore
`retry_queue()` cannot publish while `FACTORY_LIVE_PUBLISH=false` (and cannot
publish with a stale or unverifiable authorization state). A denied call is
caught by the item-level `except Exception`, recorded as an error, and the
untracked queue JSON is rewritten; no external mutation occurs.

## What it would bypass if the gate were ever opened

`retry_queue()` calls the publisher directly, so it does not pass through
`distributor.distribute()` and therefore bypasses:

- `channels/publish_protection.check_publish_allowed()` (global emergency
  stop, per-arm daily/hourly caps, cooldown after failures, minimum spacing,
  new-arm first-publish approval, elevated-risk approval),
- duplicate/registry checks performed in the distribution layer,
- the Quality Gate and file-defect/claim-risk overrides.

That is a conditional, secondary protection gap, not a live publishing path.

## Test signal

`tests/test_final_rehearsal.py::TestFinalRehearsal::test_no_autopublish_path`
fails **locally only**, because it globs `affiliate/*.py` and the untracked
file is present in this worktree. Both the module and its queue file are
untracked, so a clean checkout (and CI) does not contain either one. The test
is tracked and unchanged; no test was weakened.

## Recommendation

Owner action, not a Cycle 108 change:

1. Delete `affiliate/publish_queue.py` and `data/publish_queue.json`, or
2. Route the queue through `distributor.distribute()` so publish protection,
   quality checks and the write gate all apply, or
3. Add an explicit `check_write_authorization` precheck at the top of
   `retry_queue()` so denial is one clean result instead of four local error
   entries.

Do not commit the file as-is: it bypasses publish protection and would make a
tracked test depend on an untracked module.

## Decision taken this cycle

No edit. Ownership is unclear, the file is month-old, it has no callers, and
the central gate already prevents every live mutation. Changing it would also
require committing a test that imports an untracked module, which would fail
in CI. The risk is disclosed instead of silently patched.
