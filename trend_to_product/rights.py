"""Trend-to-Product: originality and intellectual-property checks (2026-10-29).

Decides, for one product idea or specification, whether its assets and text can
go forward:

  PASS    every asset is the factory's own work (with process evidence) or is
          used under a recorded licence that grants commercial use;
  REVIEW  ownership or derivative risk is uncertain -> a person must look;
  BLOCK   the idea depends on material we have no right to use.

Rules that are deliberately not configurable:
  * attribution alone is never commercial permission;
  * nothing taken from Pinterest is ever a product asset;
  * a licence counts only when it states commercial use and has a reference.

The text scan reuses executive_quality_gate.check_copyright_trademark_risk (the
factory's existing brand-affiliation scan) and adds derivative-work phrases. It
is a screen, not legal review.
"""
from urllib.parse import urlparse

PROVENANCE = ("ORIGINAL_FACTORY", "LICENSED", "PUBLIC_DOMAIN", "THIRD_PARTY", "UNKNOWN")

DERIVATIVE_RISK_PHRASES = (
    "copy of", "copied from", "recreate this pin", "recreated from", "same as the pin",
    "dupe of", "replica of", "traced from", "based on the pattern by", "pattern by @",
    "from pinterest", "pinterest image", "screenshot of", "reworded from", "rewritten from",
    "knockoff", "knock-off", "inspired by @",
)


def _host(url):
    return (urlparse(url or "").hostname or "").lower()


def _asset_finding(a):
    name = a.get("name") or "unnamed asset"
    prov = a.get("provenance")
    lic = a.get("licence") or {}
    src = a.get("source_url")
    if prov not in PROVENANCE:
        return "REVIEW", f"{name}: provenance not recorded"
    if src and "pinterest" in _host(src).split("."):
        return "BLOCK", f"{name}: taken from Pinterest; pins are signals, never assets"
    if prov == "ORIGINAL_FACTORY":
        if not a.get("process_evidence"):
            return "REVIEW", (f"{name}: claimed original but no process evidence "
                              "(source file, generator log or build script) is recorded")
        return "PASS", f"{name}: original, evidence {a['process_evidence']}"
    if prov == "PUBLIC_DOMAIN":
        if not a.get("public_domain_basis"):
            return "REVIEW", f"{name}: public-domain status stated without a basis"
        return "PASS", f"{name}: public domain ({a['public_domain_basis']})"
    if prov == "LICENSED":
        if lic.get("attribution_only") and not lic.get("commercial_use"):
            return "BLOCK", f"{name}: attribution-only licence is not commercial permission"
        if lic.get("commercial_use") is not True or not lic.get("reference"):
            return "BLOCK", f"{name}: licence does not record commercial use with a reference"
        if lic.get("resale_of_asset_prohibited") and a.get("resold_as_is"):
            return "BLOCK", f"{name}: licence forbids reselling the asset itself"
        return "PASS", f"{name}: licensed ({lic['reference']})"
    if prov == "THIRD_PARTY":
        return "BLOCK", f"{name}: third-party material with no licence to use it"
    return "REVIEW", f"{name}: ownership unknown"


def check_rights(assets=None, text=None):
    """Return {status, findings, checked, note}. Empty input is REVIEW, never PASS."""
    findings = []
    statuses = []
    for a in assets or []:
        st, why = _asset_finding(a)
        statuses.append(st)
        findings.append({"status": st, "finding": why})
    if text:
        low = text.lower()
        hits = [p for p in DERIVATIVE_RISK_PHRASES if p in low]
        if hits:
            statuses.append("REVIEW")
            findings.append({"status": "REVIEW", "finding": "derivative-work wording: " + ", ".join(hits)})
        try:
            import executive_quality_gate as eqg
            res = eqg.check_copyright_trademark_risk([{"content": text}])
            if res.get("status") == "FAIL" or res.get("result") == "FAIL":
                statuses.append("BLOCK")
                findings.append({"status": "BLOCK", "finding": "claimed brand affiliation/licence: "
                                 + ", ".join(res.get("evidence") or res.get("hits") or [])})
        except Exception as e:  # the screen is additive; its absence is reported
            findings.append({"status": "REVIEW", "finding": f"brand scan unavailable ({type(e).__name__})"})
            statuses.append("REVIEW")
    if text and not any(f["status"] != "PASS" for f in findings[len(assets or []):]):
        findings.append({"status": "PASS", "finding": "idea/spec text screen found no derivative or "
                                                      "brand-affiliation wording"})
    if not assets:
        # An idea with no produced assets cannot be cleared yet; at most REVIEW.
        status = "BLOCK" if "BLOCK" in statuses else "REVIEW"
        return {"status": status, "findings": findings, "checked": 0,
                "note": "no product assets recorded yet; rights are cleared only on real assets"}
    status = "BLOCK" if "BLOCK" in statuses else ("REVIEW" if "REVIEW" in statuses else "PASS")
    return {"status": status, "findings": findings, "checked": len(assets or []),
            "note": "screen only; not a substitute for legal review"}
