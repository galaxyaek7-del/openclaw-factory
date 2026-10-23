# Distribution: gaps and risks

| ID | Gap or risk | Severity | Effect | Treatment / owner |
|---|---|---|---|---|
| D-G1 | No platform can post through an API (no transports; LinkedIn/TikTok/Instagram unconnected; X needs paid credits) | High | every post is manual | founder: app/credentials per platform, or post by hand from hand-off files |
| D-G2 | No rendered images for Instagram, no product videos for TikTok | High | 0 of 87 drafts usable on those platforms | engineering: render carousel JPEGs and per-product videos with `video_studio` |
| D-G3 | Social metrics have no source (no platform analytics access) | High | reach and engagement UNKNOWN | connect read APIs when apps exist; until then only Gumroad sales referrers |
| D-G4 | Public site visits unmeasured | High | clicks from posts to site pages cannot be counted | founder: free analytics choice |
| D-G5 | Demand evidence absent for every offer | Medium | prioritization runs on clarity, measurability and rotation, not demand | record real signals as they appear |
| D-G6 | Not wired into the factory loop | Low | cycles run by hand | add a weekly step after a review cadence is agreed |
| D-R1 | 13 public guide pages print "UNKNOWN -- not captured at this granularity..." in their meta description, subtitle and fact rows | High (public quality, SEO) | those guides blocked from campaigns | source: `commission_engine.py` line 108 constant; the parallel session has uncommitted edits to it and to the 13 pages; to be fixed there |
| D-R2 | The same uncommitted parallel edits remove `og:image`, `og:description`, `canonical` and `twitter:card` tags from those pages | Medium | SEO and link-preview regression if pushed | flag to the parallel session before it commits |
| D-R3 | Two product pages are stale: they say "not yet listed"/"proposed" though the products are live (GR-2562d0b4d2, GR-41d87224ab) | Medium | wrong public information | update the pages (site-only change) |
| D-R4 | `decision_engine/distribution_engine.py` (untracked, parallel) tests write fixtures such as `PRD-001`/`asset1.pdf` into the production file `data/distribution_events.jsonl` | Medium | contaminated operational data | parallel session: isolate its tests |
| D-R5 | Publication approval is a recorded approval, not a single-use token | Low | weaker than the upload scope | same doctrine as video: `write_scope` refuses to scope publication |
| D-R6 | Hand-posted jobs cannot be verified (no read-back) | Medium | "posted" stays unverified | verify once a read API exists |
| D-R7 | The shared engine's "Need ...?" video hook is clumsy for imperative descriptions | Low | other callers still get it | kept for compatibility (a test pins it); this engine writes its own hook |
| D-R8 | X posting cost with links (about $0.20) would make API posting the most expensive channel | Medium | spend | stay manual unless the founder authorizes spend |
| D-R9 | Platform policies (spam, automation, repetitive content) | Medium | account restrictions | one post per offer per platform per 30 days (rotation), no engagement automation, no bulk messages |
