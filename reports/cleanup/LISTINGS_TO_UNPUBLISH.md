# Gumroad listings to unpublish

Founder action, manual on Gumroad. The factory makes no Gumroad writes.

Source: Gumroad API `list_products` (read-only GET, 2026-10-17), saved in `data/seo/gumroad_seo_audit.json`. All three listings below show `published: true` and 0 sales.

## Urgent

### 1. [Unavailable] AI Workflow QA & Stress Test
- **Link:** https://aekraft.gumroad.com/l/owtmpe (id `IW58tjt2zS14fPYrWZOuxg==`, price $0)
- **Problem:** still published, but its own title says it is unavailable. That confuses buyers and costs trust.
- **Action:** unpublish (set to draft).

### 2. The 5-Minute Context Reset Playbook: duplicate
Two published listings have the same title and price ($15):

| Link | Id | Tags | Description | SEO score |
|---|---|---|---|---|
| https://aekraft.gumroad.com/l/akxaae | `rMOopS7Q7LHxwaPTY462uw==` | 5 | 854 chars | 80 |
| https://aekraft.gumroad.com/l/vhofn | `9Zq9SGkALI0tjd7A97Pc_A==` | 4 | 839 chars | 65 |

- **Problem:** two identical products split views and confuse buyers.
- **Suggestion:** keep `akxaae` (the more complete listing) and unpublish `vhofn`.
  - Listing views are visible only in your Gumroad dashboard; the API does not return them. If `vhofn` shows clearly more views there, keep that one instead.
- Both listings have a cover ready in `reports/covers/gumroad/`. Skip the one you unpublish.

### 3. EU AI Act Compliance Toolkit ($155)
- **Link:** https://aekraft.gumroad.com/l/iaiyt (id `pzTmMb4v8cih3nbWTj5TeA==`)
- **Problem:** still published, although its promotion was withdrawn (earlier founder decision; the product's core regulatory premise changed).
- **Action:** unpublish (set to draft).

## How (approximate button names; not checked against today's dashboard)
1. Open gumroad.com/products and find the listing.
2. Edit, then Unpublish.

## After unpublishing
- Reply "CLEANUP DONE". The factory then re-reads the catalog (read-only) and updates its records.
- **Expected:** published listings go from 76 to 73.
- If you keep the EU AI Act Toolkit live, they go to 74.
