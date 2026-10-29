"""python -m trend_to_product [--write]: print (and optionally write) the dashboard state."""
import json
import sys

from . import linkage

if __name__ == "__main__":
    doc = linkage.write_state() if "--write" in sys.argv else linkage.build_state()
    sys.stdout.write(json.dumps({"counts": doc["counts"], "freshness": doc["evidence_freshness"],
                                 "ranked": [(o["name"], o["band"], o["composite"], o["coverage"])
                                            for o in doc["opportunities"]],
                                 "blockers": len(doc["blockers"])}, ensure_ascii=False, indent=1) + "\n")
