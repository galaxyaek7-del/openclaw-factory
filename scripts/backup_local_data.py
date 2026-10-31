#!/usr/bin/env python3
"""Daily local backup of the business records git does not hold (2026-10-31).

Approvals, inquiries, interest signals, support tickets, upload ledgers and
similar files are git-ignored on purpose (personal data, local decisions), so
until now a disk failure or a bad write lost them for good. Once per UTC day
this copies each listed file, gzip-compressed, into
data/_backups/local-<date>/ with a manifest of the original SHA-256, then
restores every copy into memory and checks the hash (a backup that cannot be
read back is reported, not trusted).

Secrets are never copied (keys, tokens, session secrets, .env): a backup must
not multiply them. Only directories this script created (local-<date>) are
pruned, keeping the newest KEEP_DAYS.

    python scripts/backup_local_data.py --once     # loop step: at most once per UTC day
    python scripts/backup_local_data.py --now      # run now
    python scripts/backup_local_data.py --verify <dir>
"""
import gzip
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "data" / "_backups"
KEEP_DAYS = 14

# Records that exist only on this machine. Order does not matter; a missing file is reported, not an error.
FILES = [
    "data/publication_approvals.json", "data/kids_upload_approvals.json",
    "data/inquiries.jsonl", "data/customer_interest.jsonl", "data/customer_interest_rejected.jsonl",
    "data/support_tickets.jsonl", "data/consultation_log.jsonl", "data/kids_feedback.jsonl",
    "data/youtube_uploads.jsonl", "data/trial_events.jsonl", "data/auth_audit.jsonl",
    "data/attribution_log.jsonl", "data/uspto_fee_monitor.jsonl", "data/agent_executions.jsonl",
    "data/agent_tasks.jsonl", "data/evidence_recording_audit_runs.jsonl",
    # tracked ledgers whose newest lines may not be committed yet
    "finance_data.json", "data/sales_ledger.jsonl", "data/decisions.jsonl", "data/incident_memory.jsonl",
]
SECRET = re.compile(r"(^|/)(\.env[^/]*|.*secret.*|.*token.*|.*key.*\.json|.*credential.*)$", re.I)


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def run(now=None, root=ROOT, dest=DEST, files=FILES, keep=KEEP_DAYS):
    now = now or datetime.now(timezone.utc)
    out = Path(dest) / f"local-{now.date().isoformat()}"
    tmp = Path(str(out) + ".partial")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    manifest = {"created_at": now.isoformat(timespec="seconds"), "files": {}, "missing": [], "refused_secret": []}
    for rel in files:
        if SECRET.search(rel):
            manifest["refused_secret"].append(rel)
            continue
        src = Path(root) / rel
        if not src.is_file():
            manifest["missing"].append(rel)
            continue
        data = src.read_bytes()
        name = rel.replace("/", "__") + ".gz"
        (tmp / name).write_bytes(gzip.compress(data, mtime=0))
        manifest["files"][rel] = {"copy": name, "bytes": len(data), "sha256": _sha(data)}
    (tmp / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    problems = verify(tmp)
    if problems:
        return {"action": "failed", "detail": "restore check failed: " + "; ".join(problems[:3]), "dir": str(tmp)}
    shutil.rmtree(out, ignore_errors=True)
    tmp.rename(out)
    pruned = prune(dest, keep)
    total = sum(f["bytes"] for f in manifest["files"].values())
    return {"action": "backed_up", "dir": str(out.relative_to(root)) if out.is_relative_to(root) else str(out),
            "detail": f"{len(manifest['files'])} file(s), {total:,} bytes, restore-checked"
                      + (f"; missing: {len(manifest['missing'])}" if manifest["missing"] else "")
                      + (f"; pruned: {', '.join(pruned)}" if pruned else "")}


def verify(backup_dir):
    """Decompress every copy and compare with the manifest hash; returns the problems."""
    d = Path(backup_dir)
    try:
        manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [f"manifest unreadable: {type(e).__name__}"]
    problems = []
    for rel, info in manifest["files"].items():
        try:
            data = gzip.decompress((d / info["copy"]).read_bytes())
        except (OSError, EOFError) as e:
            problems.append(f"{rel}: {type(e).__name__}")
            continue
        if _sha(data) != info["sha256"] or len(data) != info["bytes"]:
            problems.append(f"{rel}: hash mismatch")
    return problems


def prune(dest=DEST, keep=KEEP_DAYS):
    dirs = sorted(p for p in Path(dest).glob("local-*") if p.is_dir() and re.fullmatch(r"local-\d{4}-\d{2}-\d{2}", p.name))
    gone = []
    for p in dirs[:-keep] if keep else []:
        shutil.rmtree(p)
        gone.append(p.name)
    return gone


def once(now=None, root=ROOT, dest=DEST, **kw):
    now = now or datetime.now(timezone.utc)
    if (Path(dest) / f"local-{now.date().isoformat()}" / "manifest.json").is_file():
        return {"action": "none", "detail": f"local data already backed up for {now.date().isoformat()}"}
    return run(now, root, dest, **kw)


if __name__ == "__main__":
    if "--verify" in sys.argv:
        p = verify(sys.argv[sys.argv.index("--verify") + 1])
        print(json.dumps({"problems": p}))
        sys.exit(1 if p else 0)
    print(json.dumps(run() if "--now" in sys.argv else once()))
