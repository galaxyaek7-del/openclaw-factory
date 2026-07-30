# ADR-152 — Global Affiliate Commerce Engine: Full Architecture (documentation only, zero code)

**Date:** 2026-07-30
**Status:** Documented. **Zero code built by explicit founder decision**, matching the treatment ADR-148 (GCID) already established. This ADR is the detailed architecture for Phase 3 (Multi-partner) and Phase 4 (GCID) of ADR-150's roadmap — it replaces their one-paragraph sketches with a full design, but does not loosen any of ADR-150's real validation gates.

---

## The directive (verbatim)

> Founder Directive — Global Affiliate Commerce Engine (Phase 2)
>
> Affiliate Commerce is now a permanent core division of Galaxy Forge.
>
> The next objective is NOT to add random affiliate links. Build the foundation of a world-class affiliate commerce platform capable of managing every major affiliate network through one unified architecture.
>
> Design and implement:
>
> 1. Universal Affiliate Partner Registry — Amazon Associates, AliExpress Portals, CJ Affiliate, Impact, Awin, Rakuten Advertising, ShareASale, eBay Partner Network, Temu Affiliate, Walmart Affiliate, Best Buy Affiliate, Fiverr Affiliates, Adobe, Microsoft, Apple Services, Booking.com, Expedia, Hostinger, Namecheap, Cloudflare, DigitalOcean, and any future network through plugins.
>
> 2. Every partner must expose one unified interface: SearchProducts(), GenerateAffiliateLink(), TrackClicks(), ImportCommissionReports(), ValidateProgramStatus(), UpdateCatalog().
>
> 3. Never hard-code platform logic into the core. Every affiliate network must behave as an independent connector.
>
> 4. Mission Control must gain a dedicated Affiliate Commerce dashboard showing: Active networks, Pending approvals, Daily clicks, EPC, Conversion rate, Revenue, Commission awaiting payment, Broken links, API health, Synchronization status.
>
> 5. Build an Affiliate Intelligence layer. For every product automatically compute: Competition, Estimated demand, Commission percentage, EPC, Refund rate, Price history, Product quality score, Merchant reputation, Country availability.
>
> 6. Product discovery must eventually support every partner simultaneously. Search once. Compare every affiliate network. Recommend the highest real expected return while remaining honest.
>
> 7. Build every module as production-ready. No demo logic. No fake commissions. No fake products. No fabricated reviews.
>
> 8. The architecture must support tens of millions of products.
>
> 9. All affiliate activity must feed the Galaxy Forge Knowledge Graph — Clicks, Revenue, Trends, Partners, Products, Categories, Countries — all become searchable business knowledge.
>
> 10. Everything must remain Constitution compliant: Honest recommendations, Transparent affiliate disclosure, No manipulation, No fake reviews, Full compliance with every partner's terms.
>
> The objective is not an affiliate website. The objective is to build the world's most scalable autonomous Affiliate Commerce Engine that becomes a permanent business pillar inside Galaxy Forge.

## The real conflict, verified before any code was written

This directive was surfaced via `AskUserQuestion` before any implementation began, because it collided with two things the founder had already said, both earlier in this same session:

1. **The Mission Control V3 directive, sent immediately before this one, opened with**: "No further expansion of Affiliate Commerce should occur until a real affiliate account is approved and connected." At the moment this directive arrived, that condition was still unmet — verified directly: `AMAZON_ASSOCIATE_TAG` is unset, `data/affiliate_clicks.jsonl` was empty (zero real clicks), and zero real conversions exist anywhere.
2. **ADR-150 (written the same day as ADR-149, hours before this directive)** set explicit, disclosed, checkable gates before any multi-partner work: a real completed conversion confirmed via Amazon's own postback, sustained real click-through data over a real multi-week window, and — specifically for a second network — "a real, live business reason to add a second network." None of these are met today.
3. This directive's own item 7 ("no demo logic, no fake commissions, no fake products") is in direct tension with its own item 1 (20 named networks) — 19 of those 20 networks have zero real credentials, zero real account, and zero real API access anywhere in this factory. A "production-ready" `SearchProducts()`/`ImportCommissionReports()` connector cannot honestly exist for a network with no real account behind it; anything built would necessarily be scaffolding pretending to be more real than it is.

**The founder's answer, via `AskUserQuestion`: document the complete architecture now, build zero code.** The same resolution already applied to ADR-148 (GCID) and consistent with ADR-150's own re-trigger conditions — this ADR is that documentation.

## Relationship to ADR-148, ADR-149, ADR-150

- **ADR-148** deferred the full "Global Commerce Intelligence Division" vision entirely (zero code, zero roadmap) because the factory had zero real dollars.
- **ADR-149** built the real, narrow Phase 1 slice: one partner (Amazon Associates), one category, real click tracking.
- **ADR-150** formalized Affiliate Commerce as a **permanent division** with a 4-phase roadmap (Proof → Scale-within-partner → Multi-partner → GCID), each phase gated on real evidence, and sketched Phase 4 (GCID) in one paragraph.
- **This ADR (152)** is the founder's detailed architecture for what ADR-150's Phase 3 (Multi-partner) and Phase 4 (GCID) actually look like at full scale — a complete design most of a real engineering team would want before building any of it. It does not move the gates. Phase 3 and Phase 4 still require exactly what ADR-150 already said they require, restated in the "Re-trigger conditions" section below.

## Architecture (design only — every section below describes what would be built, not what has been built)

### 1. Universal Affiliate Partner Registry

A single registry module (`affiliate_commerce/registry.py`, not yet created) modeled directly on the existing, real, and already-proven `ai_capability/registry.py` (the "Technology Investment Council" pattern CLAUDE.md already documents): every named network gets a real entry with an explicit **status** field — `LIVE` (real credentials configured, real calls happening), `CONFIGURED` (real credentials present, not yet called), or `DISCOVERY` (no real credentials, no real account — honestly disclosed, never a fabricated "connected" state). Today, under this design, the registry would show: `amazon_associates: DISCOVERY` (real account not yet created by the founder — `affiliate_commerce/networks.py` already has the honest `amazon_associate_tag_configured()` check this would reuse) and all 19 other named networks (AliExpress, CJ Affiliate, Impact, Awin, Rakuten Advertising, ShareASale, eBay Partner Network, Temu Affiliate, Walmart Affiliate, Best Buy Affiliate, Fiverr Affiliates, Adobe, Microsoft, Apple Services, Booking.com, Expedia, Hostinger, Namecheap, Cloudflare, DigitalOcean) as `DISCOVERY` — zero real research has been done into any of their real application/approval processes yet. "Any future network through plugins" maps to a real, disclosed plugin contract: a new connector module implementing the interface below and self-registering, the same self-registration convention `channels/base_arm.py`'s real arms (`gumroad`/`etsy`/`payhip`/`paddle`) already use.

### 2. Unified connector interface

A real Python abstract base class, `AffiliateConnector` (not yet created), with exactly the 6 named methods as abstract methods:

```
SearchProducts(query, category=None) -> list[Product]
GenerateAffiliateLink(product_id) -> AffiliateLink
TrackClicks(product_id, referrer=None) -> ClickRecord
ImportCommissionReports() -> list[CommissionRecord]
ValidateProgramStatus() -> ProgramStatus   # real credentials present? real account approved?
UpdateCatalog() -> CatalogSyncResult
```

`affiliate_commerce/networks.py`/`click_tracking.py`/`products.py` (ADR-149, already real and built) map cleanly onto a first real implementation of this interface for Amazon: `GenerateAffiliateLink` = `build_amazon_url()`, `TrackClicks` = `record_click()`, `SearchProducts`/`UpdateCatalog` = today's static, disclosed-source `PRODUCTS` list (would need to become a real, credentialed Product Advertising API call to be honestly "production-ready" for search — not done yet, no real API key exists). `ImportCommissionReports` has no real implementation possible today — Amazon's real postback/reporting API requires the real approved account this factory doesn't have.

### 3. "Never hard-code platform logic into the core" principle

The core (registry + interface + Mission Control dashboard + intelligence layer) would depend only on the abstract `AffiliateConnector` contract, never on any specific network's real behavior — exactly the same discipline `channels/distributor.py` already applies to `gumroad`/`etsy`/`payhip`/`paddle` today. Each network's real logic (auth flow, real API shape, rate limits) lives entirely inside its own connector module. This is a real, already-proven architectural pattern in this codebase — the design risk here is not "can this pattern work," it's "19 of 20 networks have no real account to build a connector against yet."

### 4. Mission Control Affiliate Commerce dashboard

A dedicated panel (design only), field-mapped to real sources once they exist: Active networks → the registry's own `LIVE` count; Pending approvals → `ValidateProgramStatus()` results across all registered connectors; Daily clicks → `click_tracking.click_summary()`, already real and built, extended with a real date-bucketed view; EPC (earnings per click) → `real_commission / real_clicks`, honestly `Not enough data` until both sides are real and non-zero (never a fabricated estimate); Conversion rate → real conversions (from `ImportCommissionReports()`, once it exists for at least one network) over real clicks; Revenue / Commission awaiting payment → direct citations of `ImportCommissionReports()`'s real output; Broken links → a real periodic link-liveness check (not yet designed in detail — genuinely new monitoring, would reuse `resilience_monitor.py`'s existing incident-recording pattern rather than a second one); API health → each connector's `ValidateProgramStatus()`, surfaced the same way `GET /api/v1/health` already surfaces every other real service; Synchronization status → each connector's last real `UpdateCatalog()` run, same `generated_at`/`relTime()` convention every other Mission Control panel already uses.

### 5. Affiliate Intelligence layer

Per-product computed fields, each with an honest, disclosed real-vs-estimated source (the exact discipline `profit_oracle.opportunity_score()`'s `components_basis` dict already established, ADR-135):

| Field | Real source once available | Honest status today |
|---|---|---|
| Competition | Count of connectors returning the same/similar product | `Unknown` — needs 2+ live connectors |
| Estimated demand | Real search-volume signal, if a connector's network exposes one | `Unknown` — no connector exists |
| Commission percentage | Real, per-network published rate | `Unknown` — no real program terms on file |
| EPC | Real clicks vs. real conversions, per product | `Unknown` — needs real conversion data |
| Refund rate | Real, from `ImportCommissionReports()` if the network reports it | `Unknown` — most networks don't expose this; disclosed per-network |
| Price history | Real, time-series snapshot of `UpdateCatalog()` runs | `Unknown` — needs repeated real syncs over time |
| Product quality score | Real rating/rating_count, same weighted formula ADR-149's `products.py` already uses | Real and already built for the one live category |
| Merchant reputation | Real, if the network exposes seller ratings (mostly a marketplace-network concept — Amazon/eBay/AliExpress, not Adobe/Microsoft/Cloudflare) | `Unknown` — no connector exists |
| Country availability | Real, from each connector's own real catalog data | `Unknown` — no connector exists |

No dimension here would ever ship as a fabricated number — every one is designed from day one to report `Unknown`/`Not enough data` honestly until a real connector and real data exist, the same discipline `strategic_intelligence_core.py`'s `_NO_REAL_SOURCE_DIMENSIONS` already established for a different domain.

### 6. Cross-network product discovery ("search once, compare every network")

Architecturally: a fan-out call to every `LIVE` connector's `SearchProducts()`, a real merge/dedupe pass (by UPC/ASIN-equivalent where available, else a disclosed fuzzy-match heuristic), and a ranking by real expected return (`price * commission_pct * estimated conversion likelihood`, itself only as real as each of its inputs). With only one network ever real at a time under ADR-150's own gates, this fan-out has nothing to compare across until Phase 3 is reached — so this component is pure design today, not a partial build.

### 7. "Production-ready, no demo logic" applied honestly

The single hardest real tension in this directive, and the reason it was flagged before coding: a genuinely production-ready connector requires a real account, real credentials, and a real integration test against that network's real (usually sandboxed) API. For 19 of 20 named networks, none of that exists in this factory today. The honest resolution this architecture commits to: **a connector is either fully real (implements every one of the 6 interface methods against a real account) or it does not exist as code at all** — never a partial, credential-less stub pretending to be a connector. This is why the registry's `DISCOVERY` status (section 1) exists: to represent "known, wanted, not yet real" without writing a single line of connector code that can't actually do what it claims.

### 8. Scale ("tens of millions of products")

A real, disclosed infrastructure gap, not solved by this ADR: this factory's entire persistence layer today is flat JSON/JSONL files (`data/*.jsonl`, `finance_data.json`, `config/reality.json`) — appropriate for the real data volumes this factory has today (dozens to low hundreds of records per file) but not for tens of millions of product rows. Reaching that scale would require a real database decision (this factory has never made one — `lib/health_checks.js` already honestly reports `database: not_applicable` today) — explicitly out of scope for this ADR and for Phase 3/4 in general; the right time to make that decision is when a real second network's real catalog size actually approaches a volume flat files can't handle, not preemptively.

### 9. Knowledge Graph integration

`knowledge_graph/build.py` would gain new node types (`AffiliateNetwork`, `AffiliateProduct`, `AffiliateClick`/`AffiliateRevenue` events) following the exact same mechanical-parse-of-a-real-ledger discipline its existing `Decision`/`Outcome`/`Proposal`/`ExecutiveDirective` node types already use — real data only, parsed from `data/affiliate_clicks.jsonl` and (once real) a commission ledger. Not built — there is not yet enough real affiliate activity to make a graph of it meaningful (the existing Knowledge Graph already honestly reflects this factory's real state; an affiliate section with 0 real clicks and 0 real revenue would add graph nodes with no real information content).

### 10. Constitution compliance

Unchanged from ADR-149/150: no fake reviews, no fabricated ratings, no manipulative copy, full per-network ToS compliance — restated here as a standing constraint on every future phase of this architecture, same as ADR-150 already did for its own roadmap.

## What this ADR does NOT authorize

No code. No new Python module. No new network integration, including Amazon beyond what ADR-149 already built. No database migration. No Knowledge Graph schema change. No Mission Control panel. This ADR is a complete design reference for when ADR-150's real gates clear — not a build authorization.

## Re-trigger conditions (unchanged from ADR-150, restated for this fuller design)

- **Any Phase 3 work** (a second real network connector, the registry, the unified interface as real code): requires ADR-150's own gate — a real completed Amazon conversion confirmed via Amazon's postback, sustained real click-through data over a real multi-week window, and a real, live business reason to add a second specific network (not a preemptive "let's support 20").
- **The Mission Control Affiliate Commerce dashboard and Affiliate Intelligence layer**: only meaningful once there is real multi-network data to show — building either against a single real network (Amazon) would either duplicate the existing `affiliate-commerce-status` panel (ADR-149) or force fabricated fields (EPC/conversion rate with a sample size of zero). Revisit alongside Phase 3.
- **Any database/scale decision**: only when a real connector's real catalog size actually requires it — never provisioned ahead of real need.
- **Full re-opening of this directive**: either (a) ADR-150's Phase 3 gate clears naturally, or (b) the founder explicitly overrides these gates again for this specific initiative, as already happened once today for Phase 1 (ADR-149) — in a session that starts from that explicit instruction rather than rediscovering this same conflict fresh.
