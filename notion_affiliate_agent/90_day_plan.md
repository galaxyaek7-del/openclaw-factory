# 90-Day Phased Build & Content Plan — Notion Affiliate Agent (Notion for Lawyers / Solo Law Firms)

**Niche:** Notion for Lawyers / Solo Law Firms (selected 2026-05-13, strongest evidence bundle)
**Status:** DRAFT — AWAITING FOUNDER REVIEW
**Disclosure:** Every content piece includes "This content contains affiliate links"
**Revenue expectation:** Near-$0 in months 1-3 (honest, no inflated projections) — affiliate traffic takes 60-90 days to index and convert; gradual growth only after consistent publishing + Founder personal input

---

## Phase 1 — Weeks 1-4: Foundation + First Drafts

**Goal:** Databases live, pipeline proven, first 4 drafts ready for Founder review

- **Week 1:**
  - Founder reviews this 90-day plan and confirms Niche #1
  - Founder creates Notion internal integration and runs `notion_affiliate_agent/create_databases.py` (or approves local_store.json as interim) — Product Tracker, Content Calendar, Performance Tracker created
  - Populate Product Tracker: Notion, Notion AI, Notion Calendar, Clio, MyCase (already in local_store.json)
  - Milestone: databases created, Founder can see them in Notion

- **Week 2:**
  - n8n blueprint reviewed (`n8n_blueprint.json`) — Founder decides to import or keep Manual Trigger
  - Content pipeline tested: 4 drafts already generated in `notion_affiliate_agent/drafts/` (Review, Comparison, Guide, Template for solo law firms) — Founder reviews each for NEEDS FOUNDER PERSONAL INPUT flags
  - Milestone: 4 drafts exist at `notion_affiliate_agent/drafts/*.md` + local_store content_calendar Status="Draft Ready"

- **Week 3:**
  - Founder adds personal input at flagged spots (client intake pain points, small-firm insight) — at least 2-3 sentences per draft where flagged
  - Founder approves or rejects each draft (Status → Founder Approved or back to Draft Ready)
  - No publishing yet
  - Milestone: 0-4 drafts Founder Approved (honest: 0 is fine, Founder decides quality bar)

- **Week 4:**
  - If any draft Founder Approved: Founder manually publishes 1 draft to chosen platform (Blog) — manual, no automation
  - Log publish date in Content Calendar, create Performance Tracker entry with Status="Pending Check", Check Date = publish + 7 days
  - Milestone: 0-1 published (Founder manual), 0 clicks/conversions expected

**Revenue Month 1:** $0 (honest: 0-1 manual publish, 0 clicks, Cuelinks not yet approved or no traffic)

---

## Phase 2 — Weeks 5-8: Consistent Draft Production

**Goal:** 4 more drafts (2 reviews/comparisons, 2 guides/templates) + first performance check

- **Week 5:** New calendar entry → n8n/manual generates draft → Founder review (same pipeline) — 1 draft
- **Week 6:** Same — 1 draft + first 7-day performance check for Week 4 publish (Founder manually checks Cuelinks dashboard, enters clicks/conversions/commission into Performance Tracker, Status→Checked)
- **Week 7:** Same — 1 draft
- **Week 8:** Same — 1 draft + second performance check if Week 5 published
  - Milestone: total 8 drafts, 1-2 published (if Founder chose), 1-2 performance checks with real data (likely 0 clicks, honest)

**Revenue Month 2:** $0 (honest: 1-2 published, indexing, maybe 1-5 clicks, 0 conversions)

---

## Phase 3 — Weeks 9-12: Optimization + Pipeline Hardening

**Goal:** 4 more drafts + performance pattern review + decide to continue or pivot to backup niche

- **Week 9:** Same — 1 draft
- **Week 10:** Same — 1 draft + performance checks
- **Week 11:** Review Performance Tracker: which content type got clicks? Which platform? If 0 clicks across all, consider SEO/title adjustment or backup niche #2 (Notion for Construction) per micro_niches.md
- **Week 12:** Same — 1 draft + produce Phase 1 performance summary (honest: likely 0-$5 commission)
  - Milestone: total 12 drafts, 3-4 published, 3-4 performance checks

**Revenue Month 3:** $0-5 (honest: maybe 1 conversion if traffic exists, but near-$0 is correct expectation)

---

## Phase 4 — Beyond 90 Days (Gradual Growth, Not Included in Current Build)

- **Month 4-6:** If 1-2 conversions observed, scale to 2 drafts/week; if 0 conversions, Founder decides: continue Niche #1, pivot to Niche #2 (construction, proven $49/$149 pricing), or pause
- **No inflated projection:** Even with consistent publishing, affiliate revenue for a new site is typically $10-50/month in months 4-6, not hundreds — honest, not inflated

---

## Weekly Milestone Summary

| Week | Concrete Milestone | Revenue Expectation |
|------|-------------------|---------------------|
| 1 | Databases created | $0 |
| 2 | 4 drafts ready | $0 |
| 3 | Founder personal input added | $0 |
| 4 | 0-1 manual publish | $0 |
| 5-8 | +4 drafts, 1-2 performance checks | $0 |
| 9-12 | +4 drafts, 1-2 checks, summary | $0-5 |

**Total 90 days: 12 drafts, 3-4 manual publishes (if Founder approves), 3-4 performance checks, near-$0 revenue — honest, not inflated.**

---

## What Needs Founder Action Per Week

- **Every week:** Review drafts at flagged NEEDS FOUNDER PERSONAL INPUT spots (5 min per draft), approve/reject
- **Week 4, 6, 8, 10, 12:** If approved, manually publish 1 draft to Blog (human, not n8n)
- **Week 6, 8, 10, 12:** Manually check Cuelinks dashboard 7 days post-publish, enter clicks/conversions/commission into Performance Tracker
- **Week 11:** Decide to continue Niche #1 or pivot to backup

**No Founder action = no publish, no performance data — pipeline stays at Draft Ready.**

---

## Existing Infrastructure Reused

- **Notion:** local_store.json (no new API until Founder provides NOTION_API_KEY)
- **GROQ:** ai_capability/orchestrator.py (existing groq-sdk, no duplication)
- **n8n:** http://localhost:5678 (existing instance, blueprint not yet imported — Founder reviews first)
- **Telegram:** lib/telegram_direct.js (existing, for Founder notification)
- **Affiliate:** affiliate_commerce/ (existing Cuelinks handling, no duplication)

**No new infrastructure created beyond the 3 databases, pipeline, and blueprint already built.**

