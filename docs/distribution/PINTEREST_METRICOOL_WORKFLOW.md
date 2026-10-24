# Pinterest through Metricool: workflow and status (2026-10-24)

## Status: HOLD (needs a Pinterest board)

| Item | State | Class |
|---|---|---|
| Metricool brand 6965613 (`galaxyaek7`), Pinterest `galaxyaek7` and TikTok `aekgalaxy8` linked | connected | OBSERVED (getBrandSettings) |
| Claude Code permission for `createScheduledPostForReview` | `ask` rule; direct-publish tools stay denied | OBSERVED (`.claude/settings.local.json`) |
| Connector tools for boards (list or create) | none exist | OBSERVED (session tool list) |
| Pinterest boards on the account | 4; readable: family-home-cooking, islamic-quotes, plats | OBSERVED (public profile, read twice) |
| A board suited to business-finance products | none | DERIVED |
| Posts created in Metricool | none | OBSERVED (getScheduledPosts empty after each attempt) |
| Account looks personal (cooking, quotes) | | INFERRED |

## Required payload (learned from Metricool's own validation errors)

`createScheduledPostForReview(blogId, date, info, reviewers, approvalSystem, notify)` where `info` holds `text`, `providers[{network: "pinterest"}]`, `media[url]`, `autoPublish`, `publicationDate {dateTime local, timezone IANA}` and `pinterestData {boardId, pinTitle, pinLink}`. Attempt 1 failed on `publicationDate`, attempt 2 on `boardId`; neither created a post.

## Code

`social_distribution/metricool.py`:
- `build_pinterest_review_post()` returns the exact call arguments or refuses with every reason: board id not a real Pinterest id, time not in the future or not local, unknown zone, wrong or unconnected brand, no cover image, offer not eligible, title/text too long, an amount that is not the price, a bad tracked link, or `approvalSystem: "optional"` (auto-publish) unless explicitly allowed **and** the factory write gate is open.
- `duplicate_of()` checks Metricool's scheduled list and the local record before any submission.
- `record_attempt()` appends every submission attempt (created or not, with how that was verified) to `data/metricool_submissions.jsonl`.
Tests: `tests/test_metricool_payload.py` (9).

## Procedure for each post

1. Build the call with `build_pinterest_review_post()` (approval `any`).
2. `getScheduledPosts` for the brand and period; stop if `duplicate_of()` finds one.
3. Call `createScheduledPostForReview` once; Claude Code asks the founder first (ask rule).
4. Whatever the response, read `getScheduledPosts` again and `record_attempt()` with the result.
5. A post counts as created only when it appears in that read-back; as published only when Pinterest shows it after the founder approves it in Metricool.
6. Never retry before step 4 shows that nothing was created.

## Founder decision needed

Create a board for the products (suggested name: **Small Business Finance Tools**) on the linked Pinterest account, or, better for the long term, a separate Pinterest business account for Galaxy Forge linked to the same Metricool brand. Then tell me; the board id is read from the board's public data, never typed by hand.

## Creative note

Gumroad covers are 16:9 (1005x565 at the public URL); Pinterest favours 2:3 portrait images. The cover is accepted as is; a 1000x1500 pin image would be a later improvement.
