# Children's channel: YouTube upload pipeline (2026-10-30)

Production, checks and upload run on their own; the two things only the founder can give are the
YouTube credentials and, per episode, an approval stating that the child-safety and Arabic reviews were done.

## What runs automatically
Every loop tick (`factory_loop.js`, step `kids_youtube_publish`) runs `scripts/kids_youtube_publish_daily.py --once`:

1. For each episode in `episodes.json`, `preflight.py` checks:
   - the video file;
   - its verification record (all checks true, same file size);
   - the subtitles (`tools/check_subtitles.py`);
   - the rights ledger (every asset cleared, or declared not in this cut);
   - the metadata: title and description limits, no links, made for kids, Arabic;
   - a founder approval bound to the file's sha256;
   - that the file was not uploaded before;
   - the credentials.
2. An episode that passes everything is uploaded through `youtube_publisher.py`:
   - YouTube Data API `videos.insert`, marked **made for kids**, with the privacy chosen in the approval;
   - then the Arabic subtitle track is added (`captions.insert`).
   - At most one upload per tick.
3. The write gate is checked before any network call. Uploads need `GF_ALLOW_KIDS_VIDEO_UPLOAD=true` (or
   `FACTORY_LIVE_PUBLISH=true`). The narrow switch opens nothing else.
4. Each result goes to `data/youtube_uploads.jsonl` (git-ignored): video id, privacy, captions. A failed
   upload is recorded and tried again on the next tick; an uploaded file is never uploaded twice.

Check what blocks each episode at any time: `python scripts/kids_youtube_publish_daily.py --status`.

## What the founder does once
1. In Google Cloud Console, signed in as the account that owns the channel:
   - create a project;
   - enable **YouTube Data API v3**;
   - set up the OAuth consent screen;
   - create an OAuth client ID of type **Desktop app**, and download its JSON.
2. Run `python scripts/youtube_oauth_setup.py path/to/client_secret.json`. It opens Google's consent page,
   receives the code on a one-time listener bound to 127.0.0.1, and writes the three `YOUTUBE_*` values into
   `.env` without printing them.
3. Add `GF_ALLOW_KIDS_VIDEO_UPLOAD=true` to `.env` and restart the loop (`scripts/supervisor.js` restarts it on
   exit).

## What the founder does per episode
After watching it and having the Arabic checked:

```
python scripts/approve_kids_episode.py --episode ep01_nunu_little_bridge --privacy unlisted --child-safety-reviewed --arabic-reviewed
```

The approval is bound to the exact video file and expires after 14 days (`--days` to change). If the video is
rebuilt, approve it again. The next loop tick uploads it.

## Facts this rests on (read 2026-10-30)
- **Quota:** an upload costs 1 unit of a separate 100-uploads-per-day quota ([videos.insert](https://developers.google.com/youtube/v3/docs/videos/insert), [quota](https://developers.google.com/youtube/v3/getting-started)).
- **Unverified projects:** the current reference says uploads from unverified API projects are **not** restricted to private viewing.
  - An older revision-history entry (28 July 2020) and Help Center article say the opposite. Google's reply in October 2026 (issue [572863050](https://issuetracker.google.com/issues/572863050)) confirms the current reading.
  - If YouTube still locks the first upload as private, the channel owner gets an email, and the fix is the [API audit form](https://support.google.com/youtube/contact/yt_api_form).
- **YouTube Kids:** there is no separate upload. A video uploaded to YouTube and marked made for kids may appear in the YouTube Kids app as YouTube decides; this pipeline cannot guarantee that.
- **What made for kids switches off:** personalised ads, comments, and some features such as notifications and end screens.

## What the episodes are today
Both cuts are **animatics**: primitive 3D, music and sound, Arabic subtitles, **no voices**. Their manifest
approvals (story, child safety, founder) are still PENDING. The preflight passes everything except the approval
and the credentials.
