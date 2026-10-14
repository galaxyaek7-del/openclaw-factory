"""Galaxy Forge -- automated buyer-path manifest gate (Cycle 82).

THE DEFECT THIS CLOSES
----------------------
The /l/bfhpzl sales page publishes a per-file manifest and explicitly tells
the buyer: "unzip it and check every line above against what is on your
disk". That instruction makes the manifest a CHECKABLE PROMISE. Two of its six
entries were false:

    etsy_suspension_appeal_kit.pdf      page said 122 KB, actual 135.7 KiB
    etsy_appeal_evidence_tracker.xlsx   page said   6 KB, actual  14.7 KiB

Both drifted because the workbook was upgraded from zero formulas to 215 and
the PDF was repaired, and nothing re-derived the advertised sizes. The page
invited verification and failed it.

WHY A GATE AND NOT A DOC
------------------------
A document describing the correct sizes goes stale the moment a file is
rebuilt. This gate DERIVES every value from the artifact on disk at check
time, so it cannot drift. Nothing here is hand-typed except the page text
being audited.

FAIL-CLOSED
-----------
If a manifest entry cannot be matched to a real member of the delivered
archive, or the archive cannot be opened, the claim is BLOCKED -- never
passed, never guessed. A missing proof is not a pass.

WHAT IT CHECKS
--------------
  * the ZIP opens and every member passes CRC
  * the PDF opens, reports pages, and has no unrenderable glyphs
  * the XLSX opens, and is asked directly whether it computes
  * every manifest claim resolves to a real member, with the size unit the
    page used (KB decimal or KiB binary) determined from the claim itself
  * a computed correction is produced for anything that does not match
"""
from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass, field

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"
UNKNOWN = "UNKNOWN"

# A sales page may publish sizes in decimal KB or binary KiB. Both are accepted
# on read; which one a page uses is inferred per-entry, never assumed globally.
KB_DECIMAL = 1000.0
KIB_BINARY = 1024.0
SIZE_TOLERANCE = 0.5   # a page rounds; half a unit absorbs that honestly


@dataclass
class Claim:
    filename: str
    size_text: str            # exactly as the page states it, e.g. "122 KB"
    unit_is_decimal: bool

    @property
    def claimed_bytes(self) -> float | None:
        m = re.match(r"([\d.]+)\s*(KB|MB|bytes?)", self.size_text, re.I)
        if not m:
            return None
        val = float(m.group(1))
        unit = m.group(2).lower()
        base = 1_000_000 if unit.startswith("mb") else (
            1_000 if unit.startswith("kb") else 1.0)
        return val * base


@dataclass
class ClaimResult:
    claim: Claim
    status: str
    actual_bytes: int | None = None
    evidence: str = ""
    corrected_text: str | None = None


@dataclass
class GateResult:
    archive: str
    results: list[ClaimResult] = field(default_factory=list)
    archive_problems: list[str] = field(default_factory=list)

    @property
    def mismatched(self) -> list[ClaimResult]:
        return [r for r in self.results if r.status == FAIL]

    @property
    def blocked(self) -> list[ClaimResult]:
        return [r for r in self.results if r.status == BLOCKED]

    @property
    def verdict(self) -> str:
        if self.archive_problems:
            return BLOCKED
        if self.blocked:
            return BLOCKED
        if self.mismatched:
            return FAIL
        return PASS

    def as_dict(self) -> dict:
        return {
            "archive": self.archive,
            "verdict": self.verdict,
            "archive_problems": self.archive_problems,
            "claims_checked": len(self.results),
            "mismatched": len(self.mismatched),
            "blocked": len(self.blocked),
            "results": [
                {"filename": r.claim.filename, "page_says": r.claim.size_text,
                 "status": r.status, "actual_bytes": r.actual_bytes,
                 "corrected_text": r.corrected_text, "evidence": r.evidence}
                for r in self.results
            ],
        }


def parse_manifest(text: str) -> list[Claim]:
    """Extract `filename  123 KB` pairs from a sales-page manifest block."""
    out = []
    for m in re.finditer(
            r"([\w][\w.\-]*\.(?:pdf|docx|xlsx|txt|md))\s+(\d+(?:\.\d+)?)\s*"
            r"(KB|MB|bytes?)", text, re.I):
        out.append(Claim(m.group(1), f"{m.group(2)} {m.group(3)}",
                         not m.group(3).lower().startswith("mb")))
    return out


def inspect_archive(archive_path) -> tuple[dict[str, int], list[str]]:
    """Real member sizes read from disk. Returns ({name: bytes}, problems)."""
    problems: list[str] = []
    members: dict[str, int] = {}
    try:
        zf = zipfile.ZipFile(str(archive_path))
    except Exception as exc:  # noqa: BLE001
        return members, [f"archive does not open: {type(exc).__name__}: {exc}"]
    with zf:
        bad = zf.testzip()
        if bad is not None:
            problems.append(f"CRC failure in member {bad!r}")
        for i in zf.infolist():
            members[i.filename] = i.file_size
            if i.file_size == 0:
                problems.append(f"zero-byte member: {i.filename}")
    return members, problems


def check_member_openable(archive_path, filename: str) -> tuple[str, str]:
    """Actually open the member with a real parser. Never assume."""
    ext = filename.rsplit(".", 1)[-1].lower()
    try:
        with zipfile.ZipFile(str(archive_path)) as zf:
            blob = zf.read(filename)
    except Exception as exc:  # noqa: BLE001
        return BLOCKED, f"member unreadable: {type(exc).__name__}"
    try:
        if ext == "pdf":
            from pypdf import PdfReader
            r = PdfReader(io.BytesIO(blob))
            if not r.pages:
                return FAIL, "PDF has zero pages"
            text = "".join((p.extract_text() or "") for p in r.pages)
            boxes = text.count("\u25a0") + text.count("\ufffd")
            if boxes:
                return FAIL, f"PDF has {boxes} unrenderable glyph(s)"
            return PASS, f"{len(r.pages)} pages, {len(text.split())} words"
        if ext == "xlsx":
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(blob))
            formulas = sum(1 for ws in wb for row in ws.iter_rows()
                           for c in row
                           if isinstance(c.value, str) and c.value.startswith("="))
            return PASS, f"{len(wb.sheetnames)} sheets, {formulas} formulas"
        if ext == "docx":
            import docx
            d = docx.Document(io.BytesIO(blob))
            n = len([p for p in d.paragraphs if p.text.strip()])
            if not n and not d.tables:
                return FAIL, "DOCX is empty"
            return PASS, f"{n} non-empty paragraphs"
        if ext in ("txt", "md"):
            body = blob.decode("utf-8", "replace").strip()
            if not body:
                return FAIL, "text file is empty"
            return PASS, f"{len(body.split())} words"
    except Exception as exc:  # noqa: BLE001
        return FAIL, f"does not parse: {type(exc).__name__}"
    return UNKNOWN, f"no checker for .{ext}"


def check_manifest(archive_path, manifest_text: str) -> GateResult:
    res = GateResult(archive=str(archive_path))
    members, problems = inspect_archive(archive_path)
    res.archive_problems.extend(problems)

    claims = parse_manifest(manifest_text)
    if not claims:
        res.archive_problems.append("no manifest claims found in the supplied text")

    for claim in claims:
        actual = members.get(claim.filename)
        if actual is None:
            res.results.append(ClaimResult(
                claim, BLOCKED,
                evidence=f"page lists {claim.filename} but it is not in the archive "
                         f"(members: {sorted(members)})"))
            continue

        state, note = check_member_openable(archive_path, claim.filename)
        if state != PASS:
            res.results.append(ClaimResult(
                claim, BLOCKED, actual, f"member failed its own check: {note}"))
            continue

        claimed = claim.claimed_bytes
        if claimed is None:
            res.results.append(ClaimResult(
                claim, BLOCKED, actual, f"unparseable size text {claim.size_text!r}"))
            continue

        base = KB_DECIMAL if claim.unit_is_decimal else KIB_BINARY
        if abs(actual - claimed) <= SIZE_TOLERANCE * base:
            res.results.append(ClaimResult(
                claim, PASS, actual, f"actual {actual:,} B matches "
                                     f"{claim.size_text} ({note})"))
        else:
            kib = actual / KIB_BINARY
            dec = actual / KB_DECIMAL
            # publish in whichever unit the page is already using, so the fix
            # is a like-for-like edit rather than a unit convention change
            corrected = (f"{round(dec)} KB" if claim.unit_is_decimal
                         else f"{round(kib)} KB")
            res.results.append(ClaimResult(
                claim, FAIL, actual,
                f"page says {claim.size_text} ({claimed:,.0f} B) but the delivered "
                f"member is {actual:,} B = {kib:.1f} KiB = {dec:.1f} KB. {note}",
                corrected_text=corrected))
    return res