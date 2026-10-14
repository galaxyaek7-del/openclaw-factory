import datetime
import html as H
import json
import re
import sys
import urllib.request
from pathlib import Path
sys.path.insert(0, r"C:\openclaw-dasgboard")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

req = urllib.request.Request("https://aekraft.gumroad.com/l/bfhpzl",
                             headers={"User-Agent": "Mozilla/5.0"})
raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")

# The manifest block is the anchor we KNOW is inside the rendered description.
i = raw.find("EXACTLY WHAT YOU DOWNLOAD")
print("manifest anchor at:", i)

# walk back to the opening of that JSON string value
start = raw.rfind('":"', 0, i)
if start != -1:
    start += 3
    end = raw.find('","', i)
    blob = raw[start:end] if end != -1 else raw[start:start + 20000]
    print("captured span:", len(blob), "chars")

    desc = (blob.replace('\\"', '"').replace("\\n", "\n").replace("\\/", "/")
                .replace("\\\\", "\\"))
    desc = H.unescape(desc)
else:
    desc = ""
    print("could not locate the enclosing value")

print()
print("=" * 78)
print("ROLLBACK BASELINE (real this time)")
print("=" * 78)
print(f"description length: {len(desc)} chars")

hits = list(re.finditer(r"122 KB|6 KB", desc))
print(f"target values found: {len(hits)}")
for m in hits:
    ctx = desc[max(0, m.start() - 58):m.end() + 34].replace("\n", " ")
    print(f"  {m.group(0):<8} @{m.start():<6} ...{ctx}...")

if len(desc) < 500 or not hits:
    print("\nSTILL FAILED -> recording honestly, NOT writing a fake baseline.")
    Path("data/cycle83_description_baseline.json").write_text(json.dumps({
        "probe": "cycle83_description_rollback_baseline", "slug": "bfhpzl",
        "capture_status": "FAILED", "read_only": True, "cost_usd": 0,
        "description_html": None,
    }, indent=2), encoding="utf-8")
    raise SystemExit(2)

Path("data/cycle83_description_baseline.json").write_text(json.dumps({
    "probe": "cycle83_description_rollback_baseline", "slug": "bfhpzl",
    "captured_utc": datetime.datetime.now(
        datetime.timezone.utc).isoformat(),
    "capture_status": "OK", "read_only": True, "cost_usd": 0,
    "description_length": len(desc), "description_html": desc,
    "rollback_instruction": "re-submit this exact description_html verbatim",
}, indent=2, ensure_ascii=False), encoding="utf-8")
print("\nwrote data/cycle83_description_baseline.json")