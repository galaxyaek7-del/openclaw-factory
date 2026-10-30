#!/usr/bin/env python3
"""Upload one approved children's episode to YouTube (Data API v3).

Live writes go through channels/write_gate.require_platform_write with the
narrow kids_video switch (GF_ALLOW_KIDS_VIDEO_UPLOAD, or FACTORY_LIVE_PUBLISH),
checked before any network call. The caller (scripts/kids_youtube_publish_daily.py)
has already run kids_studio/publishing/preflight.py.

Calls, as documented by Google (read 2026-10-30):
  POST https://oauth2.googleapis.com/token              refresh token -> access token
  POST https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status
       then PUT the file to the session URL             (videos.insert, 1 unit of the upload quota)
  POST https://www.googleapis.com/upload/youtube/v3/captions?uploadType=multipart&part=snippet
                                                        (captions.insert, the Arabic SRT)

The video is marked status.selfDeclaredMadeForKids = true. Tokens are never
printed or logged. HTTP is injectable for tests.
"""
import json
import sys
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from channels.write_gate import require_platform_write  # noqa: E402

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
CAPTION_URL = "https://www.googleapis.com/upload/youtube/v3/captions?uploadType=multipart&part=snippet"


class UploadFailed(RuntimeError):
    pass


def _http(method, url, *, headers=None, data=None, timeout=600):
    """(status, headers, body bytes). Never raises on HTTP status."""
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read()


def access_token(client_id, client_secret, refresh_token, http=_http):
    body = urllib.parse.urlencode({"client_id": client_id, "client_secret": client_secret,
                                   "refresh_token": refresh_token, "grant_type": "refresh_token"}).encode()
    status, _, raw = http("POST", TOKEN_URL, headers={"Content-Type": "application/x-www-form-urlencoded"}, data=body)
    try:
        doc = json.loads(raw or b"{}")
    except ValueError:
        doc = {}
    if status != 200 or not doc.get("access_token"):
        raise UploadFailed("token refresh failed: HTTP %s %s" % (status, doc.get("error", "")))
    return doc["access_token"]


def video_resource(ep, defaults, privacy):
    return {
        "snippet": {"title": ep["title"], "description": ep["description"], "tags": ep.get("tags", []),
                    "categoryId": defaults.get("category_id", "1"),
                    "defaultLanguage": defaults.get("default_language", "ar"),
                    "defaultAudioLanguage": defaults.get("default_audio_language", "ar")},
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": True,
                   "containsSyntheticMedia": bool(defaults.get("contains_synthetic_media", False)),
                   "license": defaults.get("license", "youtube"),
                   "embeddable": bool(defaults.get("embeddable", True))},
    }


def upload(ep, defaults, privacy, video_path, srt_path, creds, http=_http):
    """Upload the video, then its Arabic captions. Returns {video_id, captions}."""
    require_platform_write("youtube", "videos.insert", kids_video=True)
    token = access_token(creds["YOUTUBE_CLIENT_ID"], creds["YOUTUBE_CLIENT_SECRET"], creds["YOUTUBE_REFRESH_TOKEN"], http)
    data = Path(video_path).read_bytes()
    meta = json.dumps(video_resource(ep, defaults, privacy), ensure_ascii=False).encode("utf-8")
    status, headers, raw = http("POST", UPLOAD_URL, data=meta, headers={
        "Authorization": "Bearer " + token, "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(len(data))})
    session = {k.lower(): v for k, v in (headers or {}).items()}.get("location")
    if status != 200 or not session:
        raise UploadFailed("could not open an upload session: HTTP %s %s" % (status, (raw or b"")[:200]))
    status, _, raw = http("PUT", session, data=data, headers={"Content-Type": "video/mp4"})
    try:
        video = json.loads(raw or b"{}")
    except ValueError:
        video = {}
    if status not in (200, 201) or not video.get("id"):
        raise UploadFailed("upload did not complete: HTTP %s" % status)
    caption = "NOT_ATTEMPTED"
    if srt_path and Path(srt_path).is_file():
        caption = upload_captions(video["id"], srt_path, token, http)
    return {"video_id": video["id"], "privacy": video.get("status", {}).get("privacyStatus", privacy),
            "made_for_kids": video.get("status", {}).get("madeForKids"), "captions": caption}


def upload_captions(video_id, srt_path, token, http=_http):
    require_platform_write("youtube", "captions.insert", kids_video=True)
    boundary = "gf-" + uuid.uuid4().hex
    meta = json.dumps({"snippet": {"videoId": video_id, "language": "ar", "name": "العربية", "isDraft": False}},
                      ensure_ascii=False).encode("utf-8")
    srt = Path(srt_path).read_bytes()
    body = (b"--" + boundary.encode() + b"\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n" + meta +
            b"\r\n--" + boundary.encode() + b"\r\nContent-Type: application/octet-stream\r\n\r\n" + srt +
            b"\r\n--" + boundary.encode() + b"--\r\n")
    status, _, _ = http("POST", CAPTION_URL, data=body, headers={
        "Authorization": "Bearer " + token, "Content-Type": "multipart/related; boundary=" + boundary})
    return "UPLOADED" if status in (200, 201) else "FAILED (HTTP %s)" % status
