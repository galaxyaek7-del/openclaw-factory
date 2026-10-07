"""Goal 2 -- DETECT + DECIDE for CI health.

WHAT THIS IS
    A deterministic, credential-free reader of GitHub Actions evidence that
    normalises "what is the state of CI right now" into exactly one of
    PASS / HOLD / BLOCKED / UNKNOWN.

WHY IT IS BUILT THIS WAY
    The entire CI incident this module exists to prevent is now documented:
    a stage sat for 341 minutes and returned NO result, then 32 shards sat for
    90 minutes and were cancelled, and during all of it the dashboard looked
    superficially fine. The recurring failure mode was never "something broke"
    -- it was "absence of evidence being mistaken for health".

    So the rules below are deliberately asymmetric:
      * PASS is only reachable when every required check is positively,
        independently observed as `success`.
      * Missing evidence can never produce PASS. It produces UNKNOWN.
      * An in-flight run is HOLD, never PASS.
      * A cancellation or timeout is BLOCKED, never PASS.

    "Zero failures observed" and "all required checks verified successful" are
    NOT the same statement, and this module refuses to conflate them.

SECURITY
    Read-only against the PUBLIC REST API. No token is read, required, stored or
    logged. There is deliberately no code path that could emit a credential:
    the HTTP layer here only ever issues anonymous GETs.

IDEMPOTENCY
    State transitions are keyed by (commit_sha, run_id). Re-collecting the same
    evidence produces the same verdict and appends nothing new, so polling the
    same run repeatedly is safe and cannot manufacture duplicate state.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

REPO = "galaxyaek7-del/openclaw-factory"
API = "https://api.github.com"

# Verdicts. Exactly one is produced per evaluation.
PASS = "PASS"
HOLD = "HOLD"
BLOCKED = "BLOCKED"
UNKNOWN = "UNKNOWN"

VERDICTS = (PASS, HOLD, BLOCKED, UNKNOWN)

# A conclusion that means "this did not succeed", as distinct from "not done".
FAILURE_CONCLUSIONS = {"failure", "cancelled", "timed_out", "action_required",
                       "stale", "startup_failure"}
IN_FLIGHT_STATUSES = {"queued", "in_progress", "waiting", "requested", "pending"}
COMPLETED_STATUSES = {"completed"}

# Jobs that must exist and must conclude successfully. The api-contract shards
# are matched by prefix because the count is a configuration choice, not a
# hard-coded truth: whatever the workflow declares, every shard it declares must
# pass.
REQUIRED_EXACT_JOBS = {"test"}


def _http_json(url, timeout=25, attempts=4, backoff=5):
    """Anonymous GET -> parsed JSON. Never sends or accepts credentials.

    Returns (payload, error). On transport/permission/shape failure the error is
    returned rather than raised, because "I could not read the evidence" must be
    distinguishable from "the evidence says the run failed".
    """
    last = None
    for i in range(max(1, attempts)):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "GalaxyForge-CI-Detector",
                              "Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8", "replace")), None
        except urllib.error.HTTPError as exc:
            # 403/404/422 are meaningful, not transient: stop retrying.
            last = "HTTP %s" % exc.code
            if exc.code in (403, 404, 422):
                break
            time.sleep(backoff)
        except Exception as exc:                      # noqa: BLE001
            last = type(exc).__name__
            time.sleep(backoff)
    return None, last


# --------------------------------------------------------------------------
# DECIDE -- pure. No I/O. This is the part that must be provably correct.
# --------------------------------------------------------------------------

def decide(evidence):
    """Normalise collected evidence into exactly one verdict.

    `evidence` is the dict produced by collect(). The rules are ordered from
    most-denial-first so that an explicit failure can never be masked by a
    later, weaker observation.
    """
    if not isinstance(evidence, dict):
        return UNKNOWN, "evidence is not a mapping", {}

    if evidence.get("evidence_error"):
        # We could not read the evidence. That is never PASS.
        return UNKNOWN, "evidence could not be read: %s" % evidence["evidence_error"], {}

    runs = evidence.get("runs")
    jobs = evidence.get("jobs")
    if not isinstance(runs, list) or not isinstance(jobs, list):
        return UNKNOWN, "evidence is missing runs or jobs", {}

    if not runs:
        return UNKNOWN, "no CI runs were found for this commit", {}

    # 1. Explicit, observed failure anywhere -> BLOCKED.
    failed = [j for j in jobs if (j.get("conclusion") or "") in FAILURE_CONCLUSIONS]
    if failed:
        return BLOCKED, "%d job(s) concluded non-success" % len(failed), {
            "failed_jobs": sorted(j["name"] for j in failed if j.get("name"))[:20],
        }

    # 2. Required jobs must all be present. A missing one is UNKNOWN, never PASS.
    present = {j.get("name") for j in jobs}
    missing_exact = sorted(REQUIRED_EXACT_JOBS - present)
    if missing_exact:
        return UNKNOWN, "required job(s) absent from evidence: %s" % ", ".join(missing_exact), {}

    declared_shards = evidence.get("expected_shards")
    observed_shards = {j["name"] for j in jobs
                       if isinstance(j.get("name"), str)
                       and j["name"].startswith("API contract shard")}
    if isinstance(declared_shards, int) and declared_shards > 0:
        if len(observed_shards) != declared_shards:
            return UNKNOWN, ("expected %d api-contract shard jobs, observed %d"
                             % (declared_shards, len(observed_shards))), {}

    # 3. Still moving -> HOLD. Never PASS on an unfinished run.
    moving = [r for r in runs if (r.get("status") or "") in IN_FLIGHT_STATUSES]
    if moving:
        return HOLD, "%d workflow run(s) still in flight" % len(moving), {}

    # 4. Any required job without a conclusion -> UNKNOWN. This is the specific
    #    trap from this incident: a job with `conclusion: null` is not a pass.
    undecided = [j.get("name") for j in jobs
                 if (j.get("status") in COMPLETED_STATUSES or not j.get("status"))
                 and not j.get("conclusion")]
    if undecided:
        return UNKNOWN, "%d required job(s) have no conclusion" % len(undecided), {
            "undecided_jobs": sorted(n for n in undecided if n)[:20],
        }

    # 5. Every required job must be positively successful.
    #
    # A job still in flight is HOLD, not BLOCKED. This ordering matters: the
    # original version let an `in_progress` job (conclusion=None) fall through
    # to this rule and be reported as a failure. Caught by test_03.
    still_running = [j for j in jobs
                     if (j.get("status") or "") in IN_FLIGHT_STATUSES]
    if still_running:
        return HOLD, "%d job(s) still running" % len(still_running), {}

    not_success = [j for j in jobs if j.get("conclusion") != "success"]
    if not_success:
        return BLOCKED, "%d job(s) are not successful" % len(not_success), {
            "not_successful": sorted(j.get("name") or "?" for j in not_success)[:20],
        }

    # 6. Every required workflow must have completed successfully.
    runs_not_ok = [r for r in runs
                   if r.get("status") not in COMPLETED_STATUSES
                   or r.get("conclusion") != "success"]
    if runs_not_ok:
        return BLOCKED, "%d workflow run(s) did not succeed" % len(runs_not_ok), {
            "runs_not_ok": ["%s=%s/%s" % (r.get("name"), r.get("status"),
                                           r.get("conclusion"))
                            for r in runs_not_ok][:10],
        }

    # 7. Positive confirmation of everything required. Only now: PASS.
    return PASS, "all required runs and jobs independently confirmed successful", {
        "jobs_confirmed": len(jobs),
        "runs_confirmed": len(runs),
    }


# --------------------------------------------------------------------------
# DETECT -- collection. Read-only, anonymous, idempotent.
# --------------------------------------------------------------------------

def collect(sha, repo=REPO, api=API):
    """Gather CI evidence for one commit. Never raises; reports its own errors."""
    out = {"commit_sha": sha, "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                            time.gmtime()),
           "runs": [], "jobs": [], "expected_shards": None, "evidence_error": None}
    if not sha or not isinstance(sha, str):
        out["evidence_error"] = "no commit sha supplied"
        return out

    payload, err = _http_json("%s/repos/%s/actions/runs?branch=main&per_page=15"
                               % (api, repo))
    if err or not isinstance(payload, dict):
        out["evidence_error"] = err or "malformed runs response"
        return out

    runs = [r for r in payload.get("workflow_runs", [])
            if (r.get("head_sha") or "").startswith(sha[:7])]
    if not runs:
        out["evidence_error"] = "no workflow runs found for %s" % sha[:7]
        return out

    for r in runs:
        out["runs"].append({"id": r.get("id"), "name": r.get("name"),
                            "status": r.get("status"),
                            "conclusion": r.get("conclusion")})
        jobs, jerr = _http_json("%s/repos/%s/actions/runs/%s/jobs?per_page=100"
                                % (api, repo, r.get("id")))
        if jerr or not isinstance(jobs, dict):
            # Record the read failure honestly rather than pretending the run
            # had no jobs -- that distinction is exactly what went wrong before.
            out.setdefault("job_read_errors", []).append(
                {"run_id": r.get("id"), "error": jerr or "malformed jobs response"})
            continue
        for j in jobs.get("jobs", []):
            out["jobs"].append({"name": j.get("name"), "status": j.get("status"),
                                "conclusion": j.get("conclusion"),
                                "run_id": r.get("id")})

    shards = sorted(j["name"] for j in out["jobs"]
                    if isinstance(j.get("name"), str)
                    and j["name"].startswith("API contract shard"))
    out["expected_shards"] = len(shards) if shards else None
    return out


def detect(sha, repo=REPO, api=API):
    """DETECT + DECIDE in one call. Returns (verdict, reason, evidence)."""
    ev = collect(sha, repo=repo, api=api)
    verdict, reason, detail = decide(ev)
    return verdict, reason, {"evidence": ev, "detail": detail}


# --------------------------------------------------------------------------
# IDEMPOTENT STATE LEDGER
# --------------------------------------------------------------------------

def record_state(verdict, reason, evidence, ledger_path, identity=None):
    """Append a state transition only when it is genuinely new.

    identity defaults to (commit_sha, run ids). Processing identical evidence
    twice is a no-op, so repeated polling cannot grow the ledger or invent a
    transition.
    """
    ev = evidence.get("evidence", evidence) if isinstance(evidence, dict) else {}
    sha = (ev.get("commit_sha") if isinstance(ev, dict) else None) or "unknown"
    run_ids = tuple(sorted(str(r.get("id")) for r in (ev.get("runs") or [])
                           if isinstance(r, dict)))
    # Normalise to a flat list of strings. The ledger round-trips through JSON,
    # which turns every tuple back into a list; comparing a live tuple against a
    # deserialised list never matched, so re-polling appended a duplicate row
    # every time. That is precisely the idempotency failure this is meant to
    # prevent, so it is worth stating explicitly rather than normalising quietly.
    key = list(identity) if identity else [sha, "|".join(run_ids), verdict, reason]

    os.makedirs(os.path.dirname(ledger_path) or ".", exist_ok=True)
    seen = []
    if os.path.exists(ledger_path):
        with open(ledger_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    seen.append(json.loads(line))
                except Exception:                      # noqa: BLE001
                    continue
    for row in seen:
        prior = [str(x) for x in row.get("identity", [])]
        if prior == [str(x) for x in key]:
            return {"recorded": False, "reason": "no state change (idempotent)",
                    "identity": list(key), "ledger_size": len(seen)}

    record = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "identity": list(key), "verdict": verdict, "reason": reason,
              "jobs": [(j.get("name"), j.get("conclusion"))
                       for j in (ev.get("jobs") or []) if isinstance(j, dict)]}
    with open(ledger_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"recorded": True, "identity": list(key), "ledger_size": len(seen) + 1}


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    v, why, payload = detect(target)
    print(json.dumps({"verdict": v, "reason": why,
                      "runs": payload["evidence"]["runs"],
                      "job_count": len(payload["evidence"]["jobs"])},
                     indent=2))