"""Galaxy Forge â€” product claim-integrity gate (Cycle 81, 2026-10-14).

WHY THIS EXISTS â€” a real, verified, live defect, not a hypothetical.

A read-only audit of the real Gumroad account on 2026-10-14 (79 live products,
enumerated via cursor pagination; see scripts/gumroad_catalog_truth.py) turned
up this listing:

    "Verified B2B Lead Lists (200-lead batch)"  --  $99
    https://aekraft.gumroad.com/l/drtaj
    its own copy promises: "Delivery as CSV and Google Sheets within 6 days",
                           "200 leads", "verified business emails"
    its actual attachment: a 1-page, 81-word PDF that only *describes* that
                           service. No CSV, no rows, no leads.

A buyer paying $99 receives a page of prose. Zero sales have occurred on any
listing, so nobody has been harmed yet -- but the listing is live and
purchasable. That is the exact class of defect the Trust & Excellence
Constitution (ADR-189: "no unfinished products", "promises match reality") and
brand_dna.py's "no misleading pricing" exist to prevent, and this factory had
no mechanical check for it.

WHAT THIS MODULE DOES

`check_claim_integrity()` takes only what is already known about a listing and
its payload -- no network, no filesystem writes, no clock, no randomness -- and
returns a verdict. distributor.py calls it as a pre-publish gate for real
(non-dry-run) publishes, so the defect cannot recur through this factory's own
publishing path.

A FIRST DRAFT OF THIS GATE WAS WRONG, AND THE REPO'S OWN REAL DATA CAUGHT IT

The first version matched a wide "data" vocabulary that included "templates",
"workbook", "tracker" and "calculator", and it flagged 9 live listings. Reading
those 9 listings' actual copy showed that 8 of the 9 were FALSE POSITIVES: they
all say "A single, focused file you download and use immediately", they do
deliver that file, and their body copy never promises a spreadsheet -- only
their *titles* contain a word like "Workbook". The $155 flagship was flagged
too, for the word "templates" in the phrase "Practical templates and
implementation guide", which is a completely legitimate PDF product.

The lesson is encoded below rather than apologised for in a comment: only
claims that CANNOT be satisfied by prose block. "CSV", "Google Sheets" and
"database" are not document formats; "workbook" and "templates" are. A gate
built on vocabulary guessing produces false positives, and a gate that produces
false positives on your own best product gets switched off.

WHAT IT DELIBERATELY DOES NOT DO

  * It never blocks on an UNKNOWN payload. Only positive evidence that a claim
    is contradicted by the payload blocks. A gate that fires on absent evidence
    is a gate that gets disabled by its first false positive.
  * It never blocks on an archive it cannot open.
  * It never fabricates. Every finding carries the matched text and the payload
    evidence that produced it.
  * It never writes to any platform. Blocking a new publish is not the same as
    withdrawing an already-published listing, which is why the audit output is
    evidence for a human decision, not automatic remediation.

ESCAPE HATCH

`allow_claim_risk=True` on distributor.distribute() mirrors the existing
`allow_protected` founder-approval pattern -- explicit and visible, never a
default.
"""

from __future__ import annotations

import re

# PASS / BLOCK / REVIEW / UNKNOWN, deliberately four values and not one
# boolean. "We could not check" is a genuinely different state from "we
# checked and it is fine", and collapsing the two is how a safety gate quietly
# stops meaning anything.
PASS = "PASS"
BLOCK = "BLOCK"
REVIEW = "REVIEW"
UNKNOWN = "UNKNOWN"

# â”€â”€ Claims that CANNOT be satisfied by a prose document â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Each of these names a machine-readable artefact or a dataset. A PDF cannot be
# a CSV, a Google Sheet, or a 200-row database, so promising one and shipping
# only documents is a contradiction, not a thin product.
#
# Words deliberately ABSENT, because reading real listings proved they are not
# reliable signals: "template(s)", "workbook", "tracker", "calculator",
# "checklist", "guide", "kit", "pack", "playbook". A PDF workbook is a real,
# legitimate product ("The Freelance Writer's Workbook"). "Templates" appears
# in the $155 flagship's own subtitle and flagging it was a false positive.
DATA_CLAIM_PATTERNS = (
    r"\bcsv\b",
    r"\btsv\b",
    r"\bspreadsheets?\b",
    r"\bxlsx?\b",
    r"\bgoogle sheets\b",
    r"\bdatabases?\b",
    r"\bdatasets?\b",
    r"\blead lists?\b",
    r"\bmailing lists?\b",
    r"\bcontact lists?\b",
    r"\bdirectories\b",
    r"\bmail merges?\b",
    r"\bimports? (?:directly )?into\b",
)
_DATA_CLAIM_RE = re.compile("|".join(DATA_CLAIM_PATTERNS), re.IGNORECASE)

# "you get" / "what you get" / "inside:" -- copy that enumerates the contents
# of the purchase. Used to tell a product that IS its deliverable apart from a
# document that only talks ABOUT the deliverable.
DELIVERABLE_PHRASES = (
    "what you get", "you get:", "you will get", "you receive",
    "inside:", "what's inside", "what is inside", "deliverable",
    "delivery as", "delivered as", "you will receive", "you download",
    "comes with", "includes:", "file you",
)

# How far (in characters) a data term may sit from a delivery phrase and still
# count as a promise about what the BUYER RECEIVES.
#
# This exists because a second real false positive proved the pure-vocabulary
# version wrong. The live "ADA Demand-Letter Response & Triage Kit"
# (aekraft.gumroad.com/l/palmdr) contains the word "datasets" -- but it cites
# them as research sources ("Built from Seyfarth Shaw counts, UsableNet/EcomBack
# datasets"), which is a statement about the AUTHOR's sources, not a promise to
# ship data. A rule that cannot tell "we drew on this dataset" from "you will
# receive this dataset" will eventually block a good product, and a gate that
# blocks good products gets switched off.
CLAIM_PROXIMITY_CHARS = 400

DATA_EXTENSIONS = (
    ".csv", ".tsv", ".xlsx", ".xls", ".ods", ".numbers", ".json",
    ".sqlite", ".db", ".parquet",
)
DOCUMENT_EXTENSIONS = (".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".epub")
ARCHIVE_EXTENSIONS = (".zip", ".tar", ".gz", ".7z", ".rar")

# A single document under this word count, sold with copy that enumerates what
# the buyer receives, is describing the product rather than being it.
# 400 words is measured, not guessed: the worst real finding measured 81 words
# on 1 page; the thinnest honest listing measured 331.
DESCRIPTION_ONLY_WORD_CEILING = 400

# Thin-for-price advisory. Disclosed constants, not a quality judgement: the
# distribution below is what the real catalog actually looks like (32 of 79
# products ship under 20KB), and an advisory that fires on almost everything
# is noise, so this deliberately targets only the clearest mismatch.
THIN_BYTES = 20_000
THIN_PRICE_FLOOR = 75.0


def _extension(name: str) -> str:
    name = (name or "").lower()
    dot = name.rfind(".")
    return name[dot:] if dot > -1 else ""


def _data_claim(title, description):
    """Return (matched_term, where) for a promise of a data artefact.

    A term in the TITLE is taken at face value -- "Lead Lists (200-lead batch)"
    is a promise whatever the body copy says.

    In the DESCRIPTION it only counts when it sits near a delivery phrase. That
    is the distinction the live ADA kit forced: its description says "Built from
    Seyfarth Shaw counts, UsableNet/EcomBack datasets", which is a citation of
    the author's sources, not an offer to ship one.

    Word-boundary matching throughout. An earlier substring version matched
    "leads" inside "misleads" and blocked an innocent listing.
    """
    m = _DATA_CLAIM_RE.search(title or "")
    if m:
        return m.group(0).lower(), "title"
    low = (description or "").lower()
    m = _DATA_CLAIM_RE.search(low)
    if not m:
        return None, None
    anchors = [low.rfind(p) for p in DELIVERABLE_PHRASES if p in low]
    if not anchors:
        return None, None
    start, end = m.span()
    for a in anchors:
        # The delivery phrase must be near the term in either direction.
        if a <= start <= a + CLAIM_PROXIMITY_CHARS:
            return m.group(0).lower(), "description"
        if start <= a <= end + CLAIM_PROXIMITY_CHARS:
            return m.group(0).lower(), "description"
    return None, None


def _enumerates_contents(text: str):
    low = (text or "").lower()
    for p in DELIVERABLE_PHRASES:
        if p in low:
            return p
    return None


def describe_payloads(payloads):
    """Normalise caller-supplied payload descriptors.

    Accepts Gumroad API dicts ({"name"/"file_name", "size", "filetype"}),
    (name, size) pairs, or plain names. An entry may carry "entries": [...] for
    an archive whose contents the caller managed to list.

    Returns a list of {"name", "bytes", "ext", "kind", "entries"}, where kind is
    "data" | "document" | "archive" | "other".

    Returns None when the caller supplied nothing, which means "not inspected"
    and is deliberately NOT the same as "ships nothing" -- only the caller that
    did the inspection can honestly claim the latter.
    """
    if payloads is None:
        return None
    out = []
    for p in payloads:
        entries = None
        if isinstance(p, dict):
            name = p.get("name") or p.get("file_name") or ""
            size = p.get("bytes")
            if size is None:
                size = p.get("size")
            ftype = (p.get("filetype") or "").lower()
            entries = p.get("entries")
        else:
            try:
                name, size = p
            except (TypeError, ValueError):
                name, size = str(p), None
            ftype = ""
        try:
            size = int(size)
        except (TypeError, ValueError):
            size = None
        ext = _extension(name)
        kind = "other"
        if ext in DATA_EXTENSIONS or ftype in ("csv", "xlsx", "xls", "json",
                                               "application/json"):
            kind = "data"
        elif ext in DOCUMENT_EXTENSIONS or ftype == "pdf":
            kind = "document"
        elif ext in ARCHIVE_EXTENSIONS or ftype in ("zip", "application/zip"):
            kind = "archive"
        out.append({"name": name, "bytes": size, "ext": ext, "kind": kind,
                    "entries": entries})
    return out


def check_claim_integrity(title, description, payloads, price_usd=None,
                          page_count=None, word_count=None):
    """Decide whether a listing's payload satisfies what the listing promises.

    title, description : str
        The listing text exactly as published.
    payloads : list | None
        Descriptors from describe_payloads(). None means the payload was never
        inspected -> UNKNOWN, never a pass on merit, never a block.
    price_usd : float | None
        0/None is a genuinely different case from a paid listing.
    page_count, word_count : int | None
        Real measured document depth, when the caller measured it.

    Returns dict(verdict, blocking_findings, advisory_findings, evidence, reason).
    """
    blocking, advisory, evidence = [], [], {}
    prepared = describe_payloads(payloads)

    # Rule 0 â€” the most important rule in the file, precisely because it is the
    # one that keeps this gate from becoming noise.
    if prepared is None:
        return {
            "verdict": UNKNOWN,
            "blocking_findings": [],
            "advisory_findings": [{
                "rule": "PAYLOAD_NOT_INSPECTED",
                "reason": "payload descriptors were not supplied, so the "
                          "listing's claims could be confirmed or refuted "
                          "neither way",
            }],
            "evidence": {},
            "reason": "payload not inspected",
        }

    data_files = [p for p in prepared if p["kind"] == "data"]
    documents = [p for p in prepared if p["kind"] == "document"]
    archives = [p for p in prepared if p["kind"] == "archive"]
    total_bytes = sum(p["bytes"] or 0 for p in prepared)

    evidence.update({
        "payload_count": len(prepared),
        "total_bytes": total_bytes,
        "data_files": [p["name"] for p in data_files],
        "document_files": [p["name"] for p in documents],
        "archive_files": [p["name"] for p in archives],
    })

    priced = bool(price_usd) and float(price_usd) > 0
    claim, claim_where = _data_claim(title, description)
    if claim:
        evidence["data_claim_term"] = claim
        evidence["data_claim_in"] = claim_where

    # Rule 1 â€” priced, but nothing ships at all.
    if priced and not prepared:
        blocking.append({
            "rule": "PRICED_BUT_NO_PAYLOAD",
            "reason": "the listing charges money but attaches no file, so a "
                      "completed purchase would deliver nothing",
        })

    # Rule 2 â€” promises a data artefact, ships no data file.
    unopened_archives = []
    opened_with_data = False
    if claim and not data_files:
        # An archive can legitimately contain the CSV we cannot see. Every
        # caller in this factory passes no `entries` for archives, so the
        # honest verdict is "cannot tell", not "false".
        unopened_archives = [a["name"] for a in archives if not a["entries"]]
        opened_with_data = any(
            any(_extension(e) in DATA_EXTENSIONS for e in (a["entries"] or []))
            for a in archives
        )
        if opened_with_data:
            pass
        elif unopened_archives:
            advisory.append({
                "rule": "DATA_CLAIM_IN_UNOPENED_ARCHIVE",
                "reason": "listing promises a data artefact (%r) but the "
                          "payload is an archive whose contents were not "
                          "listed; cannot confirm or refute" % claim,
            })
        elif prepared:
            blocking.append({
                "rule": "CLAIMED_DATA_NOT_DELIVERED",
                "reason": "listing promises a data artefact (matched %r) but "
                          "no csv/xlsx/tsv/json file is attached; a "
                          "document cannot satisfy that promise" % claim,
                "evidence": {
                    "matched_term": claim,
                    "attached": [p["name"] for p in prepared],
                    "kinds": [p["kind"] for p in prepared],
                },
            })

    # Rule 3 â€” the attachment describes the product instead of being it.
    #
    # This is deliberately NOT an independent trigger. It requires the same
    # data-artefact claim as Rule 2, because reading the real listings proved
    # that a short PDF is very often the product itself rather than a
    # description of something else: five live listings say "What you get: a
    # single, focused file you download and use immediately", they ship that
    # file, and they are thin rather than deceptive. Rule 3 therefore only
    # strengthens Rule 2 -- it names the exact way the promise was broken,
    # instead of accusing every thin listing.
    phrase = _enumerates_contents(description)
    if (claim and documents and not data_files and priced
            and not unopened_archives and phrase):
        shallow = False
        if word_count is not None:
            shallow = int(word_count) < DESCRIPTION_ONLY_WORD_CEILING
        elif page_count is not None:
            shallow = int(page_count) <= 1
        if shallow:
            evidence["word_count"] = word_count
            evidence["page_count"] = page_count
            blocking.append({
                "rule": "ATTACHMENT_DESCRIBES_RATHER_THAN_DELIVERS",
                "reason": "the copy enumerates what the buyer receives "
                          "(%r) and the only attachment is too short to be "
                          "that (pages=%s, words=%s)"
                          % (phrase, page_count, word_count),
                "evidence": {"matched_phrase": phrase,
                             "pages": page_count,
                             "words": word_count},
            })

    # Rule 4 â€” thin for the price. Advisory only: a small deliverable is a
    # pricing and product-design question, not a false statement, and this
    # factory must not confuse the two.
    if priced and total_bytes < THIN_BYTES and float(price_usd) >= THIN_PRICE_FLOOR:
        advisory.append({
            "rule": "THIN_FOR_PRICE",
            "reason": "priced at $%s but the whole payload is %s bytes; "
                      "verify the depth actually supports the price"
                      % (price_usd, total_bytes),
        })

    verdict = BLOCK if blocking else (REVIEW if advisory else PASS)
    return {
        "verdict": verdict,
        "blocking_findings": blocking,
        "advisory_findings": advisory,
        "evidence": evidence,
        "reason": "; ".join(f["rule"] for f in (blocking + advisory))
                  or "no claim contradicted by the payload",
    }