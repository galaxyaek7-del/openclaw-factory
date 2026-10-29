"""Affiliate click classification (backlog B24, 2026-10-29).

Every row in data/affiliate_clicks.jsonl gets a class and the basis for it.
The ledger is append-only and is never rewritten: classification is derived on
read and summarised in data/affiliate_click_classification.json.

Classes (strongest evidence first):
  BOT               the request's user agent was recorded and looks automated
  INTERNAL          came from this machine: recorded origin "loopback", or the
                    server could only be reached from this machine when it was
                    recorded (see server_reachability)
  TEST              product id exists in no catalog the routes accept
  EXTERNAL_BROWSER  recorded origin "external" and a browser user agent: the
                    strongest signal of a person available, not proof of one
  UNKNOWN           not enough recorded to say

Only EXTERNAL_BROWSER counts as possible human traffic.

Since 2026-10-29 the two public click routes (/api/affiliate/click and
/api/solutions/click in server.js) record `ua_category` and `origin` on each
click. Rows written before that carry neither; they are classified by
server_reachability() or left UNKNOWN.
"""
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LEDGER = _ROOT / "data" / "affiliate_clicks.jsonl"
DEFAULT_SUMMARY = _ROOT / "data" / "affiliate_click_classification.json"

CLASSES = ("BOT", "INTERNAL", "TEST", "EXTERNAL_BROWSER", "UNKNOWN")

# Commit 63f7af8 (2026-07-17, "loopback-only binding") made server.js listen on
# BIND_HOST || '127.0.0.1'. Before it the server bound all interfaces.
LOOPBACK_SINCE = "2026-07-17"
LOOPBACK_COMMIT = "63f7af8"
_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def _read_env_bind_host(env_path):
    try:
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"\s*BIND_HOST\s*=\s*(\S*)", line)
                if m:
                    return m.group(1).strip("'\"")
    except OSError:
        pass
    return None


def server_reachability(root=None, environ=None):
    """Whether the click routes could only be reached from this machine.

    Read from the code and config, not assumed: server.js must still default
    BIND_HOST to 127.0.0.1, and neither the process environment nor .env may
    override it with a non-loopback address. A tunnel or reverse proxy in front
    of the server would make external clicks arrive as loopback; none is
    configured in this repository, which is all this check can see.
    """
    root = Path(root or _ROOT)
    environ = os.environ if environ is None else environ
    try:
        server = (root / "server.js").read_text(encoding="utf-8")
    except OSError:
        return {"loopback_only": None, "basis": "server.js not readable"}
    default_loopback = re.search(r"BIND_HOST\s*=\s*process\.env\.BIND_HOST\s*\|\|\s*'127\.0\.0\.1'", server)
    override = environ.get("BIND_HOST") or _read_env_bind_host(root / ".env")
    if not default_loopback:
        return {"loopback_only": None, "basis": "server.js no longer defaults BIND_HOST to 127.0.0.1"}
    if override and override not in _LOOPBACK:
        return {"loopback_only": False, "basis": f"BIND_HOST overridden to {override}"}
    return {"loopback_only": True, "since": LOOPBACK_SINCE,
            "basis": f"server.js listens on BIND_HOST || '127.0.0.1' (commit {LOOPBACK_COMMIT}, "
                     f"{LOOPBACK_SINCE}); no non-loopback BIND_HOST in the environment or .env"}


def known_product_ids():
    """Ids the two click routes accept: Amazon catalog + commission portfolio."""
    ids = set()
    try:
        from affiliate_commerce import products
        ids |= {p["id"] for p in products.PRODUCTS}
    except Exception:
        pass
    try:
        from commission_engine import load_opportunity_portfolio
        ids |= {o.get("opportunity_id") for o in load_opportunity_portfolio()}
    except Exception:
        pass
    return {i for i in ids if i}


def classify(row, reach, known_ids=None):
    """(class, basis) for one click row."""
    ua = row.get("ua_category")
    origin = row.get("origin")
    if ua == "bot":
        return "BOT", "recorded user agent is automated"
    if origin == "loopback":
        return "INTERNAL", "recorded origin is this machine"
    ts = str(row.get("timestamp") or "")
    if origin is None and reach.get("loopback_only") and ts[:10] >= reach.get("since", "9999"):
        return "INTERNAL", "server reachable only from this machine when recorded (" + reach["basis"] + ")"
    if known_ids is not None and row.get("product_id") not in known_ids:
        return "TEST", f"product id {row.get('product_id')!r} is in no catalog the click routes accept"
    if origin == "external" and ua == "browser":
        return "EXTERNAL_BROWSER", "external origin with a browser user agent (not proof of a person)"
    missing = [k for k in ("origin", "ua_category") if row.get(k) is None]
    return "UNKNOWN", "not recorded: " + ", ".join(missing) if missing else "external but not a browser agent"


def _read(path):
    out = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        continue
    except OSError:
        pass
    return out


def summarize(ledger_path=None, root=None, environ=None, known_ids=None):
    rows = _read(ledger_path or DEFAULT_LEDGER)
    reach = server_reachability(root, environ)
    ids = known_product_ids() if known_ids is None else known_ids
    counts = {c: 0 for c in CLASSES}
    bases = {}
    for r in rows:
        c, why = classify(r, reach, ids)
        counts[c] += 1
        bases.setdefault(c, {}).setdefault(why, 0)
        bases[c][why] += 1
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_recorded": len(rows),
        "counts": counts,
        "possible_human": counts["EXTERNAL_BROWSER"],
        "bases": bases,
        "server_reachability": reach,
        "note": "possible_human counts only external clicks with a browser user agent; "
                "internal, test, bot and unknown clicks are excluded",
    }


def write_summary(path=None, **kw):
    doc = summarize(**kw)
    path = Path(path or DEFAULT_SUMMARY)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)
    return doc


if __name__ == "__main__":
    import sys
    d = write_summary() if "--write" in sys.argv else summarize()
    sys.stdout.write(json.dumps({k: d[k] for k in ("total_recorded", "counts", "possible_human")},
                                indent=1) + "\n")
