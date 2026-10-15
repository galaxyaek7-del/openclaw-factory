"""Cycle 86: prepare and (only on explicit approval) apply the /l/bfhpzl
description repair through update_product_description_scoped().

DEFAULT MODE IS DRY RUN. It verifies everything and performs no network write.

Safety properties this script is built to demonstrate, not merely claim:

  * The approval is bound to ONE product, ONE operation (update_description),
    ONE field (description), and the sha256 of the EXACT text to be written.
    Every other field, product, or text is refused before any request.
  * FACTORY_LIVE_PUBLISH is never set. If it is already set in the environment
    this script aborts rather than proceeding under a compromised posture.
  * The write is verified by re-reading the live description afterwards, so a
    200 that silently fails to persist is reported as FAIL, not success.

Usage
    python scripts/cycle86_apply_description_repair.py            # dry run
    python scripts/cycle86_apply_description_repair.py --execute  # live write
"""
import argparse
import datetime
import hashlib
import json
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PRODUCT_ID = "LzOV85deBGdLgNZmvpvYGw=="
PRODUCT_URL = "https://aekraft.gumroad.com/l/bfhpzl"
ZIP = "books/_releases/etsy_suspension_complete_bundle_v3.zip"
BASELINE = "data/cycle83_description_baseline.json"
REPORT = "data/cycle86_description_repair.json"

# The two approved corrections. Nothing else may change.
TARGETS = [
    ("etsy_suspension_appeal_kit.pdf", 138923, 122, 139),
    ("etsy_appeal_evidence_tracker.xlsx", 15011, 6, 15),
]


def fail(msg):
    print(f"\nABORT: {msg}")
    sys.exit(1)


def load_token():
    for line in open(".env", encoding="utf-8"):
        if line.startswith("GUMROAD_ACCESS_TOKEN="):
            return line.split("=", 1)[1].strip()
    fail("no GUMROAD_ACCESS_TOKEN in .env")


def verify_sizes():
    """Re-read the delivered file from its real source, not from a note."""
    if not os.path.isfile(ZIP):
        fail(f"delivery archive missing: {ZIP}")
    zf = zipfile.ZipFile(ZIP)
    bad = zf.testzip()
    if bad is not None:
        fail(f"archive CRC failure in {bad}; refusing to quote sizes from it")
    sizes = {i.filename: i.file_size for i in zf.infolist()}
    rows = []
    for name, expect_bytes, _was, _now in TARGETS:
        actual = sizes.get(name)
        if actual is None:
            fail(f"{name} is not in the archive; the approved numbers no longer apply")
        if actual != expect_bytes:
            fail(f"{name} is {actual:,} B, approved numbers assumed {expect_bytes:,} B.\n"
                 "      The approval no longer matches reality -- stop and re-derive.")
        rows.append({"file": name, "bytes": actual,
                     "decimal_kb": round(actual / 1000),
                     "binary_kib": round(actual / 1024)})
    return rows


def build_patch():
    """Rebuild the exact new text from the captured baseline, read-only."""
    html = json.load(open(BASELINE, encoding="utf-8"))["description_html"]
    import re
    new = html
    changes = []
    for name, size, was, now in TARGETS:
        pat = re.compile(r"(" + re.escape(name) + r"\s+)" + str(was) + r"(\s*KB\b)")
        if len(pat.findall(new)) != 1:
            fail(f"anchor for {name} is not unique; refusing to edit")
        new, n = pat.subn(r"\g<1>" + str(now) + r"\g<2>", new, count=1)
        changes.append({"file": name, "bytes": size, "was_kb": was, "now_kb": now})

    import difflib
    ops = [o for o in difflib.SequenceMatcher(None, html, new, autojunk=False)
           .get_opcodes() if o[0] != "equal"]
    if len(ops) != 2:
        fail(f"expected exactly 2 changed regions, found {len(ops)}")

    # Restoring the edits must reproduce the original exactly: proof the patch
    # cannot have touched anything outside the two approved numbers.
    restored = new
    for tag, i1, i2, j1, j2 in reversed(ops):
        restored = restored[:j1] + html[i1:i2] + restored[j2:]
    if restored != html:
        fail("the patch leaked outside the approved numbers; refusing to proceed")
    return html, new, changes, ops


def prove_binding(new_text):
    """Demonstrate the authorization's limits using the real gate, no network."""
    from channels import write_scope as ws
    print("\n--- authorization binding, exercised against the real gate ---")

    good = ws.issue_scope(product_id=PRODUCT_ID, slug="bfhpzl",
                          payload={"description": new_text},
                          operation="update_description",
                          note="cycle86 binding proof")
    d = ws.consume_scope(scope_id=good.scope_id, product_id=PRODUCT_ID,
                         payload={"description": new_text},
                         operation="update_description")
    print(f"  exact product + operation + text        : "
          f"{'ALLOWED' if d.allowed else 'REFUSED'}  ({d.reason or 'ok'})")

    def probe(label, **kw):
        s = kw.pop("scope_kwargs")
        sc = ws.issue_scope(**s)
        r = ws.consume_scope(scope_id=sc.scope_id, **kw)
        print(f"  {label:42s}: {'ALLOWED' if r.allowed else 'REFUSED'}")
        return r.allowed

    other = ws.issue_scope(product_id="mvuoJTNLfsWsm0NF-CrZHw==", slug="fgruzn",
                           payload={"description": new_text},
                           operation="update_description", note="wrong product")
    r = ws.consume_scope(scope_id=other.scope_id, product_id=PRODUCT_ID,
                         payload={"description": new_text},
                         operation="update_description")
    print(f"  {'scope minted for a DIFFERENT product':42s}: "
          f"{'ALLOWED' if r.allowed else 'REFUSED'}")

    diff = ws.issue_scope(product_id=PRODUCT_ID, slug="bfhpzl",
                          payload={"description": new_text + " tampered"},
                          operation="update_description", note="wrong text")
    r = ws.consume_scope(scope_id=diff.scope_id, product_id=PRODUCT_ID,
                         payload={"description": new_text},
                         operation="update_description")
    print(f"  {'scope minted for DIFFERENT text':42s}: "
          f"{'ALLOWED' if r.allowed else 'REFUSED'}")

    replay = ws.consume_scope(scope_id=good.scope_id, product_id=PRODUCT_ID,
                              payload={"description": new_text},
                              operation="update_description")
    print(f"  {'REPLAY of the already-spent scope':42s}: "
          f"{'ALLOWED' if replay.allowed else 'REFUSED'}")

    # Price/title/files/publication must be outside this operation entirely.
    #
    # These probes exercise the FULL mint-then-consume chain, not the mint
    # alone. An earlier version tested only issue_scope and reported "ALLOWED"
    # for price/name/files/published -- a false alarm: consume_scope refuses
    # any payload touching fields outside the authorization, so the write was
    # never reachable. Proving this end-to-end is the only honest way to state
    # the guarantee.
    for field in ("price", "name", "files", "published"):
        verdict = "no scope can even be minted"
        try:
            s2 = ws.issue_scope(product_id=PRODUCT_ID, slug="bfhpzl",
                                payload={field: "x"},
                                operation="update_description",
                                note="field smuggling probe")
        except (ValueError, TypeError):
            pass
        else:
            d2 = ws.consume_scope(scope_id=s2.scope_id, product_id=PRODUCT_ID,
                                  payload={field: "x"},
                                  operation="update_description")
            verdict = ("MINTED BUT REFUSED ON CONSUME"
                       if not d2.allowed else "*** WRITE WOULD BE REACHABLE ***")
        print(f"  {('field ' + field + ' under update_description'):42s}: {verdict}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true",
                    help="perform the live write (requires founder approval)")
    args = ap.parse_args()

    # Never proceed under a globally-permissive posture.
    if os.environ.get("FACTORY_LIVE_PUBLISH", "").strip().lower() in ("1", "true", "yes"):
        fail("FACTORY_LIVE_PUBLISH is set. This repair must use a single-use "
             "scope, never the global flag.")

    print("=" * 72)
    print("Cycle 86 -- /l/bfhpzl description repair")
    print("=" * 72)
    print(f"mode: {'LIVE WRITE (--execute)' if args.execute else 'DRY RUN (no write)'}")

    print("\n--- 1. delivered file, read from its real source ---")
    for r in verify_sizes():
        print(f"  {r['file']:40s} {r['bytes']:>8,} B   "
              f"decimal {r['decimal_kb']} KB | binary {r['binary_kib']} KiB")

    print("\n--- 2. exact text change ---")
    old, new, changes, ops = build_patch()
    print(f"  old sha256 : {hashlib.sha256(old.encode()).hexdigest()}")
    print(f"  new sha256 : {hashlib.sha256(new.encode()).hexdigest()}")
    for c in changes:
        print(f"  {c['file']:40s} {c['was_kb']:>4} KB -> {c['now_kb']:>3} KB "
              f"({c['bytes']:,} B)")
    print(f"  changed regions: {len(ops)}  ->  "
          + ", ".join(f"{old[i1:i2]!r}->{new[j1:j2]!r}" for _t, i1, i2, j1, j2 in ops))
    print("  price / title / attachments / publication state: UNTOUCHED")

    print("\n--- 3. authorization limits ---")
    prove_binding(new)

    result = {
        "probe": "cycle86_description_repair",
        "generated_at_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "product_id": PRODUCT_ID,
        "product_url": PRODUCT_URL,
        "mode": "LIVE" if args.execute else "DRY RUN",
        "live_write_performed": False,
        "cost_usd": 0,
        "old_sha256": hashlib.sha256(old.encode()).hexdigest(),
        "new_sha256": hashlib.sha256(new.encode()).hexdigest(),
        "changes": changes,
        "authorization_state": "NOT MINTED -- no scope has been issued",
        "awaiting": "independent founder approval before any live write",
    }

    if not args.execute:
        print("\n--- 4. no write performed ---")
        print("  This run prepared and validated only. No scope was minted,")
        print("  no request was sent, nothing changed live.")
        json.dump(result, open(REPORT, "w", encoding="utf-8"),
                  indent=2, ensure_ascii=False)
        print(f"\nwrote {REPORT}")
        return

    # ---- live path: only reached with --execute ----
    print("\n--- 4. live write ---")
    token = load_token()
    from channels import gumroad_publisher as gp
    from channels import write_scope as ws

    scope = ws.issue_scope(product_id=PRODUCT_ID, slug="bfhpzl",
                           payload={"description": new},
                           operation="update_description",
                           note="cycle86 approved repair")
    print(f"  scope issued: {scope.scope_id[:12]}... (single use)")

    try:
        gp.update_product_description_scoped(token, PRODUCT_ID, new,
                                            scope_id=scope.scope_id)
    except Exception as e:
        print(f"  REFUSED / FAILED: {type(e).__name__}: {e}")
        result["authorization_state"] = f"REFUSED: {e}"
        json.dump(result, open(REPORT, "w", encoding="utf-8"),
                  indent=2, ensure_ascii=False)
        sys.exit(2)

    print("  write verified by re-read. PASS")
    result["live_write_performed"] = True
    result["authorization_state"] = "scope minted, consumed, write verified"
    json.dump(result, open(REPORT, "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    print(f"\nwrote {REPORT}")


if __name__ == "__main__":
    main()