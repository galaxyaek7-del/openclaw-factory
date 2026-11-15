# Public lead ingest

A free-tier Cloudflare Worker that receives the existing customer-site lead forms, stores each submission in KV as an **unverified external lead**, and never counts it as demand.

The worker is **disabled by default**: `PUBLIC_LEAD_INGEST_ENABLED = "false"`. A POST returns `503 disabled` until the flag is explicitly turned on.

Full setup, limits, and the reachability comparison are in `docs/factory/PUBLIC_LEAD_INGEST.md`.

## Local checks

```powershell
node --test tests/test_public_lead_ingest.js
```

## Deploy outline

1. Create a Cloudflare account and KV namespace.
2. Replace `REPLACE_WITH_KV_NAMESPACE_ID` in `wrangler.toml`.
3. Optionally set `TURNSTILE_SECRET` with `wrangler secret put TURNSTILE_SECRET`.
4. Deploy with the flag still false and verify POST returns `503 disabled`.
5. Set `PUBLIC_LEAD_INGEST_ENABLED = "true"`, deploy again, and test one submission.
6. Set `window.GF_PUBLIC_LEAD_ENDPOINT` in `customer_site/assets/public-lead-config.js` to the worker URL.

No secret belongs in this repository.
