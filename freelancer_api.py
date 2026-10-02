"""Freelancer.com integration — read-only public API + fail-closed write path.

Proven live 2026-10-01 (S3-REVENUE-02 audit):
  GET /api/projects/0.1/projects/{id}/  -> 200, no auth, returns
  status / frontend_project_status / budget{min,max} / bid_stats / type.

Write operations (place bid, messages) exist ONLY behind OAuth2 via the
official API (see official freelancer-sdk-python: Session(oauth_token=...)).
This module NEVER prompts for, accepts, stores, or logs a token: if no
token is configured it raises FounderAuthorizationRequired and stops.
Token provisioning is a one-time founder browser action at
https://developers.freelancer.com (app registration + authorize), after
which the token lives ONLY in the local .env (never git, never JSON logs).

Evidence states used: PREPARED / FOUNDER_REPORTED / PLATFORM_VERIFIED.
This module never converts PREPARED -> SUBMITTED on its own.
"""

import json
import urllib.request
import urllib.error

API_BASE = "https://www.freelancer.com/api"
USER_AGENT = "GalaxyForge-readonly-probe/1.0"
TIMEOUT = 30


class FounderAuthorizationRequired(RuntimeError):
    """Raised when an operation needs the founder's one-time OAuth grant."""


class FreelancerAPIError(RuntimeError):
    pass


def _get(path):
    from lib.http import get_json, HttpError

    try:
        body = get_json(API_BASE + path,
                        headers={"User-Agent": USER_AGENT})
    except HttpError as e:
        raise FreelancerAPIError(
            "GET %s -> HTTP %s: %s" % (path, e.code, str(e)[:200])
        )
    if body.get("status") != "success":
        raise FreelancerAPIError("GET %s -> error: %s" % (path, str(body)[:200]))
    return body["result"]


def get_project(project_id):
    """Public, no-auth project read. Returns raw result dict. Evidence: OBSERVED."""
    return _get("/projects/0.1/projects/%d/" % int(project_id))


def _get_with_params(path, params):
    import urllib.parse

    qs = urllib.parse.urlencode(params)
    return _get("%s?%s" % (path, qs))


def search_active(query, limit=10, offset=0):
    """Public project search (no auth). Returns list of raw project dicts."""
    res = _get_with_params(
        "/projects/0.1/projects/active/",
        {"query": query, "limit": int(limit), "offset": int(offset)},
    )
    if isinstance(res, dict):
        return res.get("projects", [])
    return res


def summarize_project(project_id):
    """Minimal verified-facts projection. No inference, no ranking, no WTP claims."""
    p = get_project(project_id)
    budget = p.get("budget") or {}
    stats = p.get("bid_stats") or {}
    return {
        "project_id": int(project_id),
        "title": p.get("title"),
        "status": p.get("status"),
        "sub_status": p.get("sub_status"),
        "frontend_status": p.get("frontend_project_status"),
        "project_type": p.get("type"),
        "budget_min": budget.get("minimum"),
        "budget_max": budget.get("maximum"),
        "bid_count": stats.get("bid_count"),
        "bid_avg": stats.get("bid_avg"),
        "time_submitted": p.get("time_submitted"),
        "evidence": "PLATFORM_VERIFIED (public API, no auth)",
    }


def is_open(summary):
    return summary.get("status") == "active" and summary.get(
        "frontend_status"
    ) in ("open", "active", None)


# Reusable platform logic — lesson S3-DELEGATE-01: PUBLISHED != BIDDABLE.
# A listing page can render while the project is already awarded/closed
# (KDP 40743207 read "In Progress" while sub_status was closed_awarded).
# Every proposal operation must pass is_biddable() first.
CLOSED_SUB_STATUSES = {
    "closed_awarded",
    "closed_completed",
    "closed_expired",
    "closed_cancelled",
    "closed",
}


def biddability(summary):
    """Returns (biddable: bool, reason: str). Pure function of API fields."""
    sub = summary.get("sub_status")
    if sub in CLOSED_SUB_STATUSES:
        return False, "sub_status=%s (awarded/closed/expired)" % sub
    if summary.get("status") != "active":
        return False, "status=%s (not active)" % summary.get("status")
    if summary.get("frontend_status") not in ("open", "active", None):
        return (
            False,
            "frontend_status=%s (not accepting bids)" % summary.get("frontend_status"),
        )
    return True, "active, no closed sub-status, frontend open"


def is_biddable(summary):
    ok, _ = biddability(summary)
    return ok


def select_price(summary, policy_min=30.0, policy_max=250.0):
    """Autonomous price selection inside policy bounds. Returns (price, basis).

    Logic: anchor at the observed market average when it lies inside both the
    buyer budget and the policy range (competitive parity, no undercut race);
    otherwise fall back to the buyer-budget midpoint clipped to policy bounds.
    Deterministic, explainable, no founder input needed.
    """
    avg = summary.get("bid_avg")
    bmin = summary.get("budget_min") or policy_min
    bmax = summary.get("budget_max") or policy_max
    lo = max(policy_min, bmin)
    hi = min(policy_max, bmax)
    if avg is not None and lo <= avg <= hi:
        return round(avg, 2), "market-average parity (avg %.2f inside bounds)" % avg
    mid = round((lo + hi) / 2.0, 2)
    return mid, "buyer-budget midpoint clipped to policy bounds"


def place_bid(project_id, amount, description, token=None):
    """FAIL-CLOSED: raises FounderAuthorizationRequired unless a token is
    explicitly passed by an authorized caller. No token storage here, ever."""
    if not token:
        raise FounderAuthorizationRequired(
            "place_bid(project=%s): no OAuth2 token configured. "
            "One-time founder action required: authorize at "
            "https://developers.freelancer.com and set FREELANCER_OAUTH_TOKEN "
            "in local .env (never in chat, git, or JSON logs)." % project_id
        )
    raise NotImplementedError(
        "Authenticated write path intentionally unwired until the one-time "
        "founder OAuth grant exists. See data/bounded_commercial_policy.json "
        "for the submission preconditions that will gate it."
    )
