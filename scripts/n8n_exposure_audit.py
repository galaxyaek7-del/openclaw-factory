"""Read-only exposure audit for n8n workflows (Cycle 95).

n8n is the factory's notification/execution layer, never its decision centre.
Anything it exposes on a webhook is reachable by whoever can reach n8n, and the
instance has been reachable through a public tunnel. This script reports every
entry point that would let an outsider make the factory act:

  UNAUTH_WEBHOOK      webhook node with no authentication
  PUBLIC_CHAT         chatTrigger with public=true and no authentication
                      (a public LLM endpoint billed to the founder's key)
  ENV_EXPRESSION      ``$env`` in an expression (blocked by default in n8n 2.x)
  EXECUTE_COMMAND     executeCommand node (disabled by default in n8n 2.x)
  INLINE_SECRET       a token-shaped string stored in the definition

Sources:
  * definitions in ``n8n_workflows/*.json`` (tracked exports and prepared files);
  * optionally a COPY of ``~/.n8n/database.sqlite`` (``--db``), opened
    read-only and immutable, to report what is registered and active.

It never talks to the n8n API, never imports, activates or edits anything.
Exit code: 0 when no active-workflow finding is HIGH, 1 otherwise.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF_DIR = os.path.join(ROOT, "n8n_workflows")

_SECRET_RE = re.compile(
    r"(bot\d{6,}:[A-Za-z0-9_-]{30,}|gsk_[A-Za-z0-9]{20,}|pdl_live_\w+|"
    r"sk-[A-Za-z0-9]{20,}|access_token=[A-Za-z0-9_-]{16,})"
)
_ENV_RE = re.compile(r"\$env\b")

SEVERITY = {
    "UNAUTH_WEBHOOK": "HIGH",
    "PUBLIC_CHAT": "HIGH",
    "INLINE_SECRET": "HIGH",
    "EXECUTE_COMMAND": "MEDIUM",
    "ENV_EXPRESSION": "MEDIUM",
}


def _redact(text: str) -> str:
    return _SECRET_RE.sub(lambda m: m.group(0)[:6] + "…<redacted>", text)


def audit_nodes(nodes: list, *, workflow: str, source: str, active: bool | None) -> list[dict]:
    """Return findings for one workflow's node list."""
    findings: list[dict] = []

    def add(kind: str, node: dict, detail: str) -> None:
        findings.append({
            "workflow": workflow, "source": source, "active": active,
            "node": node.get("name"), "kind": kind, "severity": SEVERITY[kind],
            "detail": detail,
        })

    for node in nodes or []:
        ntype = node.get("type", "")
        params = node.get("parameters") or {}
        auth = params.get("authentication") or "none"
        if ntype == "n8n-nodes-base.webhook" and auth == "none":
            add("UNAUTH_WEBHOOK", node,
                f"{params.get('httpMethod') or 'GET'} /webhook/{params.get('path')}")
        if ntype.endswith(".chatTrigger") and params.get("public") and auth == "none":
            add("PUBLIC_CHAT", node, f"mode={params.get('mode') or 'hostedChat'}")
        if ntype == "n8n-nodes-base.executeCommand":
            add("EXECUTE_COMMAND", node, "disabled by default in n8n 2.x")
        blob = json.dumps(params, ensure_ascii=False)
        if _ENV_RE.search(blob):
            add("ENV_EXPRESSION", node, "uses $env (blocked by default)")
        match = _SECRET_RE.search(blob)
        if match:
            add("INLINE_SECRET", node, _redact(match.group(0)))
    return findings


def audit_definitions(wf_dir: str = WF_DIR) -> list[dict]:
    findings: list[dict] = []
    for path in sorted(glob.glob(os.path.join(wf_dir, "*.json"))):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        for wf in data if isinstance(data, list) else [data]:
            if not isinstance(wf, dict):
                continue
            retired = (wf.get("meta") or {}).get("gf_status", "").startswith("SUPERSEDED")
            for f in audit_nodes(wf.get("nodes"), workflow=wf.get("name", "?"),
                                 source=os.path.basename(path), active=None):
                f["retired"] = retired
                findings.append(f)
    return findings


def audit_database(db_path: str) -> list[dict]:
    """Audit a COPY of n8n's database, opened read-only and immutable."""
    uri = "file:" + os.path.abspath(db_path).replace("\\", "/") + "?mode=ro&immutable=1"
    con = sqlite3.connect(uri, uri=True)
    try:
        rows = con.execute("SELECT name, active, nodes FROM workflow_entity").fetchall()
    finally:
        con.close()
    findings: list[dict] = []
    for name, active, nodes in rows:
        try:
            parsed = json.loads(nodes) if isinstance(nodes, str) else nodes
        except ValueError:
            continue
        findings.extend(audit_nodes(parsed, workflow=name, source="database",
                                    active=bool(active)))
    return findings


def alert_path_status(env_path: str = os.path.join(ROOT, ".env")) -> dict:
    """Which alert paths COULD deliver: reports variable presence only, never values.

    The direct path (lib/telegram_direct.js, channels/telegram_direct.py) needs
    both TELEGRAM_BOT_TOKEN and OPENCLAW_TELEGRAM_CHAT_ID. The n8n relay path
    acknowledges with HTTP 200 before its workflow runs, so a 200 there is not
    proof of delivery.
    """
    names: set[str] = set()
    try:
        with open(env_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    if value.strip():
                        names.add(key.strip())
    except OSError:
        pass
    names |= {n for n in ("TELEGRAM_BOT_TOKEN", "OPENCLAW_TELEGRAM_CHAT_ID") if os.environ.get(n)}
    direct_ready = {"TELEGRAM_BOT_TOKEN", "OPENCLAW_TELEGRAM_CHAT_ID"} <= names
    return {
        "direct_telegram_ready": direct_ready,
        "missing_for_direct": sorted({"TELEGRAM_BOT_TOKEN", "OPENCLAW_TELEGRAM_CHAT_ID"} - names),
        "n8n_relay_configured": sorted(n for n in ("N8N_TELEGRAM_WEBHOOK_URL", "N8N_PRODUCTION_WEBHOOK_URL") if n in names),
        "note": "n8n relay returns 200 on receipt; delivery is not confirmed by the factory",
    }


def summarize(findings: list[dict]) -> dict:
    live_high = [f for f in findings if f["active"] and f["severity"] == "HIGH"]
    return {
        "total": len(findings),
        "active_high": len(live_high),
        "by_kind": {k: sum(1 for f in findings if f["kind"] == k) for k in SEVERITY},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", help="path to a COPY of ~/.n8n/database.sqlite")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    findings = audit_definitions()
    if args.db:
        findings += audit_database(args.db)
    report = {"summary": summarize(findings), "alert_paths": alert_path_status(),
              "findings": findings}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for f in findings:
            state = {True: "ACTIVE", False: "inactive", None: "file"}[f["active"]]
            print(f"{f['severity']:6} {f['kind']:16} {state:8} {f['workflow']} :: "
                  f"{f['node']} :: {f['detail']} [{f['source']}]")
        print(json.dumps(report["summary"]))
        print(json.dumps(report["alert_paths"]))
    return 1 if report["summary"]["active_high"] else 0


if __name__ == "__main__":
    sys.exit(main())
