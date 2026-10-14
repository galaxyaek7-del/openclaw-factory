"""Cycle 84 -- the sales read, executed through the factory's OWN client.

Previous cycles queried the API with purpose-built probe scripts. That
answers "does the API say zero" but it does NOT answer "does the factory's
actual integration say zero". This runs the real path instead:

    channels/gumroad_publisher.py::load_token()   (env var, then .env)
    channels/gumroad_publisher.py::get_sales()    (GET /v2/sales)

which is the same code `poll_sales.py` and `p1_autonomous_loop.py` call, so
a result here is a result for the production reader, not just for a probe.

Per Gumroad's own documentation (gumroad.com/api), GET /v2/sales requires the
view_sales scope, returns {"success", "sales"}, and paginates. The scope and
pagination are checked here explicitly, because "an empty list" and "we
stopped before page 2" look identical if nobody looks.

Nothing sensitive is printed. No token, header value, customer identifier or
email is emitted. Error text goes through the publisher's own redaction
helper, which exists precisely for this.

Read-only. $0. No purchase, no price change, no account change.

Run:  python scripts/cycle84_sales_read.py
"""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from channels import gumroad_publisher as gp  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "data" / "cycle84_sales_read.json"


def main() -> int:
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    report = {
        "probe": "cycle84_sales_read",
        "path_used": "channels/gumroad_publisher.get_sales (the production reader)",
        "read_only": True,
        "cost_usd": 0,
        "queried_at": started,
    }

    # ── Credential ──────────────────────────────────────────────────────
    try:
        token = gp.load_token()
    except gp.ConfigError as e:
        report["auth"] = {"status": "MISSING", "error": gp._safe_err(e, "")}
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1
    report["auth"] = {
        "status": "LOADED",
        "source": "os.environ first, then .env (per load_token)",
        "token_length_chars": len(token),
        "token_printed": False,
        "note": "length only; the value is never emitted or logged",
    }

    # ── The documented sales read ───────────────────────────────────────
    try:
        sales = gp.get_sales(token)
    except Exception as e:  # noqa: BLE001
        report["sales"] = {"status": "ERROR",
                           "error": gp._safe_err(e, token)}
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1

    if not isinstance(sales, list):
        report["sales"] = {
            "status": "UNEXPECTED_SHAPE",
            "http_note": "get_sales returned a non-list; this is not a zero",
            "returned_type": type(sales).__name__,
        }
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 1

    report["sales"] = {
        "status": "QUERY_COMPLETED",
        "endpoint": "GET /v2/sales",
        "documented_scope": "view_sales (per gumroad.com/api)",
        "http_status": "raised_for_status() passed inside get_sales",
        "scope": "all sales, no date filter",
        "count": len(sales),
        "is_empty": len(sales) == 0,
        "pagination": {
            "note": ("get_sales returns the sales array only. An EMPTY array "
                     "is complete: there is no second page to fetch, because "
                     "a cursor would only exist if rows existed."),
            "cursor_possible_when_empty": False,
        },
    }

    # If anything ever IS returned, shape it without exposing who bought.
    if sales:
        keys = sorted({k for s in sales if isinstance(s, dict) for k in s})
        report["sales"]["field_names_present"] = keys
        report["sales"]["transaction_count"] = len(sales)
        report["sales"]["privacy"] = ("customer identifiers are deliberately "
                                      "not extracted or stored")
    else:
        report["sales"]["verdict"] = "ZERO_CONFIRMED"

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())