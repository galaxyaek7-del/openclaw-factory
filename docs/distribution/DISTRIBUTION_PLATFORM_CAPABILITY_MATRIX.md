# Distribution: platform capability matrix

Declarations live in `social_distribution/platforms.py`; readiness is computed from credential names present on this machine and recorded evidence. Requirements checked against documentation on 2026-10-23; third-party figures are marked.

| | LinkedIn | TikTok | Instagram | X |
|---|---|---|---|---|
| Formats | text, text with link, image, document | vertical video, photo | image, carousel, Reel | text, thread, image |
| Account | member profile (pages need org permissions) | TikTok account | professional (Business/Creator) | account with developer app |
| Permission | `w_member_social` via "Share on LinkedIn" | `video.publish` / `video.upload` | content publishing permission on a Meta app | OAuth 1.0a user write |
| Big constraint | 60-day member token | unaudited apps post SELF_ONLY (private) until audited | JPEG only, fetched from a public URL; 100 posts / 24 h | pay-per-use writes |
| Text limit | 3,000 | caption 2,200 | caption 2,200, links not clickable | 280, links count 23 |
| Scheduling | ours | ours | ours | ours |
| Verification | read post id back | publish status by id | media id and permalink | GET post id |
| Cost | free API | free API; audit takes weeks (third-party estimate) | free API | about $0.015 per post, about $0.20 with a link (third-party summaries of docs.x.com) |
| **State here** | NOT_CONNECTED | NOT_CONNECTED | NOT_CONNECTED | BLOCKED_SPEND (credentials work for reading; a post returned 402 credits depleted) |
| **What can be automated today** | drafts, QA, tracked links, hand-off files | scripts and scene plans; video only where rendered and cleared | captions and slide plans | drafts, QA, hand-off files |
| **Needs a person** | create app and token, or post by hand | app + audit, or upload by hand | professional account + Meta app + image hosting, or post by hand | buy credits (spend not authorized) or post by hand in the app (free) |

Posting by hand from each app costs nothing and needs no API; that is the zero-spend path the engine prepares for (hand-off files).

Sources: [LinkedIn Share on LinkedIn](https://developer.linkedin.com/documents/share-api), [Microsoft Learn: Share on LinkedIn](https://learn.microsoft.com/linkedin/consumer/integrations/self-serve/share-on-linkedin), [TikTok Direct Post](https://developers.tiktok.com/doc/content-posting-api-reference-direct-post), [TikTok Content Posting get started](https://developers.tiktok.com/docs/en/content-posting-api-get-started), [Postiz TikTok notes](https://docs.postiz.com/providers/tiktok.md), [Meta content publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing), [Postproxy X pricing 2026](https://postproxy.dev/blog/x-api-pricing-2026), [MediaNama X pay-per-use](https://www.medianama.com/2026/02/223-x-developer-api-pricing-pay-per-use-model/).
