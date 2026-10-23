# Video factory: rights and policy checklist

Per-video rights manifests: `video_studio/projects/<id>.rights.json`. `youtube_upload.request_upload` refuses any job whose status is not `CLEARED`.

## Rights (both pilots)

| Asset | Source | Status |
|---|---|---|
| Script | original, written for Galaxy Forge (AI-assisted) | OWNED_ORIGINAL |
| Voice | Microsoft Zira Desktop (Windows System.Speech) | UNRESOLVED: commercial video use not confirmed |
| Fonts | Segoe UI, Consolas (Windows) rendered to pixels | UNRESOLVED: replace with OFL fonts |
| Graphics | drawn by code | OWNED_ORIGINAL |
| Music, footage, images | none | NOT_APPLICABLE |
| Trademarks | only "Galaxy Forge" | OWNED_ORIGINAL |
| People depicted | none | NOT_APPLICABLE |

## Platform policy (sources checked 2026-10-23, secondary coverage; confirm on YouTube's own help pages before publishing)

| Topic | What applies | Our handling |
|---|---|---|
| Altered or synthetic content disclosure | Required for realistic content a viewer could mistake for real people, places or events; productivity uses and unrealistic content are exempt; finance is listed among sensitive topics that can get a more prominent label | metadata field `contains_synthetic_media` must be set explicitly; set true for the synthetic voice |
| Inauthentic (formerly "repetitious") content, YouTube Partner Program, from 15 July 2025 | Mass-produced or repetitive content is not eligible for monetization; it is not banned from the platform; AI use itself remains eligible when there is original value | each video built around a real worked example; no batch generation of near-identical videos; this is risk V5 |
| Made for kids | Must be declared at upload | metadata field required; pilots: false |
| Financial content | Educational framing, no promises | pilot B states "education, not financial advice" |
| Metadata | Title up to 100 characters, description up to 5,000 bytes, no `<` or `>` | enforced by `validate_metadata` |

Sources: [MediaPost](https://www.mediapost.com/publications/article/391062/youtube-requires-creators-to-label-altered-synthe.html), [NBC News](https://www.nbcnews.com/tech/tech-news/youtube-says-will-require-creators-label-ai-content-rcna143937), [Social Media Today](https://www.socialmediatoday.com/news/youtube-clarifies-monetization-update-inauthentic-repeated-content/752892/), [Plagiarism Today](https://www.plagiarismtoday.com/2025/07/08/youtube-targets-inauthentic-content/), [Gulf News](https://gulfnews.com/technology/youtube-updates-monetisation-policies-ai-and-repetitive-content-ban-begins-july-15-1.500192660).

## Secrets

The YouTube module holds no credentials; error text is redacted for token-like strings before it reaches the ledger (tested). No OAuth client exists.
