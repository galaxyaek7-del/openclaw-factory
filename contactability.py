"""Contactability scoring (S3-LOOP-04). Internal execution filter, never a
claim about people. Applied AFTER Quality Gate fit assessment.

C3 = owner/channel clearly reachable (owned key, public reply allowed)
C2 = partially reachable (login wall but pack-ready for founder session)
C1 = demand visible, access weak (anonymous platform buyers)
C0 = no practical route.
"""
C3, C2, C1, C0 = 3, 2, 1, 0


def score(opportunity):
    """opportunity: {source, contact_route, needs_auth}. Returns (Cx, reason)."""
    route = (opportunity.get("contact_route") or "").lower()
    source = (opportunity.get("source") or "").lower()
    if opportunity.get("needs_auth") is False and route in (
            "nostr-reply", "owned-session", "public-form-instant"):
        return C3, "direct send-capable route"
    if "founder" in route or opportunity.get("needs_auth") is True:
        return C2, "pack-ready, needs founder session"
    if source in ("freelancer", "marketplace") or "anonymous" in route:
        return C1, "demand visible, buyers behind platform wall"
    return C0, "no practical route"


def priority(fit, contact):
    """fit: HIGH/MEDIUM/LOW. Returns rank tuple (lower is better)."""
    fit_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(fit, 3)
    return (fit_rank, -contact)
