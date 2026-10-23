"""Fail-closed YouTube upload/publication state machine (no real transport).

States, in order (a job only ever moves forward one step, or into a failure
state that names what a human must do):

  LOCAL_READY -> QA_PASSED -> AWAITING_AUTHORIZATION -> UPLOAD_IN_PROGRESS
  -> UPLOADED_PRIVATE_OR_UNLISTED -> PROCESSING_VERIFIED
  -> PUBLICATION_AUTHORIZED -> PUBLISHED_VERIFIED

  failures: QA_FAILED, BLOCKED (rights/metadata/authorization), UPLOAD_FAILED
  (retryable with a new authorization), NEEDS_RECONCILIATION (a crash during
  upload: never re-uploaded automatically, a human checks the channel first),
  PROCESSING_FAILED (rejected or failed processing on the platform).

Authorization, in layers, all checked before any transport call:
  * channels.write_gate.require_platform_write("youtube", ...) -- the factory
    switch (FACTORY_LIVE_PUBLISH), false on this machine;
  * upload: a single-use channels.write_scope "upload_file" scope bound to
    product_id "yt:<video sha256>" and the file path, so it authorizes exactly
    this file's bytes once;
  * publication: an approval record (approver + evidence reference) for this
    video's sha AND the platform video id. write_scope deliberately refuses to
    scope "published" (see its issue_scope), so this is a recorded approval,
    not a single-use token -- a disclosed difference in strength.
Uploads are always private or unlisted; going public is only the separate
publication step, and it counts only after a read-back shows "public".

There is no real HTTP transport in this module. The default transport refuses
every call; tests and the offline simulation inject a fake one. Connecting the
real YouTube Data API needs an OAuth client the founder creates -- NOT BUILT.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "data" / "video_publish_jobs.jsonl"

STATES = ("LOCAL_READY", "QA_PASSED", "AWAITING_AUTHORIZATION", "UPLOAD_IN_PROGRESS",
          "UPLOADED_PRIVATE_OR_UNLISTED", "PROCESSING_VERIFIED", "PUBLICATION_AUTHORIZED", "PUBLISHED_VERIFIED")
FAILURE_STATES = ("QA_FAILED", "BLOCKED", "UPLOAD_FAILED", "NEEDS_RECONCILIATION", "PROCESSING_FAILED")
UPLOAD_PRIVACY = ("private", "unlisted")

TITLE_MAX, DESCRIPTION_MAX_BYTES, TAGS_MAX_CHARS = 100, 5000, 500
_SECRET = re.compile(r"(ya29\.[\w\-.]+|1//[\w\-]{20,}|AIza[\w\-]{30,}|(?i:bearer)\s+[\w\-.~+/]{16,}|"
                     r"(?i:client_secret|refresh_token|access_token|api_key)[\"']?\s*[:=]\s*[\"']?[\w\-.~+/]{8,})")


class Refused(RuntimeError):
    """A step was refused before any transport call."""


class TransportNotConfigured(RuntimeError):
    pass


class NoTransport:
    """The default. Real YouTube access is NOT BUILT; every call refuses."""

    def _no(self, *a, **k):
        raise TransportNotConfigured("real YouTube transport NOT BUILT; no network call was made")

    upload = get_status = set_privacy = _no


def redact(text) -> str:
    return _SECRET.sub("[REDACTED]", str(text))


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_metadata(meta: dict) -> list:
    """YouTube's documented limits plus this factory's disclosure rules."""
    errors = []
    title, desc = meta.get("title") or "", meta.get("description") or ""
    if not title.strip():
        errors.append("title is empty")
    if len(title) > TITLE_MAX:
        errors.append(f"title longer than {TITLE_MAX} characters")
    if len(desc.encode("utf-8")) > DESCRIPTION_MAX_BYTES:
        errors.append(f"description longer than {DESCRIPTION_MAX_BYTES} bytes")
    if any(c in title + desc for c in "<>"):
        errors.append("title/description contain < or >, which YouTube rejects")
    tags = meta.get("tags") or []
    if sum(len(t) + (2 if " " in t else 0) for t in tags) + max(0, len(tags) - 1) > TAGS_MAX_CHARS:
        errors.append(f"tags exceed {TAGS_MAX_CHARS} characters")
    if not isinstance(meta.get("made_for_kids"), bool):
        errors.append("made_for_kids must be set explicitly (true/false)")
    if not isinstance(meta.get("contains_synthetic_media"), bool):
        errors.append("contains_synthetic_media must be set explicitly (altered/synthetic content disclosure)")
    if not str(meta.get("category_id", "")).isdigit():
        errors.append("category_id must be a numeric YouTube category id")
    if meta.get("privacy") not in UPLOAD_PRIVACY:
        errors.append(f"upload privacy must be one of {UPLOAD_PRIVACY}; going public is a separate, approved step")
    return errors


class Jobs:
    """Append-only event ledger; a job's state is its last event's state."""

    def __init__(self, ledger=LEDGER, transport=None, clock=time.time):
        self.ledger = Path(ledger)
        self.transport = transport or NoTransport()
        self.clock = clock

    # ---- ledger ----------------------------------------------------------
    def _events(self):
        if not self.ledger.exists():
            return []
        out = []
        for line in self.ledger.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return out

    def _append(self, job_id, state, **fields):
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        ev = {"ts": self.clock(), "job_id": job_id, "state": state}
        ev.update({k: (redact(v) if k in ("error", "reason") and v is not None else v) for k, v in fields.items()})
        with open(self.ledger, "a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        return ev

    def job(self, job_id) -> dict:
        merged = {}
        for ev in self._events():
            if ev["job_id"] == job_id:
                merged.update({k: v for k, v in ev.items() if v is not None})
        return merged

    def calls(self) -> int:
        return sum(1 for e in self._events() if e.get("transport_call"))

    # ---- steps -----------------------------------------------------------
    def register(self, video_path, metadata: dict, rights_manifest: dict) -> str:
        sha = sha256_file(video_path)
        job_id = "VJ-" + sha[:12]
        if self.job(job_id):
            return job_id  # same bytes, same job: idempotent
        self._append(job_id, "LOCAL_READY", video_sha256=sha, video_path=str(video_path),
                     metadata=metadata, rights_status=rights_manifest.get("status"))
        return job_id

    def record_qa(self, job_id, qa_report: dict):
        j = self._require(job_id, "LOCAL_READY", "QA_FAILED")
        if qa_report.get("passed") and qa_report.get("video_sha256") == j["video_sha256"]:
            return self._append(job_id, "QA_PASSED", qa_score=qa_report.get("score"))
        why = "QA report is for different bytes" if qa_report.get("video_sha256") != j["video_sha256"] else "QA did not pass"
        return self._append(job_id, "QA_FAILED", reason=why)

    def request_upload(self, job_id):
        """Checks everything that does not need authorization; parks the job."""
        j = self._require(job_id, "QA_PASSED", "UPLOAD_FAILED", "BLOCKED")
        problems = []
        if j.get("rights_status") != "CLEARED":
            problems.append(f"rights not cleared (status {j.get('rights_status')!r})")
        problems += validate_metadata(j.get("metadata") or {})
        if problems:
            self._append(job_id, "BLOCKED", reason="; ".join(problems))
            raise Refused("; ".join(problems))
        return self._append(job_id, "AWAITING_AUTHORIZATION")

    def upload(self, job_id, scope_id: str):
        j = self.job(job_id)
        if j.get("youtube_video_id"):  # idempotency: these bytes are already on the platform
            return {"state": j["state"], "youtube_video_id": j["youtube_video_id"], "duplicate": True}
        if j.get("state") == "UPLOAD_IN_PROGRESS":
            self._append(job_id, "NEEDS_RECONCILIATION",
                         reason="an earlier upload started and never recorded a result; check the channel before any retry")
            raise Refused("upload outcome unknown; reconcile by hand first")
        self._require(job_id, "AWAITING_AUTHORIZATION")
        from channels import write_gate, write_scope
        write_gate.require_platform_write("youtube", "upload")          # raises WriteNotAuthorized
        d = write_scope.consume_scope(scope_id=scope_id, product_id="yt:" + j["video_sha256"],
                                      payload={"file_path": j["video_path"]}, operation="upload_file")
        if not d.allowed:
            raise Refused(f"upload authorization refused: {d.reason}")
        if sha256_file(j["video_path"]) != j["video_sha256"]:
            self._append(job_id, "BLOCKED", reason="file changed after QA")
            raise Refused("file changed after QA")
        meta = j["metadata"]
        self._append(job_id, "UPLOAD_IN_PROGRESS", transport_call="upload")
        try:
            r = self.transport.upload(j["video_path"], meta)
        except Exception as exc:  # noqa: BLE001 -- any failure is recorded, never swallowed
            self._append(job_id, "UPLOAD_FAILED", error=f"{type(exc).__name__}: {exc}")
            raise
        mismatch = r.get("privacy") != meta["privacy"]
        return self._append(job_id, "UPLOADED_PRIVATE_OR_UNLISTED", youtube_video_id=r["video_id"],
                            platform_privacy=r.get("privacy"),
                            error=(f"platform reports privacy {r.get('privacy')!r}; requested {meta['privacy']!r}"
                                   if mismatch else None))

    def check_processing(self, job_id):
        j = self._require(job_id, "UPLOADED_PRIVATE_OR_UNLISTED")
        self._append(job_id, "UPLOADED_PRIVATE_OR_UNLISTED", transport_call="get_status")
        s = self.transport.get_status(j["youtube_video_id"])
        if s.get("upload_status") in ("failed", "rejected", "deleted"):
            return self._append(job_id, "PROCESSING_FAILED", reason=f"platform status {s.get('upload_status')}: "
                                f"{s.get('failure_reason') or s.get('rejection_reason') or ''}".strip())
        if s.get("upload_status") == "processed":
            return self._append(job_id, "PROCESSING_VERIFIED", platform_privacy=s.get("privacy"))
        return self.job(job_id)  # still processing: stay, check later

    def approve_publication(self, job_id, *, approver: str, evidence: str, youtube_video_id: str):
        """Records a human's approval. Only a person calls this; the loop never does."""
        j = self._require(job_id, "PROCESSING_VERIFIED")
        if not approver.strip() or len(evidence.strip()) < 10:
            raise Refused("publication approval needs an approver and an evidence reference (10+ characters)")
        if youtube_video_id != j["youtube_video_id"]:
            raise Refused("approval names a different platform video")
        return self._append(job_id, "PUBLICATION_AUTHORIZED", approved_by=approver, approval_evidence=evidence)

    def publish(self, job_id):
        j = self._require(job_id, "PUBLICATION_AUTHORIZED")
        from channels import write_gate
        write_gate.require_platform_write("youtube", "set_privacy_public")
        self._append(job_id, "PUBLICATION_AUTHORIZED", transport_call="set_privacy")
        self.transport.set_privacy(j["youtube_video_id"], "public")
        self._append(job_id, "PUBLICATION_AUTHORIZED", transport_call="get_status")
        s = self.transport.get_status(j["youtube_video_id"])
        if s.get("privacy") == "public" and s.get("upload_status") == "processed":
            return self._append(job_id, "PUBLISHED_VERIFIED", platform_privacy="public")
        return self._append(job_id, "PUBLICATION_AUTHORIZED",
                            error=f"read-back shows privacy {s.get('privacy')!r}; not counted as published")

    def _require(self, job_id, *allowed):
        j = self.job(job_id)
        if not j:
            raise Refused(f"unknown job {job_id}")
        if j["state"] not in allowed:
            raise Refused(f"job is {j['state']}, step needs {' or '.join(allowed)}")
        return j
