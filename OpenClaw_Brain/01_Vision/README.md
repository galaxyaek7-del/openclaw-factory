# 01 — Vision

## Identity

OpenClaw Factory is not a book factory. Per [CLAUDE.md](../../CLAUDE.md): it is a multi-product digital production platform, built to switch instantly between product tracks so the business survives any single platform or product line dying.

## The Six Planned Tracks

| # | Track | Platforms | Status |
|---|---|---|---|
| 1 | Digital books | Amazon KDP | **Active** — the only track built so far |
| 2 | Ready-made templates | Etsy, Gumroad | Not started |
| 3 | Digital art | Etsy, Society6, Redbubble | Not started |
| 4 | Apps & digital tools | App stores, Web | Not started |
| 5 | Business services | VIP subscriptions | Not started |
| 6 | International trade platform | Cars, wholesale goods | Not started |

## The Golden Rules (CLAUDE.md, verbatim principle, not paraphrased)

- **Do not expand to a new product before the first dollar from the current product.** This is why tracks 2–6 are untouched — track 1 hasn't proven profitable yet (see [15_Finance](../15_Finance/): $0 revenue recorded to date).
- Every new engine must follow the same interface as the existing `book_engine`.
- Security: everything local, API keys in `.env` only, no cloud.
- Content: every agent must be easily transferable between tracks.

## North Star (OPENCLAW_OS_CONSTITUTION.md)

> "Become the world's most intelligent, secure, trusted and continuously evolving digital company for creating digital value."

## What this means in practice today

Every build decision this project has made — Quality Council gates, the Butter Principle's $30 floor, the circuit breaker, this very Brain — exists in service of *one* track (`book_engine`) proving itself before any of the other five are touched. See [02_Roadmap](../02_Roadmap/) for what "proving itself" concretely requires next.
