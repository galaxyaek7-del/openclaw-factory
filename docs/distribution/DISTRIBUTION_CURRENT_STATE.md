# Distribution: current state (verified 2026-10-23)

## What already existed

| Piece | State | Evidence |
|---|---|---|
| `content_generation/repurposing_engine.py` | Real, deterministic copy for 8 channels (no LLM, no invented facts) | tracked, 19 tests |
| `distribution_os.py` | Read-only cross-channel read model for sales channels | tracked, tests |
| `commercial_operations.distribution_capability_matrix()` | Per-channel labels (social = content automated, human-gated publishing) | tracked |
| `channels/x_arm.py`, `channels/x_verify.py` | X adapter behind the write gate; credential read check | tracked |
| X credentials | Present in `.env`; read OK; a post attempt returned HTTP 402 "credits depleted" | `data/channel_x_assessment.json`, `data/x_post_queue.json` |
| LinkedIn | `channels/linkedin_publisher.py` exists only as an untracked file of a parallel session; no `LINKEDIN_*` credentials | file header, `.env` names |
| TikTok, Instagram | No code, no credentials | repository search |
| `product_registry.py` | 92 Gumroad products, 89 verified live, 0 sales | `data/product_registry.json` |
| Public site | 86 pages on GitHub Pages; visits unmeasured (no beacon receiver) | `docs/factory` baseline |
| Social posts ever published | None found | no ledger records any |

Untracked parallel-session work, not used here: `channels/distribution_engine.py`, `channels/distribution_state_machine.py`, `channels/capability_matrix.py`, `decision_engine/distribution_engine.py`.

## What exists after this mandate

- `social_distribution/`: cross-arm offer registry, platform declarations and readiness, platform-native drafts with content QA, tracked links, a resumable campaign job ledger with gated adapters and manual hand-off, prioritization, and a dashboard.
- 173 offers across 5 arms, each with an evidence-based eligibility: 137 eligible, 7 need review, 29 not eligible.
- 24 drafts for 8 offers from 3 arms: 16 passed QA and await founder approval; 8 are blocked for real reasons (no rendered images or video, video rights unresolved).
- 33 tests.

## Truth line

Posts published: 0. Platform connections able to post: 0. Social traffic, engagement, leads, sales, commissions: ZERO VERIFIED (nothing measured yet).
