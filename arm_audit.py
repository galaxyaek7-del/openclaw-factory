"""Deep arm audit: every chapter per arm (registration, status, supports,
publish dry-run, guards). Read-only + dry-run only. Prints JSON verdicts."""
import json
import distributor
import schemas.product as S
import channels.registry as R

prod = S.Product(
    title="ARM-DEEP-AUDIT-PROBE", subtitle="", description="dry-run audit probe",
    price_usd=39.0, file_path="books/eu_ai_act_compliance_toolkit.pdf",
    cover_path="", tags=[], language="en", source_id="ARM-AUDIT",
    raw_price_hint=None, needs_pricing=False, price_source="audit",
)
job = {"title": "Probe post", "text": "dry-run", "price_usd": 39.0,
       "needs_pricing": False}

out = {"arms": {}}
for name in sorted(R._ARMS.keys()):
    arm = R.get(name)
    row = {"class": type(arm).__name__}
    for fn in ["status", "supports", "publish"]:
        row[fn] = hasattr(arm, fn)
    try:
        st = arm.status()
        row["status_value"] = str(st)
    except Exception as e:
        row["status_value"] = "RAISED:%s:%s" % (type(e).__name__, str(e)[:100])
    try:
        row["supports_product"] = bool(arm.supports(prod))
    except Exception as e:
        row["supports_product"] = "RAISED:%s" % type(e).__name__
    try:
        r = distributor.distribute(
            job if name == "x" else prod, arm_names=[name], dry_run=True
        )[0]
        res = r["result"]
        row["dry"] = {"attempted": r["attempted"], "ok": r["ok"],
                      "skip": r["skip_reason"],
                      "err": (res.error if res else None)}
    except Exception as e:
        row["dry"] = {"EXC": "%s:%s" % (type(e).__name__, str(e)[:120])}
    out["arms"][name] = row

# freelancer arm (separate module)
try:
    import freelancer_api as F
    s = F.summarize_project(40742370)
    out["arms"]["freelancer"] = {
        "live": True, "project": s["status"] + "/" + str(s["frontend_status"]),
        "bids": s["bid_count"], "biddable": F.biddability(s),
    }
except Exception as e:
    out["arms"]["freelancer"] = {"live": False, "err": str(e)[:120]}

print(json.dumps(out, indent=1, default=str))
json.dump(out, open("data/arm_deep_audit.json", "w"), indent=1, default=str)
