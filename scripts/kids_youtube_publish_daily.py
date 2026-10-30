#!/usr/bin/env python3
"""Loop step: upload children's episodes that have passed every check.

For each episode in kids_studio/publishing/episodes.json it runs the
preflight (video, verification, subtitles, rights, metadata, founder approval
bound to the file, not yet uploaded, credentials). An episode that passes is
uploaded through kids_studio/publishing/youtube_publisher.py, at most
MAX_PER_RUN per run, and the result is appended to data/youtube_uploads.jsonl
(git-ignored). Anything that fails is reported with its reasons; nothing is
retried silently. The write gate (GF_ALLOW_KIDS_VIDEO_UPLOAD or
FACTORY_LIVE_PUBLISH) is checked before any network call.

    python scripts/kids_youtube_publish_daily.py --once      # loop step
    python scripts/kids_youtube_publish_daily.py --status    # what blocks each episode
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "kids_studio" / "publishing"))
import preflight  # noqa: E402
import youtube_publisher  # noqa: E402
from channels.env_config import read_env_value  # noqa: E402
from channels.write_gate import check_platform_write  # noqa: E402

MAX_PER_RUN = 1


def credentials():
    import os
    return {k: os.environ.get(k) or read_env_value(k, ROOT / ".env") or "" for k in preflight.CREDENTIAL_VARS}


def status(creds=None, now=None, **paths):
    creds = credentials() if creds is None else creds
    defaults, eps = preflight.load_registry(paths.get("registry", preflight.REGISTRY))
    rows = []
    for ep in eps:
        res, digest = preflight.check(ep, defaults, env=creds, now=now,
                                      approvals_path=paths.get("approvals", preflight.APPROVALS),
                                      ledger=paths.get("ledger", preflight.LEDGER),
                                      root=paths.get("root", ROOT))
        rows.append({"episode": ep["episode"], "video_sha256": digest, **preflight.summary(res),
                     "reasons": {k: v["detail"] for k, v in res.items() if v["status"] != "PASS"}, "_ep": ep})
    return defaults, rows


def _log(rec, ledger):
    ledger = Path(ledger)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def once(creds=None, now=None, http=None, **paths):
    now = now or datetime.now(timezone.utc)
    creds = credentials() if creds is None else creds
    ledger = paths.get("ledger", preflight.LEDGER)
    defaults, rows = status(creds, now, **paths)
    ready = [r for r in rows if r["passed"]]
    blocked = ["%s: %s" % (r["episode"], ", ".join(r["failing"])) for r in rows if not r["passed"]]
    if not ready:
        return {"action": "none", "detail": "no episode ready; " + "; ".join(blocked)}
    gate = check_platform_write("youtube", "videos.insert", kids_video=True)
    if not gate.allowed:
        return {"action": "blocked", "detail": "%d episode(s) ready but %s" % (len(ready), gate.reason)}
    done = []
    for r in ready[:MAX_PER_RUN]:
        ep = r["_ep"]
        appr = preflight.find_approval(ep["episode"], r["video_sha256"], paths.get("approvals", preflight.APPROVALS))
        root = Path(paths.get("root", ROOT))
        try:
            out = youtube_publisher.upload(ep, defaults, appr["privacy"], root / ep["video"], root / ep["subtitles"],
                                           creds, **({"http": http} if http else {}))
            rec = {"status": "UPLOADED", "episode": ep["episode"], "video_sha256": r["video_sha256"],
                   "at": now.isoformat(timespec="seconds"), **out}
            done.append("%s -> https://youtu.be/%s (%s, captions %s)" % (ep["episode"], out["video_id"],
                                                                        out["privacy"], out["captions"]))
        except Exception as exc:  # noqa: BLE001  (a failed upload is recorded, never hidden)
            rec = {"status": "FAILED", "episode": ep["episode"], "video_sha256": r["video_sha256"],
                   "at": now.isoformat(timespec="seconds"), "error": str(exc)[:300]}
            done.append("%s failed: %s" % (ep["episode"], str(exc)[:120]))
        _log(rec, ledger)
    failed = any("failed" in d for d in done)
    return {"action": "failed" if failed else "uploaded", "detail": "; ".join(done)}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--status" in argv:
        _, rows = status()
        print(json.dumps([{k: v for k, v in r.items() if k != "_ep"} for r in rows], ensure_ascii=False, indent=1))
        return 0
    print(json.dumps(once(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
