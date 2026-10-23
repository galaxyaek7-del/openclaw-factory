"""Resumable campaign pipeline: job ledger, adapters, approval, publication, verification.

Stages (job states):
  CONTENT_CREATED -> QA_PASSED | QA_FAILED -> APPROVED -> HANDOFF_READY (manual) | QUEUED (API)
  -> PUBLISHING -> PUBLISHED_UNVERIFIED -> PUBLISHED_VERIFIED
  MANUAL_POSTED_UNVERIFIED     a person posted it and recorded the URL; no platform read-back
  side states: STALE (offer changed after drafting), BLOCKED (gate, credentials, permission,
  spend), RATE_LIMITED (retry_at), FAILED_RETRYABLE, FAILED (attempts exhausted),
  NEEDS_RECONCILIATION (a crash while publishing: never retried automatically)

The ledger is append-only JSONL; a job's state is its last event. job_id is a
hash of offer, platform and content, so the same draft is one job and can never
be published twice. Retries are bounded (MAX_ATTEMPTS) with a recorded backoff
time; nothing sleeps. A platform's failure never touches another platform's jobs.
Approval is a recorded human decision; the loop never calls approve() or publish().
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from social_distribution import platforms as plat

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "data" / "social_campaign_jobs.jsonl"
HANDOFF_DIR = ROOT / "data" / "social_handoff"
MAX_ATTEMPTS = 3
BACKOFF_S = (60, 300, 1800)


class Refused(RuntimeError):
    pass


# ---- adapter errors (what a real transport would raise) -------------------
class AdapterError(RuntimeError):
    retryable = False


class RateLimited(AdapterError):
    retryable = True

    def __init__(self, retry_after_s=900, msg="rate limited"):
        super().__init__(msg)
        self.retry_after_s = retry_after_s


class TransientError(AdapterError):
    retryable = True


class PermissionDenied(AdapterError):
    pass


class CredentialsMissing(AdapterError):
    pass


class SpendRequired(AdapterError):
    pass


class TransportNotBuilt(AdapterError):
    pass


class Adapter:
    """One per platform. No real transport exists; publish refuses unless a
    transport is injected (tests, or a future founder-approved client)."""

    def __init__(self, platform, transport=None, readiness=None):
        self.platform = platform
        self.transport = transport
        self.readiness = readiness if readiness is not None else plat.readiness()[platform]

    def capability(self):
        return dict(plat.PLATFORMS[self.platform], readiness=self.readiness)

    def mode(self):
        return "API" if self.transport is not None else "MANUAL_HANDOFF"

    def publish(self, draft):
        if self.readiness["state"] == plat.BLOCKED_SPEND:
            raise SpendRequired(f"{self.platform}: posting needs paid API credits; TOTAL_NEW_SPEND=$0")
        if self.readiness["missing_credentials"]:
            raise CredentialsMissing(f"{self.platform}: missing {self.readiness['missing_credentials']}")
        if self.transport is None:
            raise TransportNotBuilt(f"{self.platform}: no publish transport is built; use the manual hand-off")
        return self.transport.publish(self.platform, draft)

    def verify(self, post_id):
        if self.transport is None:
            raise TransportNotBuilt(f"{self.platform}: no read-back transport")
        return self.transport.get(self.platform, post_id)


class Jobs:
    def __init__(self, ledger=LEDGER, handoff_dir=HANDOFF_DIR, adapters=None, clock=time.time):
        self.ledger = Path(ledger)
        self.handoff_dir = Path(handoff_dir)
        self.adapters = adapters or {}
        self.clock = clock

    # ---- ledger ----
    def events(self):
        if not self.ledger.exists():
            return []
        out = []
        for line in self.ledger.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
        return out

    def _append(self, job_id, state, **kw):
        from video_studio.youtube_upload import redact  # one shared secret redactor
        ev = {"ts": self.clock(), "job_id": job_id, "state": state}
        ev.update({k: (redact(v) if k in ("error", "reason") and v is not None else v) for k, v in kw.items()})
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ledger, "a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        return ev

    def job(self, job_id):
        merged = {}
        for ev in self.events():
            if ev["job_id"] == job_id:
                merged.update({k: v for k, v in ev.items() if v is not None})
        return merged

    def jobs(self):
        ids = []
        for ev in self.events():
            if ev["job_id"] not in ids:
                ids.append(ev["job_id"])
        return [self.job(i) for i in ids]

    def adapter(self, platform):
        if platform not in self.adapters:
            self.adapters[platform] = Adapter(platform)
        return self.adapters[platform]

    # ---- stages ----
    @staticmethod
    def job_id_for(draft):
        key = f"{draft['offer_id']}|{draft['platform']}|{draft['content_sha256']}"
        return "SJ-" + hashlib.sha256(key.encode()).hexdigest()[:12]

    def add_draft(self, draft):
        jid = self.job_id_for(draft)
        if self.job(jid):
            return jid  # same content for the same offer and platform: one job
        self._append(jid, "CONTENT_CREATED", offer_id=draft["offer_id"], arm=draft["arm"], platform=draft["platform"],
                     campaign=draft["campaign"], link=draft["link"], content_sha256=draft["content_sha256"],
                     draft=draft, offer_snapshot=draft["offer_snapshot"])
        if draft["qa"]["passed"]:
            self._append(jid, "QA_PASSED")
        else:
            self._append(jid, "QA_FAILED", reason="; ".join(draft["qa"]["issues"]), qa_issues=draft["qa"]["issues"])
        return jid

    def approve(self, jid, *, approver, evidence):
        """A person's decision, recorded with evidence. Never called by automation."""
        self._require(jid, "QA_PASSED")
        if not approver.strip() or len(evidence.strip()) < 10:
            raise Refused("approval needs an approver and an evidence reference (10+ characters)")
        return self._append(jid, "APPROVED", approved_by=approver, approval_evidence=evidence)

    def queue(self, jid):
        """Approved jobs go to the platform's API queue, or become a hand-off package."""
        j = self._require(jid, "APPROVED")
        a = self.adapter(j["platform"])
        if a.mode() == "MANUAL_HANDOFF":
            path = self.handoff_dir / f"{jid}.md"
            self.handoff_dir.mkdir(parents=True, exist_ok=True)
            d = j["draft"]
            body = [f"# Hand-off {jid}: {j['platform']} post for {j['offer_id']}", "",
                    "Post this by hand from the authorized account, then record the post URL with "
                    "`Jobs.record_manual_post(job_id, post_url=..., posted_by=...)`.", "",
                    f"Destination (tracked): {j['link']}", "", "## Text", "", d["fields"].get("text", "")]
            for k, v in d["fields"].items():
                if k != "text":
                    body += ["", f"## {k}", "", json.dumps(v, indent=1, ensure_ascii=False)]
            if d.get("visual"):
                body += ["", "## Visual", "", json.dumps(d["visual"], ensure_ascii=False)]
            path.write_text("\n".join(body) + "\n", encoding="utf-8")
            return self._append(jid, "HANDOFF_READY", handoff=str(path))
        return self._append(jid, "QUEUED")

    def publish(self, jid, current_offer):
        j = self.job(jid)
        if j.get("state") == "PUBLISHING":
            self._append(jid, "NEEDS_RECONCILIATION",
                         reason="an earlier publish never recorded a result; check the platform before any retry")
            raise Refused("publish outcome unknown; reconcile first")
        if j.get("state") in ("PUBLISHED_UNVERIFIED", "PUBLISHED_VERIFIED", "MANUAL_POSTED_UNVERIFIED"):
            return {"state": j["state"], "duplicate": True}
        j = self._require(jid, "QUEUED", "FAILED_RETRYABLE", "RATE_LIMITED")
        if j.get("retry_at") and self.clock() < j["retry_at"] and j["state"] in ("FAILED_RETRYABLE", "RATE_LIMITED"):
            raise Refused(f"not before {j['retry_at']}")
        snap = j["offer_snapshot"]
        if (current_offer.get("url"), current_offer.get("price_cents")) != (snap["url"], snap["price_cents"]) \
                or current_offer.get("eligibility", {}).get("status") != "ELIGIBLE":
            self._append(jid, "STALE", reason="offer changed or is no longer eligible since the draft; redraft")
            raise Refused("offer changed since drafting")
        from channels import write_gate
        decision = write_gate.check_platform_write(j["platform"], "post")
        if not decision.allowed:
            self._append(jid, "BLOCKED", reason=decision.reason)
            raise Refused(decision.reason)
        attempts = j.get("attempts", 0) + 1
        self._append(jid, "PUBLISHING", attempts=attempts, transport_call="publish")
        try:
            r = self.adapter(j["platform"]).publish(j["draft"])
        except RateLimited as e:
            return self._append(jid, "RATE_LIMITED", error=str(e), retry_at=self.clock() + e.retry_after_s, attempts=attempts)
        except AdapterError as e:
            if e.retryable and attempts < MAX_ATTEMPTS:
                return self._append(jid, "FAILED_RETRYABLE", error=f"{type(e).__name__}: {e}", attempts=attempts,
                                    retry_at=self.clock() + BACKOFF_S[attempts - 1])
            state = "FAILED" if e.retryable else "BLOCKED"
            return self._append(jid, state, error=f"{type(e).__name__}: {e}", attempts=attempts)
        self._append(jid, "PUBLISHED_UNVERIFIED", post_id=r.get("post_id"), post_url=r.get("url"), attempts=attempts)
        return self.verify(jid)

    def verify(self, jid):
        """A post counts only when a read-back shows it public and live."""
        j = self._require(jid, "PUBLISHED_UNVERIFIED")
        try:
            r = self.adapter(j["platform"]).verify(j["post_id"])
        except AdapterError as e:
            return self._append(jid, "PUBLISHED_UNVERIFIED", error=f"verification failed: {e}")
        if r.get("visible") is True and r.get("public") is True:
            return self._append(jid, "PUBLISHED_VERIFIED", verified_url=r.get("url"))
        return self._append(jid, "PUBLISHED_UNVERIFIED", error=f"read-back not public/visible: {r}")

    def record_manual_post(self, jid, *, post_url, posted_by):
        """The founder posted the hand-off. Recorded, but unverified: no read-back exists."""
        self._require(jid, "HANDOFF_READY")
        if not str(post_url).startswith("https://") or not posted_by.strip():
            raise Refused("needs the https post URL and who posted it")
        return self._append(jid, "MANUAL_POSTED_UNVERIFIED", post_url=post_url, posted_by=posted_by)

    def _require(self, jid, *allowed):
        j = self.job(jid)
        if not j:
            raise Refused(f"unknown job {jid}")
        if j["state"] not in allowed:
            raise Refused(f"job is {j['state']}, step needs {' or '.join(allowed)}")
        return j

    def summary(self):
        from collections import Counter
        js = self.jobs()
        return {"jobs": len(js), "by_state": dict(Counter(j["state"] for j in js)),
                "by_platform": dict(Counter(j["platform"] for j in js)),
                "published_verified": sum(1 for j in js if j["state"] == "PUBLISHED_VERIFIED")}
