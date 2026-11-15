# Public lead ingest: reachability options and preparation

Status: **prepared, disabled, not deployed**.

The existing `customer_site/` lead forms can write to the local Express API, but GitHub Pages cannot reach a laptop API. The current public path therefore records no external leads. This document compares the three viable $0 options and prepares the recommended one behind an OFF flag.

`reports/phase5/visit_receiver_options.md` covers visit counting, not lead capture; it does not solve this path.

## Options

| Option | Public reachability | $0 | Laptop exposure | Spam / rate control | Data ownership | Setup effort | Verdict |
|---|---|---|---|---|---|---|---|
| A. Cloudflare Worker + KV (+ optional Turnstile) | Yes, public HTTPS endpoint | Free tier, verify current limits | None | Built into this code: origin allow-list, honeypot, size limit, rate limit, dedup, optional Turnstile | Leads stay in the founder's Cloudflare account | Medium: account, KV namespace, one deploy | **Recommended** |
| B. Hosted form service (Formspree/Netlify Forms free tier) | Yes | Free tier, verify current limits | None | Vendor-provided, usually limited on free plans | Vendor stores the leads | Low | Acceptable fallback, weaker ownership and less control |
| C. Direct email/contact link | Yes | Yes | None | None | Email provider | Lowest | Does not create a stored lead record; no reliable counting or dedup |

## Recommendation

Use **Option A**: a Cloudflare Worker with KV storage and an optional Turnstile secret. It is the only option that is public, $0 at low volume, does not expose the laptop, and keeps the lead record under the founder's control while allowing an explicit `UNVERIFIED_EXTERNAL` label.

The worker is in `cloudflare/lead-ingest/` and is **OFF by default**:

```toml
PUBLIC_LEAD_INGEST_ENABLED = "false"
```

A POST while OFF returns `503 disabled` and writes nothing.

## What the worker does

- Accepts `POST` JSON only from the allow-listed origins:
  - `https://galaxyaek7-del.github.io`
  - `http://localhost:3000`
  - `http://127.0.0.1:3000`
- Accepts `message` or the local API's `interest` alias as the required message, and stores `product_interest`/`product_id` when supplied.
- Rejects non-POST methods, disallowed origins, non-JSON bodies, bodies over 8 KB, invalid emails, missing messages, messages over 4,000 characters, and messages with more than 3 links.
- Uses a hidden `website` honeypot field and returns `200 ignored` without storing.
- Limits each hashed client IP to 5 submissions per 10-minute window.
- Deduplicates the same email + message for 30 days.
- Optionally verifies a Cloudflare Turnstile token when `TURNSTILE_SECRET` is set.
- Stores no raw IP address. It stores a salted SHA-256 `ip_hash`, a truncated user agent, and the Cloudflare country code when present.
- Stores every accepted row as:
  - `verification_status: "UNVERIFIED_EXTERNAL"`
  - `provenance_quality: "external_unverified"`
  - `counted_as_demand: false`
  - `synthetic: false`
- Returns `status: "accepted"`, a `lead_id`/`signal_id`, and `counted_as_demand: false`.

The worker does not write `data/customer_interest.jsonl`, does not call `demand_gate.py`, and does not count as demand.

## Manual setup

1. Create a Cloudflare account.
2. Install Wrangler: `npm install -g wrangler`.
3. Run `wrangler login`.
4. Create the KV namespace: `wrangler kv namespace create LEADS`.
5. Put the returned namespace id into `cloudflare/lead-ingest/wrangler.toml`.
6. Set a random IP salt: `wrangler secret put LEAD_IP_SALT`. Without it the worker uses a public default salt, so the stored IP hash could be brute-forced for IPv4.
7. Optional but recommended: create a Turnstile widget and run `wrangler secret put TURNSTILE_SECRET` from `cloudflare/lead-ingest`. Do not set this secret until the forms include a Turnstile widget; without a token the worker rejects every form POST with `turnstile_required` and the forms fall back to email.
8. Deploy while the flag is false: `wrangler deploy`.
9. Verify a POST returns `503 disabled`.
10. Set `PUBLIC_LEAD_INGEST_ENABLED = "true"` and deploy again.
11. Submit one real test lead and confirm the KV record says `UNVERIFIED_EXTERNAL`.
12. Set `window.GF_PUBLIC_LEAD_ENDPOINT` in `customer_site/assets/public-lead-config.js` to the worker URL. The forms keep using the local endpoint while this value is empty.

No secret belongs in the repository. The only committed value is the public endpoint URL after deployment.

## Bringing leads into the local factory

Leads live in Cloudflare KV, not in the local ledger. To review them locally:

```powershell
wrangler kv key list --namespace-id <id>
wrangler kv key get --namespace-id <id> "lead:<lead_id>"
```

Append reviewed rows to a local inbox with `verification_status: "UNVERIFIED_EXTERNAL"` and `counted_as_demand: false`. Do not copy them into `data/customer_interest.jsonl` and do not treat them as demand until a human proves the buyer and the purchase. The demand gate skips rows explicitly marked `UNVERIFIED` or `UNVERIFIED_EXTERNAL`.

## Limitations

- KV rate limiting is approximate; it is not an atomic counter.
- Dedup is best-effort: if the dedup write fails after the lead is stored, the lead is still accepted and a retry could create a duplicate.
- There is no automatic email notification and no automatic local import.
- Turnstile is optional; without it the worker still uses the honeypot, size, origin, dedup, and rate controls.
- A stored lead is not a sale, a verified buyer, or demand. The only success definition remains `FIRST_SALE_VERIFIED`.
