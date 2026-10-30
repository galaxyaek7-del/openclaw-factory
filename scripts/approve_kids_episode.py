#!/usr/bin/env python3
"""Record the founder's approval to upload one children's episode.

The approval is bound to the sha256 of the exact video file: if the file is
rebuilt, the approval no longer matches and the upload stops. Both reviews
must be stated explicitly; there is no default "yes".

    python scripts/approve_kids_episode.py --episode ep01_nunu_little_bridge --privacy unlisted \
        --child-safety-reviewed --arabic-reviewed [--days 14]

Writes data/kids_upload_approvals.json (git-ignored). Run by the founder.
"""
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "kids_studio" / "publishing"))
import preflight  # noqa: E402


def approve(episode, privacy, child_safety, arabic, days=14, approvals_path=preflight.APPROVALS,
            registry=preflight.REGISTRY, root=ROOT, now=None):
    if privacy not in preflight.PRIVACY:
        raise ValueError("privacy must be one of %s" % ", ".join(preflight.PRIVACY))
    if not (child_safety and arabic):
        raise ValueError("both --child-safety-reviewed and --arabic-reviewed are required")
    _, eps = preflight.load_registry(registry)
    ep = next((e for e in eps if e["episode"] == episode), None)
    if not ep:
        raise ValueError("unknown episode %s" % episode)
    video = Path(root) / ep["video"]
    if not video.is_file():
        raise ValueError("video missing: %s" % ep["video"])
    now = now or datetime.now(timezone.utc)
    rec = {"episode": episode, "video_sha256": preflight.sha256(video), "privacy": privacy,
           "child_safety_reviewed": True, "arabic_reviewed": True, "approved_by": "founder",
           "approved_at": now.isoformat(timespec="seconds"),
           "expires_at": (now + timedelta(days=days)).isoformat(timespec="seconds")}
    path = Path(approvals_path)
    doc = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"approvals": []}
    doc["approvals"] = [a for a in doc.get("approvals", []) if a.get("episode") != episode] + [rec]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--episode", required=True)
    ap.add_argument("--privacy", required=True, choices=preflight.PRIVACY)
    ap.add_argument("--child-safety-reviewed", action="store_true")
    ap.add_argument("--arabic-reviewed", action="store_true")
    ap.add_argument("--days", type=int, default=14)
    a = ap.parse_args(argv)
    try:
        rec = approve(a.episode, a.privacy, a.child_safety_reviewed, a.arabic_reviewed, a.days)
    except ValueError as exc:
        print(json.dumps({"refused": str(exc)}))
        return 1
    print(json.dumps({"approved": rec["episode"], "privacy": rec["privacy"], "expires_at": rec["expires_at"],
                      "video_sha256": rec["video_sha256"][:16]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
