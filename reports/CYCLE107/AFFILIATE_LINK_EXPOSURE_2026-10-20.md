# Affiliate Link Exposure Disclosure

Date: 2026-10-20
Severity: high for hygiene, low for direct financial loss.
Incident: `INC-6617e0c40f33`

## What was found

`customer_site/guide-systemeio-affiliate.html`, line 72, hardcodes the real
systeme.io affiliate URL with the live partner id. The file is committed, and
the repository is public. The link has been in history since commit `e341d28`,
which predates this cycle's render helper and its never-commit rule.

A `git grep` over `HEAD` for the real id shape returns exactly one file: this
one. No other committed file contains a systeme id.

## Why it matters, and why it is not a credential leak

The id is a tracking identifier, not a password. Anyone holding it can attribute
a referral to this account; they cannot log in, change settings, or withdraw
money with it. Affiliates publish these ids in every link they share. The
problem is narrower: this factory's own rule says the tracked link is never
committed, because committing it couples a public artifact to an account
identifier and makes rotation harder.

## What was done

- `tests/test_no_committed_affiliate_links.py` scans `HEAD` for
  `sa=` followed by an optional `sa` and 30+ lowercase hex characters.
- Exactly one file is allowlisted, with its date and reason. The allowlist is
  self-cleaning: the test fails if the file is fixed and the entry stays.
- This disclosure and incident record.

The page was not edited. The id was not rotated.

## What only the founder can do

1. **Rotate the id** in the systeme.io affiliate settings. That is the only
   action that removes the exposure already present in public git history.
   Rotation is free and does not require a new account.
2. Decide whether the page should keep a direct link, a local redirect, or a
   rendered placeholder. Editing it now stops future exposure but does not
   undo history.

## What is still unknown

- Whether the page is publicly deployed today. The local tree serves it under
  `/site/`; the public host is not verified.
- Whether the id has already been collected. Public history cannot be recalled.
- Whether rotating it breaks links already shared. No click on this page is
  recorded, but no recorded click is not proof that no link exists.
- Whether other programs' ids exist in the tree under a shape this pattern does
  not cover. Only the systeme shape was scanned.

## Why the guard is still worth having

Rotation is a founder action that may take time. A guard makes the next
committed id a test failure rather than another discovery months later, and it
forces this exception to be revisited instead of silently becoming permanent.
