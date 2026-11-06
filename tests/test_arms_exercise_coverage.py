import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import arms_exercise as ae  # noqa: E402


def test_every_official_business_arm_has_an_exercise():
    arms = json.loads((ROOT / "data" / "business_arms_state.json").read_text(encoding="utf-8"))["arms"]
    names = [a["name"].lower() for a in (arms if isinstance(arms, list) else arms.values())]
    exercised = " | ".join(n.lower() for n, _ in ae.ARMS)
    key = {"digital products": "digital", "micro-b2b services": "micro-b2b", "research and data services": "research",
           "affiliate intelligence": "affiliate", "content and distribution": "content", "ai operations": "ai operations",
           "productized ai services": "productized", "children's media studio": "children"}
    for n in names:
        assert key[n] in exercised, f"arm {n!r} has no exercise in scripts/arms_exercise.py"


def test_a_crashing_exercise_is_reported_as_failed_not_hidden(monkeypatch):
    def boom():
        raise RuntimeError("x")
    monkeypatch.setattr(ae, "ARMS", [("Broken arm", boom)])
    r = ae.run_all()
    assert r[0]["status"] == "FAILED" and "RuntimeError" in r[0]["evidence"]["crash"]
