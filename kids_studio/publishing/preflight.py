#!/usr/bin/env python3
"""Upload preflight for one children's episode (2026-10-30).

Every check must PASS before scripts/kids_youtube_publish_daily.py may upload.
Nothing here touches the network or writes anything.

  video          the file exists and is a non-trivial MP4
  verify         verify_video.py's record: every check true, file size and
                 duration consistent with the file being uploaded
  subtitles      kids_studio/tools/check_subtitles.py passes (no errors)
  rights         every asset in the rights ledger is usable, except ones the
                 episode declares as not in this cut (with a reason)
  metadata       title <= 100 chars, description <= 5000, no < or >, no links,
                 tags <= 500 chars in total, made for kids, Arabic language
  approval       a founder approval for this episode bound to the video's
                 sha256, with child-safety and Arabic review recorded, a
                 privacy setting, and not expired
  not_uploaded   this exact file is not already in the upload ledger
  credentials    the YouTube OAuth variables exist (values never read here)

Approvals live in data/kids_upload_approvals.json (git-ignored):
  {"approvals": [{"episode": "...", "video_sha256": "...", "privacy": "public|unlisted|private",
                  "child_safety_reviewed": true, "arabic_reviewed": true,
                  "approved_by": "founder", "approved_at": "ISO", "expires_at": "ISO"}]}
"""
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kids_studio" / "tools"))
import check_subtitles  # noqa: E402

REGISTRY = ROOT / "kids_studio" / "publishing" / "episodes.json"
APPROVALS = ROOT / "data" / "kids_upload_approvals.json"
LEDGER = ROOT / "data" / "youtube_uploads.jsonl"
CREDENTIAL_VARS = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
PRIVACY = ("public", "unlisted", "private")
LINK = re.compile(r"https?://|www\.", re.I)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _ts(v):
    try:
        t = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def load_registry(path=REGISTRY):
    doc = _json(path, {})
    return doc.get("channel_defaults", {}), doc.get("episodes", [])


def uploaded_hashes(ledger=LEDGER):
    out = set()
    try:
        for line in Path(ledger).read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("status") == "UPLOADED" and rec.get("video_sha256"):
                out.add(rec["video_sha256"])
    except OSError:
        pass
    return out


def find_approval(episode, digest, approvals_path=APPROVALS):
    doc = _json(approvals_path, {}) or {}
    for a in doc.get("approvals", []):
        if a.get("episode") == episode and a.get("video_sha256") == digest:
            return a
    return None


def check(ep, defaults, *, root=ROOT, approvals_path=APPROVALS, ledger=LEDGER, env=None, now=None):
    """{name: {"status": PASS|FAIL, "detail": str}} plus the video digest."""
    env = os.environ if env is None else env
    now = now or datetime.now(timezone.utc)
    res = {}

    def put(name, ok, detail):
        res[name] = {"status": "PASS" if ok else "FAIL", "detail": detail}

    video = Path(root) / ep["video"]
    digest = None
    if video.is_file() and video.stat().st_size > 100_000 and video.suffix.lower() == ".mp4":
        digest = sha256(video)
        put("video", True, "%s, %d bytes" % (ep["video"], video.stat().st_size))
    else:
        put("video", False, "missing or not a real MP4: %s" % ep["video"])

    v = _json(Path(root) / ep["verify"])
    if not v:
        put("verify", False, "no verification record %s" % ep["verify"])
    else:
        failed = [k for k, ok in (v.get("checks") or {}).items() if ok is not True]
        size_ok = video.is_file() and v.get("bytes") == video.stat().st_size
        ok = bool(v.get("checks")) and not failed and size_ok
        put("verify", ok, "all %d checks true, size matches" % len(v["checks"]) if ok else
            "failed checks %s; record size %s vs file %s" % (failed, v.get("bytes"),
                                                            video.stat().st_size if video.is_file() else None))

    srt = Path(root) / ep["subtitles"]
    if srt.is_file() and v:
        s = check_subtitles.check(srt.read_text(encoding="utf-8-sig"), v.get("container_duration_s"))
        put("subtitles", s["passed"], "%d cues, %d warnings" % (s["cues"], s["warnings"]) if s["passed"]
            else "; ".join(i["issue"] for i in s["issues"] if i["severity"] == "error")[:300])
    else:
        put("subtitles", False, "subtitle file or verification record missing")

    led = _json(Path(root) / ep["rights_ledger"], {}) or {}
    excluded = ep.get("not_in_this_cut") or {}
    bad = [a.get("id") for a in led.get("assets", []) if a.get("usable") is not True and a.get("id") not in excluded]
    put("rights", bool(led.get("assets")) and not bad,
        "every asset cleared (%d excluded from this cut: %s)" % (len(excluded), ", ".join(excluded)) if not bad
        else "not cleared: %s" % ", ".join(map(str, bad)))

    title, desc, tags = ep.get("title", ""), ep.get("description", ""), ep.get("tags", [])
    probs = []
    if not title or len(title) > 100:
        probs.append("title must be 1-100 characters")
    if len(desc) > 5000:
        probs.append("description over 5000 characters")
    if any(c in title + desc + "".join(tags) for c in "<>"):
        probs.append("< or > is rejected by YouTube")
    if LINK.search(desc):
        probs.append("no links in a children's description")
    if sum(len(t) + (2 if " " in t else 0) for t in tags) + max(0, len(tags) - 1) > 500:
        probs.append("tags over 500 characters")
    if defaults.get("made_for_kids") is not True:
        probs.append("made_for_kids must be true")
    put("metadata", not probs, "ok" if not probs else "; ".join(probs))

    appr = find_approval(ep["episode"], digest, approvals_path) if digest else None
    if not appr:
        put("approval", False, "no founder approval bound to this exact file (sha256 %s)" % (digest or "unknown"))
    else:
        exp = _ts(appr.get("expires_at"))
        missing = [k for k in ("child_safety_reviewed", "arabic_reviewed") if appr.get(k) is not True]
        why = []
        if missing:
            why.append("not recorded as reviewed: %s" % ", ".join(missing))
        if appr.get("privacy") not in PRIVACY:
            why.append("privacy must be one of %s" % ", ".join(PRIVACY))
        if not exp or now >= exp:
            why.append("approval expired or has no expiry")
        put("approval", not why, "approved by %s, privacy %s, expires %s" % (appr.get("approved_by"),
            appr.get("privacy"), appr.get("expires_at")) if not why else "; ".join(why))

    put("not_uploaded", digest is not None and digest not in uploaded_hashes(ledger),
        "not uploaded yet" if digest and digest not in uploaded_hashes(ledger) else "already uploaded or unreadable")

    absent = [k for k in CREDENTIAL_VARS if not str(env.get(k, "")).strip()]
    put("credentials", not absent, "present" if not absent else "missing: %s" % ", ".join(absent))
    return res, digest


def summary(results):
    return {"passed": all(r["status"] == "PASS" for r in results.values()),
            "failing": [k for k, r in results.items() if r["status"] != "PASS"]}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    defaults, eps = load_registry()
    out = []
    for ep in eps:
        if argv and ep["episode"] not in argv:
            continue
        res, digest = check(ep, defaults)
        out.append({"episode": ep["episode"], "video_sha256": digest, **summary(res), "checks": res})
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
