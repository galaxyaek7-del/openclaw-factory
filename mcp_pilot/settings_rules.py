"""Apply or roll back the MCP-pilot deny rules in .claude/settings.local.json.

    python mcp_pilot/settings_rules.py apply    [settings_path]
    python mcp_pilot/settings_rules.py rollback [settings_path]
    python mcp_pilot/settings_rules.py check    [settings_path]

apply inserts a "deny" array as an exact text block after "allow", so every
existing byte (all allow rules and their formatting) is untouched. rollback
removes that exact block, which restores the file byte for byte. If someone
has since edited the deny array (e.g. Claude Code saved an "always deny"
choice), rollback falls back to removing only these entries through JSON and
reports that formatting may change. It never touches allow rules.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT = HERE.parent / ".claude" / "settings.local.json"
RULES = json.loads((HERE / "deny_rules.json").read_text(encoding="utf-8"))["deny"]


def _block(nl):
    body = ("," + nl).join(f'      {json.dumps(r)}' for r in RULES)
    return f',{nl}    "deny": [{nl}{body}{nl}    ]'


def _nl(text):
    return "\r\n" if "\r\n" in text else "\n"


def apply(path):
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    perms = data.get("permissions", {})
    if "deny" in perms:
        missing = [r for r in RULES if r not in perms["deny"]]
        if not missing:
            return "already applied"
        raise SystemExit("a deny array already exists; refusing to merge by hand -- review it first")
    nl = _nl(text)
    tail = f"{nl}  }}{nl}}}"
    end = text.rstrip()
    if not end.endswith("]" + tail):
        raise SystemExit("unexpected file layout; not editing")
    cut = len(end) - len(tail)
    new = end[:cut] + _block(nl) + end[cut:] + text[len(end):]
    after = json.loads(new)
    assert after["permissions"]["allow"] == perms["allow"], "allow rules changed"
    assert after["permissions"]["deny"] == RULES
    path.write_text(new, encoding="utf-8", newline="")
    return f"applied {len(RULES)} deny rules; {len(perms['allow'])} allow rules unchanged"


def rollback(path):
    text = path.read_text(encoding="utf-8")
    block = _block(_nl(text))
    if block in text:
        path.write_text(text.replace(block, "", 1), encoding="utf-8", newline="")
        return "removed the exact deny block (byte-for-byte restore)"
    data = json.loads(text)
    perms = data.get("permissions", {})
    if "deny" not in perms:
        return "nothing to roll back"
    kept = [r for r in perms["deny"] if r not in RULES]
    if kept:
        perms["deny"] = kept
    else:
        del perms["deny"]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return f"removed pilot rules via JSON (formatting may differ); {len(kept)} other deny rules kept"


def check(path):
    perms = json.loads(path.read_text(encoding="utf-8")).get("permissions", {})
    deny = perms.get("deny", [])
    return {"allow": len(perms.get("allow", [])), "deny": len(deny),
            "pilot_rules_present": sum(r in deny for r in RULES), "pilot_rules_total": len(RULES)}


if __name__ == "__main__":
    cmd = sys.argv[1]
    target = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT
    print({"apply": apply, "rollback": rollback, "check": check}[cmd](target))
