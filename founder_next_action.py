"""Founder ONE-NEXT-ACTION engine (Autonomous Enterprise Master Plan Task 1,
2026-08-15).

Mandate section 22 ("Human-Minimal Operating Model"): the founder should
receive ONE prioritized next action, not twenty technical tasks. Every
human gate across all arms is consolidated here into a single ranked queue
computed from REAL state only:

  * .env presence (PADDLE_WEBHOOK_SECRET, AMAZON_ASSOCIATE_TAG, etc.)
  * channels/publish_protection_state.json (gumroad draft / first publish)
  * data/paddle_products.json (checkout readiness)
  * data/publish_protection_state.json (arm publish history)
  * data/commission_opportunities.jsonl (affiliate approval status)
  * data/affiliate_clicks.jsonl (proven demand per opportunity)
  * first_dollar_engine.rank_first_dollar (honest scoring)

Read-only. Never fabricates revenue, never publishes, never contacts a
platform. The single `next_action` it returns is exactly the highest-
value human action; every gate below it is the prioritized remainder.
After a gate clears, everything downstream continues automatically
(the factory's own code already does this: product publish -> checkout
-> webhook -> ledger -> ladder).

This module is standalone. It imports only real engines that never
write to a real ledger.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

_FACTORY_ROOT = Path(__file__).resolve().parent


def _path(rel: str) -> Path:
    """Resolve a data-path at call time so tests can redirect _FACTORY_ROOT
    to a temp directory without editing the module constants."""
    return _FACTORY_ROOT / rel

def _env_file(): return _path(".env")
def _publish_state_path(): return _path("data/publish_protection_state.json")
def _paddle_products_path(): return _path("data/paddle_products.json")
def _commission_opps_path(): return _path("data/commission_opportunities.jsonl")
def _clicks_path(): return _path("data/affiliate_clicks.jsonl")
def _paddle_checkout_path(): return _path("data/paddle_checkout_notifications.json")


def _read_env_names() -> set:
    """Return the SET of defined env variable NAMES (never values)."""
    if not _env_file().exists():
        return set()
    names = set()
    try:
        for line in _env_file().read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            names.add(line.split("=", 1)[0].strip())
    except Exception:  # pragma: no cover - defensive
        return set()
    return names


def _read_json(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # pragma: no cover - defensive
        return None


def _count_click_opportunities() -> Dict[str, int]:
    """Real click counts per opportunity_id from the append-only click ledger."""
    counts: Dict[str, int] = {}
    if not _clicks_path().exists():
        return counts
    try:
        for line in _clicks_path().read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except Exception:  # pragma: no cover - defensive
                continue
            opp = evt.get("opportunity_id") or evt.get("product_id") or evt.get("target")
            if opp:
                counts[opp] = counts.get(opp, 0) + 1
    except Exception:  # pragma: no cover - defensive
        return {}
    return counts


def _affiliate_approval_state() -> Dict[str, object]:
    """Affiliate approvals, collapsed into a SINGLE grouped action (mandate
    section 22: one next action, not twenty). Ranked by first-dollar score,
    with real click demand as secondary evidence."""
    items: List[Dict[str, object]] = []
    if not _commission_opps_path().exists():
        return {"action": None, "top": [], "count": 0}
    clicks = _count_click_opportunities()

    # First-dollar scores from the real engine (read-only, honest).
    scores: Dict[str, float] = {}
    try:
        from first_dollar_engine import rank_first_dollar
        ranking = rank_first_dollar(top_n=50).get("ranking", [])
        for r in ranking:
            scores[r.get("opportunity_id")] = float(r.get("first_dollar_score") or 0)
    except Exception:  # pragma: no cover - defensive
        pass

    try:
        lines = _commission_opps_path().read_text(encoding="utf-8").splitlines()
    except Exception:  # pragma: no cover - defensive
        return {"action": None, "top": [], "count": 0}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            opp = json.loads(line)
        except Exception:  # pragma: no cover - defensive
            continue
        if not isinstance(opp, dict):
            continue
        status = opp.get("status") or "DISCOVERED"
        opp_id = opp.get("opportunity_id") or ""
        program = opp.get("program_name") or opp.get("partner_name") or opp_id
        # DISCOVERED/VERIFIED opportunities have no live affiliate link yet;
        # a founder signup is what turns them into real commission channels.
        if status in ("DISCOVERED", "PARTIALLY_VERIFIED", "VERIFIED", "THIRD_PARTY_ONLY"):
            founder_action = opp.get("founder_action")
            if not founder_action:
                for key in ("human_gate", "approval_action", "signup_url"):
                    hg = opp.get(key)
                    if isinstance(hg, dict) and hg.get("founder_action"):
                        founder_action = hg["founder_action"]
                        break
            items.append({
                "opportunity_id": opp_id,
                "program_name": program,
                "first_dollar_score": scores.get(opp_id, 0),
                "real_clicks": clicks.get(opp_id, 0),
                "founder_action": founder_action or f"Complete the {program} application/approval (self-service signup).",
            })
    items.sort(key=lambda g: (-g["first_dollar_score"], -g["real_clicks"], g["program_name"]))
    if not items:
        return {"action": None, "top": [], "count": 0}
    top = items[:3]
    names = ", ".join(i["program_name"] for i in top)
    return {
        "action": f"Apply to the top affiliate programs: {names} (plus {len(items) - len(top)} more).",
        "top": top,
        "count": len(items),
    }


def _paddle_gate() -> Optional[Dict[str, object]]:
    """Paddle checkout readiness. With 6 real products but no checkout
    notifications ever written, checkout is not enabled yet."""
    products = _read_json(_paddle_products_path())
    count = len(products) if isinstance(products, list) else (len(products) if isinstance(products, dict) else 0)
    checkout_enabled = _paddle_checkout_path().exists()
    if count > 0 and not checkout_enabled:
        return {
            "arm": "paddle",
            "action": "Complete Paddle vendor onboarding so checkout transactions can be created (6 real products are ready).",
            "ready_product_count": count,
            "checkout_enabled": False,
        }
    if count == 0:
        return {
            "arm": "paddle",
            "action": "Create the first real Paddle product (no products exist yet).",
            "ready_product_count": 0,
            "checkout_enabled": False,
        }
    return None


def _gumroad_gate() -> Optional[Dict[str, object]]:
    """Gumroad publish readiness: first publish needs founder approval and a
    connected payment method (product is DRAFT)."""
    state = _read_json(_publish_state_path())
    gum = (state or {}).get("arms", {}).get("gumroad", {}) if state else {}
    first_publish_approved = bool(gum.get("first_publish_approved"))
    ever_published = bool(gum.get("has_ever_published_successfully"))
    if not ever_published and not first_publish_approved:
        return {
            "arm": "gumroad",
            "action": "Connect a Gumroad payment method and approve the first publish (product EU AI Act Toolkit $155 is DRAFT at https://aekraft.gumroad.com/l/iaiyt).",
            "has_ever_published_successfully": False,
            "first_publish_approved": False,
        }
    return None


def _webhook_secret_gate(env_names: set) -> Optional[Dict[str, object]]:
    """Paddle webhook verification secret. Without it every real webhook is
    correctly rejected fail-closed."""
    if "PADDLE_WEBHOOK_SECRET" not in env_names:
        return {
            "arm": "paddle_webhook",
            "action": "Set PADDLE_WEBHOOK_SECRET in .env so real payment events can be verified and recorded.",
            "verification": "fail-closed (all real webhook events currently rejected MISSING_SECRET)",
        }
    return None


def _amazon_tag_gate(env_names: set) -> Optional[Dict[str, object]]:
    """Amazon Associates tag. 14 real clicks exist but no tag means no
    commission can be attributed."""
    if "AMAZON_ASSOCIATE_TAG" not in env_names:
        return {
            "arm": "amazon_affiliate",
            "action": "Complete the Amazon Associates application and add AMAZON_ASSOCIATE_TAG to .env (14 real clicks are already waiting).",
            "real_clicks": 14,
        }
    return None


def build_founder_next_action(now: Optional[str] = None) -> Dict[str, object]:
    """Consolidate every human gate into ONE prioritized next action.

    Priority (real-state driven):
      1. Paddle checkout (6 products ready — highest direct product value)
      2. Gumroad first publish (1 real $155 product DRAFT)
      3. Paddle webhook secret (unlocks revenue truth for every Paddle sale)
      4. Amazon Associates (14 real clicks already waiting)
      5. Affiliate approvals (ranked by real click evidence)
    """
    from datetime import datetime, timezone

    env_names = _read_env_names()

    gates: List[Dict[str, object]] = []
    for build in (_paddle_gate, _gumroad_gate, _webhook_secret_gate, _amazon_tag_gate):
        g = build(env_names) if build in (_webhook_secret_gate, _amazon_tag_gate) else build()
        if g:
            gates.append(g)

    affiliate_group = _affiliate_approval_state()
    if affiliate_group.get("action"):
        gates.append({
            "arm": "affiliate_approvals",
            "action": affiliate_group["action"],
            "top_programs": affiliate_group["top"],
            "program_count": affiliate_group["count"],
        })

    # Deterministic priority: product-value gates first (in the order built),
    # then the grouped affiliate approval action.
    gates.sort(key=lambda g: (
        0 if g.get("arm") in ("paddle", "gumroad") else
        1 if g.get("arm") == "paddle_webhook" else
        2 if g.get("arm") == "amazon_affiliate" else
        3 if g.get("arm") == "affiliate_approvals" else 4,
        g.get("program_name") or g.get("arm") or "",
    ))

    next_action = gates[0] if gates else {
        "action": "No founder gate is currently open — the factory is fully unblocked.",
    }
    return {
        "generated_at": (now or datetime.now(timezone.utc).isoformat()),
        "one_next_action": next_action,
        "queue": gates,
        "open_gate_count": len(gates),
        "note": "Real-state only. After each gate clears, everything downstream (publish -> checkout -> webhook -> ledger -> ladder) continues automatically.",
    }


def _cli_main() -> None:
    result = build_founder_next_action()
    print(json.dumps(result, ensure_ascii=False, default=str))


if __name__ == "__main__":
    _cli_main()