"""Arm-status watch: detect credential/availability flips across all arms.

--once : status() per registry arm + freelancer grant + associates tag,
         compare against baseline, print one JSON line, update baseline.
         Silent unless the READY set changes. Exit 0 always.
"""
import json

BASELINE_PATH = "data/arm_status_baseline.json"


def _load_dotenv():
    """Deterministic status in any context: bare shells lack the dotenv
    variables factory_loop injects (X creds live in .env). Fill missing
    keys from .env WITHOUT overriding real env and WITHOUT logging values.
    This fixed a false READY/UNAVAILABLE flip-flop between tick and shell."""
    import os

    try:
        with open(".env", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                if k and k not in os.environ:
                    os.environ[k] = v
    except OSError:
        pass


def arm_snapshot():
    import channels.registry as R
    import channels.gumroad_arm  # noqa: F401
    import channels.etsy_arm  # noqa: F401
    import channels.payhip_arm  # noqa: F401
    import channels.paddle_arm  # noqa: F401
    import channels.kdp_arm  # noqa: F401
    import channels.x_arm  # noqa: F401

    snap = {}
    for name in sorted(R._ARMS.keys()):
        try:
            snap[name] = str(R.get(name).status())
        except Exception as e:
            snap[name] = "RAISED:%s" % type(e).__name__
    return snap


def main():
    import os
    import affiliate_commerce.networks as N

    _load_dotenv()
    snap = arm_snapshot()
    snap["freelancer_grant"] = "PRESENT" if any(
        os.environ.get(n) for n in ("FREELANCER_OAUTH_TOKEN", "FLN_OAUTH_TOKEN")
    ) else "ABSENT"
    snap["associates_tag"] = "PRESENT" if N.amazon_associate_tag_configured() else "ABSENT"

    try:
        old = json.load(open(BASELINE_PATH))
    except (OSError, ValueError):
        old = {}
    changes = {
        k: {"from": old.get(k), "to": v}
        for k, v in snap.items()
        if old.get(k) != v
    }
    # First run seeds silently (no false "change" storm).
    action = "silent" if (not old or not changes) else "changed"
    if not old:
        changes = {}
    json.dump(snap, open(BASELINE_PATH, "w"), indent=1)
    print(json.dumps({"checked": len(snap), "changes": changes, "action": action}))


if __name__ == "__main__":
    main()
