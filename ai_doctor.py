"""
AI Doctor (EOS Phase 2, 2026-07-19) — the real, non-fabricated
engineering-health system this factory's own `CLAUDE.md` already says
`quality_doctor.py` should have been. `quality_doctor.py` is confirmed
still fake: every `_check_*()` method appends a hardcoded string to
`fixes_applied` without ever regenerating/redrawing/repricing anything
real, and `health_score` is a bare `100 - len(issues)*15` with no real
issues behind it. AI Doctor never repeats that pattern — every section
below either reuses an already-real signal or degrades to an honest
"unavailable, here's why" rather than inventing one.

Combines two already-real, already-tested Phase 1 reports unchanged:
  - evolution_engine.build_evolution_report() (bottlenecks, technical
    debt, high-ROI ranking, capability gaps, tool proposals)
  - lib/infrastructure_intelligence.js's getInfrastructureStatus() (via
    mission_control_api.py's existing CLI bridge, reused here directly)

Plus one genuinely new, narrowly-scoped check: dependency risk. Live
`npm audit`/`pip audit` vulnerability scanning is NOT attempted for
`pip` (a real, measured `pip list --outdated` call in this exact
environment took ~54 seconds and checks the whole Python environment,
not just this project's pinned `requirements.txt` — disproportionately
slow for a report section, and not honestly scoped to this project's
real risk). `npm audit --json` IS attempted (fast) and reports its real
result, including the real, confirmed failure mode in this environment
(the configured registry mirror returns 404/NOT_IMPLEMENTED for the
audit endpoint — a tooling limitation, not a project finding, matching
FOUNDER_ACTIVATION_CHECKLIST.md's own prior documented finding). Both
`requirements.txt` and `package.json` are also checked for a real,
instant, static signal: whether dependencies are version-pinned
(`==` in Python, no `^`/`~`/range in Node) — a genuine, well-established
dependency-risk indicator that needs no network call at all.

Architecture drift and deep error-log analysis are deliberately NOT
attempted here (Track C, ADR-081) — no architecture baseline exists to
diff against, and no log-parsing infrastructure exists; building either
now would risk exactly the fabrication `quality_doctor.py` is the
cautionary tale for.
"""

import json
import os
import re
import shutil
import subprocess

FACTORY_DIR = os.path.dirname(os.path.abspath(__file__))
REQUIREMENTS_PATH = os.path.join(FACTORY_DIR, 'requirements.txt')
PACKAGE_JSON_PATH = os.path.join(FACTORY_DIR, 'package.json')


def _check_python_pinning(requirements_path=None):
    path = requirements_path or REQUIREMENTS_PATH
    if not os.path.exists(path):
        return {"checked": 0, "pinned": 0, "unpinned": [], "note": "لا ملف requirements.txt موجود"}

    pinned, unpinned = 0, []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            name = re.split(r'[=<>~! ]', line, maxsplit=1)[0]
            if '==' in line:
                pinned += 1
            else:
                unpinned.append(name)
    return {"checked": pinned + len(unpinned), "pinned": pinned, "unpinned": unpinned, "source": "requirements.txt"}


def _check_node_pinning(package_json_path=None):
    path = package_json_path or PACKAGE_JSON_PATH
    if not os.path.exists(path):
        return {"checked": 0, "pinned": 0, "unpinned": [], "note": "لا ملف package.json موجود"}

    with open(path, 'r', encoding='utf-8') as f:
        pkg = json.load(f)
    deps = pkg.get("dependencies", {})
    pinned, unpinned = 0, []
    for name, spec in deps.items():
        if re.match(r'^\d', spec):  # exact version, no range prefix
            pinned += 1
        else:
            unpinned.append(name)
    return {"checked": len(deps), "pinned": pinned, "unpinned": unpinned, "source": "package.json"}


def _check_npm_audit(timeout=20, cwd=None):
    """Real attempt, honest failure. Never fabricates a vulnerability
    count when the audit endpoint itself is unreachable.

    shutil.which() resolves the real npm executable path -- on Windows,
    npm is a .cmd shim that subprocess.run(["npm", ...]) can't find
    without shell resolution; passing the resolved path directly avoids
    a spurious "file not found" masking the real, honest result (this
    environment's configured registry mirror doesn't implement the
    audit endpoint at all -- confirmed directly, not guessed)."""
    npm_path = shutil.which("npm")
    if not npm_path:
        return {"available": False, "reason": "npm غير موجود على PATH"}
    try:
        result = subprocess.run(
            [npm_path, "audit", "--json"], capture_output=True, encoding="utf-8",
            timeout=timeout, cwd=cwd or FACTORY_DIR,
        )
        data = json.loads(result.stdout or "{}")
        # npm's real error response shape puts the message at the top
        # level (message/method/uri/headers), not nested under an
        # "error" key -- confirmed directly against this environment's
        # real response, not assumed.
        if "metadata" not in data and "message" in data:
            return {"available": False, "reason": data["message"]}
        vulnerabilities = data.get("metadata", {}).get("vulnerabilities", {})
        return {"available": True, "vulnerabilities": vulnerabilities}
    except Exception as e:
        return {"available": False, "reason": str(e)}


def build_ai_doctor_report(decisions_path=None, outcomes_path=None, timeline_path=None,
                            sales_ledger_path=None, capability_registry_path=None):
    import evolution_engine
    from infrastructure_bridge import get_infrastructure_status

    evolution = evolution_engine.build_evolution_report(
        decisions_path=decisions_path, outcomes_path=outcomes_path, timeline_path=timeline_path,
        sales_ledger_path=sales_ledger_path, capability_registry_path=capability_registry_path,
    )
    infrastructure = get_infrastructure_status()

    return {
        "evolution": evolution,
        "infrastructure": infrastructure,
        "dependency_risk": {
            "python": _check_python_pinning(),
            "node": _check_node_pinning(),
            "npm_audit": _check_npm_audit(),
        },
    }


def render_markdown(report):
    import evolution_engine
    from infrastructure_bridge import render_infrastructure_markdown

    lines = ["## AI Doctor — التشخيص الهندسي الحقيقي\n"]
    lines.append(evolution_engine.render_markdown(report["evolution"]))

    lines.append("### البنية التحتية")
    lines.append(render_infrastructure_markdown(report["infrastructure"]))

    dep = report["dependency_risk"]
    lines.append("### مخاطر التبعيات (Dependency Risk)")
    py = dep["python"]
    node = dep["node"]
    lines.append(f"- Python: {py['pinned']}/{py['checked']} مثبَّتة بدقة (pinned)" + (f" — غير مثبَّتة: {', '.join(py['unpinned'])}" if py.get("unpinned") else ""))
    lines.append(f"- Node: {node['pinned']}/{node['checked']} مثبَّتة بدقة (pinned)" + (f" — غير مثبَّتة: {', '.join(node['unpinned'])}" if node.get("unpinned") else ""))
    audit = dep["npm_audit"]
    if audit["available"]:
        lines.append(f"- npm audit: {audit['vulnerabilities']}")
    else:
        lines.append(f"- npm audit: غير متاح — {audit['reason']}")

    return "\n".join(lines) + "\n"
