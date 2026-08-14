"""Founder approval gates (Universal Production Engine Roadmap Step 4,
2026-07-19): a real, current-state-driven answer to "what needs founder
action before this can publish for real" — computed from every
registered arm's own real status(), never a hardcoded narrative about
one platform's business status. Business state changes (a founder
finishing Paddle's onboarding, adding a missing token) and a fixed
comment claiming otherwise would just go stale — status() is the single
source of truth, the same one distributor.py already reads before every
real publish attempt.

Payoneer is deliberately absent here: it is the founder's own payout/
withdrawal rail configured inside Paddle/Gumroad's own settings, not a
distribution channel this factory publishes to (confirmed repeatedly —
see IDENTITY_ARCHITECTURE.md/ADR-014) — there is no "PayoneerArm" to gate.
"""

from channels import registry as channel_registry
from channels.base_arm import ArmStatus

_GATE_REASONS = {
    ArmStatus.UNAVAILABLE: (
        "credentials missing or invalid — founder must add/fix the real API credential in .env"
    ),
    ArmStatus.COOLDOWN: (
        "repeated real publish failures tripped the circuit breaker — founder should check the "
        "real error (channels/ledger.py's publish_attempt events); it clears itself once a "
        "publish succeeds again"
    ),
}


def check_approval_gates():
    """Real, computed split: which registered arms are already usable
    autonomously (status == READY) vs which need founder action right
    now, and why. Never fabricates readiness for an arm that hasn't
    proven it — status() is the same real check distributor.py already
    uses to decide whether to even attempt a publish."""
    gated = []
    autonomous = []
    for arm in channel_registry.all_arms():
        status = arm.status()
        if status == ArmStatus.READY:
            autonomous.append({"marketplace": arm.name, "status": status.value})
        else:
            gated.append({
                "marketplace": arm.name,
                "status": status.value,
                "reason": _GATE_REASONS.get(status, "not ready — see arm.status() for detail"),
            })
    return {"gated": gated, "autonomous": autonomous}
