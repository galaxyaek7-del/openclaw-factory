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
    req = urllib.request.Request(
        API_BASE + path, headers={"User-Agent": USER_AGENT}
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise FreelancerAPIError(
            "GET %s -> HTTP %s: %s" % (path, e.code, e.read().decode()[:200])
        )
    if body.get("status") != "success":
        raise FreelancerAPIError("GET %s -> error: %s" % (path, str(body)[:200]))
    return body["result"]


def get_project(project_id):
    """Public, no-auth project read. Returns raw result dict. Evidence: OBSERVED."""
    return _get("/projects/0.1/projects/%d/" % int(project_id))


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
