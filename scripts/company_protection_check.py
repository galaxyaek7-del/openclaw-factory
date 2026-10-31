#!/usr/bin/env python3
"""Daily protection check: one read-only view of the controls that already exist (2026-10-31).

Each check reads a signal another part of the factory already produces; nothing
here writes to a platform or changes a control. Results go to
data/company_protection.json (git-ignored); the founder's decision queue
(lib/commercial_funnel.js) shows every check that fails.

  live_write_switch   FACTORY_LIVE_PUBLISH is not left on in .env (live writes only
                      through the gated scripts, which set it per run)
  secrets_in_repo     scripts/scan_for_secrets.py finds nothing in tracked files
  product_files_public no paid product file (pdf/xlsx/zip/docx) is tracked under books/
  local_backup        newest data/_backups/local-<date> is at most 2 days old and restores
  disk_space          at least 5 GB free on the factory's drive
  payable_withdrawn   no held listing is still published (registry)

    python scripts/company_protection_check.py --once   # loop step, at most once per UTC day
    python scripts/company_protection_check.py --now
"""
import json
import re
import shutil
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "company_protection.json"
MIN_FREE_GB = 5.0
BACKUP_MAX_AGE_DAYS = 2


def _env_value(name, env_path):
    try:
        for line in Path(env_path).read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(rf"\s*{re.escape(name)}\s*=\s*(.*)$", line)
            if m:
                return m.group(1).strip().strip('"').strip("'")
    except OSError:
        return None
    return None


def check_live_write_switch(root=ROOT):
    v = _env_value("FACTORY_LIVE_PUBLISH", Path(root) / ".env")
    if (v or "").lower() == "true":
        return "FAIL", "FACTORY_LIVE_PUBLISH=true is left in .env: every platform write would pass the global switch"
    return "PASS", "off in .env (gated scripts turn it on for one run only)"


def check_secrets(root=ROOT):
    r = subprocess.run([sys.executable, str(Path(root) / "scripts" / "scan_for_secrets.py")], cwd=root,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    last = (r.stdout.strip().splitlines() or [""])[-1]
    return ("PASS" if r.returncode == 0 else "FAIL"), last[:200] or f"exit {r.returncode}"


def check_product_files(root=ROOT):
    out = subprocess.run(["git", "ls-files", "books"], cwd=root, capture_output=True, text=True).stdout
    bad = [p for p in out.splitlines() if re.search(r"\.(pdf|xlsx|zip|docx)$", p, re.I)]
    return ("FAIL", f"{len(bad)} tracked: {', '.join(bad[:3])}") if bad else ("PASS", "none tracked under books/")


def check_backup(root=ROOT, today=None):
    today = today or datetime.now(timezone.utc).date()
    dirs = sorted(p for p in (Path(root) / "data" / "_backups").glob("local-*") if p.is_dir())
    if not dirs:
        return "FAIL", "no local backup exists"
    newest = dirs[-1]
    age = (today - date.fromisoformat(newest.name[len("local-"):])).days
    sys.path.insert(0, str(Path(root) / "scripts"))
    import backup_local_data
    problems = backup_local_data.verify(newest)
    if problems:
        return "FAIL", f"{newest.name} does not restore: {problems[0]}"
    if age > BACKUP_MAX_AGE_DAYS:
        return "FAIL", f"newest backup {newest.name} is {age} days old"
    return "PASS", f"{newest.name} restores cleanly (on this disk only; no off-machine copy)"


def check_disk(root=ROOT):
    free = shutil.disk_usage(root).free / 1e9
    return ("PASS" if free >= MIN_FREE_GB else "FAIL"), f"{free:.1f} GB free (minimum {MIN_FREE_GB:.0f} GB)"


def check_withdrawn_listings(root=ROOT):
    try:
        held = json.loads((Path(root) / "data" / "hold_products.json").read_text(encoding="utf-8"))["products"]
        reg = json.loads((Path(root) / "data" / "product_registry.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError) as e:
        return "UNKNOWN", f"cannot read hold list or registry ({type(e).__name__})"
    ids = {h["product_id"] for h in held.values()}
    live = [p.get("url") for p in reg.get("products", []) if p.get("published") and (p.get("external_ids") or {}).get("gumroad") in ids]
    return ("FAIL", f"{len(live)} held listing(s) still published: {', '.join(live)}") if live else ("PASS", "no held listing is published")


CHECKS = [("live_write_switch", check_live_write_switch), ("secrets_in_repo", check_secrets),
          ("product_files_public", check_product_files), ("local_backup", check_backup),
          ("disk_space", check_disk), ("payable_withdrawn", check_withdrawn_listings)]


def run(now=None, out=OUT, checks=CHECKS):
    now = now or datetime.now(timezone.utc)
    results = {}
    for name, fn in checks:
        try:
            status, detail = fn()
        except Exception as e:  # a broken check is itself a finding
            status, detail = "FAIL", f"{type(e).__name__}: {str(e)[:160]}"
        results[name] = {"status": status, "detail": detail}
    doc = {"checked_at": now.isoformat(timespec="seconds"), "results": results,
           "failing": [k for k, v in results.items() if v["status"] == "FAIL"]}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    return doc


def once(now=None, out=OUT, checks=CHECKS):
    now = now or datetime.now(timezone.utc)
    try:
        last = json.loads(Path(out).read_text(encoding="utf-8")).get("checked_at", "")[:10]
    except (OSError, ValueError):
        last = None
    if last == now.date().isoformat():
        return {"action": "none", "detail": "protection already checked today"}
    doc = run(now, out, checks)
    return {"action": "failed" if doc["failing"] else "checked",
            "detail": ("failing: " + ", ".join(doc["failing"])) if doc["failing"] else f"all {len(doc['results'])} protections hold"}


if __name__ == "__main__":
    print(json.dumps(run() if "--now" in sys.argv else once(), ensure_ascii=False, indent=1 if "--now" in sys.argv else None))
