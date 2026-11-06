#!/usr/bin/env python3
"""Loop step: daily storefront health guard (one read-only Gumroad list call). See listing_health.py."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import listing_health  # noqa: E402

if __name__ == "__main__":
    try:
        r = listing_health.run_once(force="--now" in sys.argv)
    except Exception as e:  # noqa: BLE001
        r = {"action": "failed", "detail": f"{type(e).__name__}: {str(e)[:200]}"}
    sys.stdout.write(json.dumps(r, ensure_ascii=False) + "\n")
