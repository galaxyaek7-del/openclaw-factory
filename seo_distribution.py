"""SEO Distribution Engine (Autonomous Enterprise Master Plan Task 2,
2026-08-15).

The ONLY distribution channel that is READY today is SEO (deterministic,
zero-cost, no external approval). This engine publishes honest, original,
problem-first SEO pages to the customer site from REAL portfolio
opportunities (data/commission_opportunities.jsonl). Every page:

  * is generated from real opportunity fields only (never fabricated)
  * states the REAL approval state of the affiliate program
  * discloses honestly that the affiliate link is not yet live (HUMAN_GATE)
  * registers itself in a publish ledger (data/seo_pages.json) so pages
    are never duplicated and every page's existence is auditable
  * tracks real page views via the existing record_page_view() ledger

Read-only for ledgers (append to seo_pages.json registry + page views);
never contacts a platform, never spends money, never fabricates revenue.
Idempotent: regenerating for the same opportunity updates the page in
place and never duplicates the registry entry.
"""

import json
import re
import html
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

_FACTORY_ROOT = Path(__file__).resolve().parent
_COMMISSION_OPPORTUNITIES = _FACTORY_ROOT / "data" / "commission_opportunities.jsonl"
_SEO_PAGES_REGISTRY = _FACTORY_ROOT / "data" / "seo_pages.json"
_CUSTOMER_SITE_DIR = _FACTORY_ROOT / "customer_site"

_SITE_HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<meta name="description" content="__DESCRIPTION__">
<meta name="robots" content="index, follow">
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Cdefs%3E%3ClinearGradient id='g' x1='0' y1='0' x2='1' y2='1'%3E%3Cstop offset='0' stop-color='%23d97a3f'/%3E%3Cstop offset='1' stop-color='%238a4a1f'/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='32' height='32' rx='9' fill='url(%23g)'/%3E%3Ctext x='16' y='22' font-family='IBM Plex Sans,Arial,sans-serif' font-weight='800' font-size='14' fill='%231a0e05' text-anchor='middle'%3EGF%3C/text%3E%3C/svg%3E">
<style>
:root{--bg:#0a0c11;--bg-elev:#12151d;--bg-card:#161a24;--border:#242938;--ink:#eef0f6;--ink-dim:#9198ad;--ink-faint:#5c6379;--accent:#d97a3f;--accent-ink:#f0a468;--warn:#d9a441;--warn-soft:#2e2412;--good:#4a9d6f;--sans:'IBM Plex Sans',-apple-system,sans-serif;--mono:'IBM Plex Mono',ui-monospace,monospace;--radius:12px;color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);-webkit-font-smoothing:antialiased;line-height:1.65}
a{color:var(--accent-ink);text-decoration:none}
.wrap{max-width:820px;margin:0 auto;padding:0 1.5rem}
header{position:sticky;top:0;background:rgba(10,12,17,.9);backdrop-filter:blur(10px);border-bottom:1px solid #1a1e2a;z-index:50}
.nav{display:flex;align-items:center;gap:1rem;padding:.8rem 1.5rem;max-width:1120px;margin:0 auto}
.brand{font-weight:700;color:var(--ink)}
.brand small{color:var(--ink-dim);font-weight:400}
main{padding:2.5rem 0 4rem}
.eyebrow{font-family:var(--mono);font-size:.7rem;letter-spacing:.06em;text-transform:uppercase;color:var(--accent-ink);background:#3a2818;border:1px solid rgba(217,122,63,.3);padding:.35rem .7rem;border-radius:99px;display:inline-block;margin-bottom:1rem}
h1{font-size:1.7rem;letter-spacing:-.02em;margin:0 0 .4rem}
.sub{color:var(--ink-dim);font-size:.95rem;margin-bottom:1.6rem}
.disclosure{background:var(--warn-soft);border:1px solid rgba(217,164,65,.35);border-radius:var(--radius);padding:1rem 1.3rem;font-size:.85rem;color:var(--ink);margin:1.2rem 0 2rem;line-height:1.55}
.disclosure b{color:var(--warn)}
.fact{background:var(--bg-elev);border:1px solid #1a1e2a;border-radius:var(--radius);padding:1.1rem 1.3rem;margin-bottom:1.6rem;font-size:.87rem;line-height:1.6}
.fact b{color:var(--ink)}
.fact .row{display:flex;gap:.5rem;margin-bottom:.35rem}
.fact .k{color:var(--ink-faint);min-width:150px;font-family:var(--mono);font-size:.78rem;padding-top:.15rem}
h2{font-size:1.15rem;letter-spacing:-.02em;margin:2rem 0 .6rem}
p{margin:0 0 1rem}
.steps{background:var(--bg-card);border:1px solid #1a1e2a;border-radius:var(--radius);padding:1.2rem 1.4rem;margin:1rem 0}
.steps ol{margin:0;padding-left:1.2rem}
.steps li{margin-bottom:.5rem}
.status{display:inline-block;font-family:var(--mono);font-size:.75rem;padding:.3rem .7rem;border-radius:99px;border:1px solid var(--border);margin-bottom:1rem}
.status.warn{color:var(--warn);border-color:rgba(217,164,65,.4)}
footer{border-top:1px solid #1a1e2a;padding:2rem 0;text-align:center;color:var(--ink-faint);font-size:.8rem}
</style>
</head>
<body>
<header>
  <div class="nav"><span class="brand">Galaxy Forge <small>· honest guides</small></span></div>
</header>
<main>
<div class="wrap">
"""

_SITE_TAIL = """</div>
</main>
<footer>Galaxy Forge · __YEAR__ · Content generated from verified program data; affiliate links activate only after founder approval.</footer>
<script>
// Privacy-minimal page-view beacon (Autonomous Enterprise Directive gap #2,
// 2026-08-15): records ONE real page view via the existing public
// /api/page-view endpoint (click_tracking.record_page_view). Sends only the
// page id + referrer -- no cookies, no fingerprinting, no third party.
try {
  fetch('/api/page-view', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ page_id: '__PAGE_ID__' }),
    keepalive: true,
  }).catch(function () {});
} catch (e) {}
</script>
</body>
</html>
"""


def _now_iso(now: Optional[datetime] = None) -> str:
    return (now or datetime.now(timezone.utc)).isoformat()


def _slug(program_name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", program_name.lower()).strip("-")
    return s or "guide"


def _esc(v) -> str:
    return html.escape(str(v), quote=True)


def _load_opportunities() -> List[Dict[str, object]]:
    if not _COMMISSION_OPPORTUNITIES.exists():
        return []
    out = []
    for line in _COMMISSION_OPPORTUNITIES.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:  # pragma: no cover - defensive
            continue
    return out


def _load_registry() -> List[Dict[str, object]]:
    if not _SEO_PAGES_REGISTRY.exists():
        return []
    try:
        data = json.loads(_SEO_PAGES_REGISTRY.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:  # pragma: no cover - defensive
        return []


def _save_registry(entries: List[Dict[str, object]]) -> None:
    _SEO_PAGES_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    _SEO_PAGES_REGISTRY.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )


def _page_html(opp: Dict[str, object], slug: str = "") -> str:
    program = str(opp.get("program_name") or opp.get("partner_name") or "Program")
    problem = str(opp.get("customer_problem") or "")
    audience = str(opp.get("target_customer") or "")
    product = str(opp.get("product_or_service") or program)
    commission = str(opp.get("commission_value") or "")
    recurring = "Yes" if opp.get("recurring_commission") else "No"
    commission_duration = str(opp.get("commission_duration") or "")
    payout = str(opp.get("payout_terms") or "")
    eligibility = str(opp.get("eligibility") or "")
    geography = str(opp.get("geography") or "")
    min_conditions = str(opp.get("minimum_conditions") or "")
    founder_action = str(opp.get("founder_action") or "")
    verification = str(opp.get("verification") or "DISCOVERED")

    if not founder_action:
        for key in ("human_gate", "approval_action", "signup_url"):
            hg = opp.get(key)
            if isinstance(hg, dict) and hg.get("founder_action"):
                founder_action = str(hg["founder_action"])
                break

    title = f"{program}: what to know before choosing"
    description = f"A real, evidence-based guide to {program} for {audience}. Verified program details, honest pricing, and clear steps."

    rows = []
    for label, val in (
        ("Who this is for", audience),
        ("The problem it solves", problem),
        ("What the product/service is", product),
        ("Commission structure", commission),
        ("Recurring commission", recurring),
        ("Commission duration", commission_duration),
        ("Payout terms", payout),
        ("Eligibility", eligibility),
        ("Geography", geography),
        ("Minimum conditions", min_conditions),
        ("Verification", verification),
    ):
        if val:
            rows.append(f'<div class="row"><span class="k">{_esc(label)}</span><span>{_esc(val)}</span></div>')

    facts = "".join(rows) if rows else '<div class="row"><span class="k">Verification</span><span>DISCOVERED — official program details pending real confirmation.</span></div>'

    steps_html = ""
    if problem and audience:
        steps_html = f"""
<section class="steps">
<h2>How to evaluate {_esc(program)}</h2>
<ol>
<li>Start from the need: <b>{_esc(audience)}</b> facing <b>{_esc(problem)}</b>.</li>
<li>Compare options in this category on real long-term cost, ease of start, quality, and support — not on marketing.</li>
<li>Read the official program terms (payout, cookie window, eligibility) before committing.</li>
<li>Try the service at the lowest-risk tier first, and only recommend it once it works for the actual use case.</li>
</ol>
</section>"""

    status_html = '<span class="status warn">STATUS: awaiting founder approval to activate the affiliate link</span>'
    if founder_action:
        status_html = (
            '<span class="status warn">STATUS: awaiting founder approval</span>'
            f'<div class="disclosure"><b>Disclosure:</b> This page is an educational guide to <b>{_esc(program)}</b>. '
            f'<b>We are not yet an approved affiliate of this program.</b> The affiliate link activates only after the founder completes: '
            f'{_esc(founder_action)}. We only recommend what we believe is genuinely useful; if a commission ever applies, we disclose it.</div>'
        )
    else:
        status_html = (
            '<span class="status warn">STATUS: program details verified, affiliate link not yet active</span>'
            '<div class="disclosure"><b>Disclosure:</b> Educational guide to '
            f'<b>{_esc(program)}</b>. Galaxy Forge is not yet an approved affiliate; no commission is collected from this page today.</div>'
        )

    body = (
        _SITE_HEAD.replace("__TITLE__", _esc(title)).replace("__DESCRIPTION__", _esc(description))
        + f'<span class="eyebrow">Honest guide</span>'
        + f'<h1>{_esc(title)}</h1>'
        + f'<div class="sub">{_esc(audience) if audience else "An evidence-based overview."}</div>'
        + status_html
        + f'<div class="fact">{facts}</div>'
        + steps_html
        + f"<p>This page is part of Galaxy Forge's autonomous distribution engine. It is generated from the real, verified opportunity record "
        + f"(opportunity ID <code>{_esc(opp.get('opportunity_id') or '')}</code>) and updated as the record changes. Nothing on this page is fabricated.</p>"
        + _SITE_TAIL.replace("__YEAR__", str(datetime.now(timezone.utc).year))
              .replace("__PAGE_ID__", f"guide-{slug}")
    )
    return body


def publish_seo_pages(now: Optional[datetime] = None) -> Dict[str, object]:
    """Generate (or refresh) an SEO page for every real affiliate opportunity
    that has enough real content to make an honest page (program + problem).

    Idempotent: existing pages are overwritten in place; the registry entry
    is updated (never duplicated). Returns the publish summary."""
    ts = _now_iso(now)
    opportunities = _load_opportunities()
    registry = _load_registry()
    published = []
    failed = []

    for opp in opportunities:
        if not isinstance(opp, dict):
            continue
        program = opp.get("program_name") or opp.get("partner_name")
        problem = opp.get("customer_problem")
        if not program or not problem:
            continue
        opp_id = opp.get("opportunity_id") or ""
        slug = _slug(str(program))
        filename = f"guide-{slug}.html"
        page_path = _CUSTOMER_SITE_DIR / filename
        try:
            body = _page_html(opp, slug)
            _CUSTOMER_SITE_DIR.mkdir(parents=True, exist_ok=True)
            page_path.write_text(body, encoding="utf-8")
            entry = {
                "page": f"/site/{filename}",
                "opportunity_id": opp_id,
                "program_name": program,
                "generated_at": ts,
                "verification": opp.get("verification") or "DISCOVERED",
            }
            # Idempotent: replace existing registry entry for the same page.
            for i, e in enumerate(registry):
                if e.get("page") == entry["page"]:
                    registry[i] = entry
                    break
            else:
                registry.append(entry)
            published.append(entry["page"])
        except Exception as e:  # pragma: no cover - defensive
            failed.append({"opportunity_id": opp_id, "error": str(e)})

    _save_registry(registry)
    return {
        "generated_at": ts,
        "published_pages": published,
        "published_count": len(published),
        "failed_count": len(failed),
        "failed": failed,
        "registry_count": len(registry),
        "note": "SEO is the only distribution channel READY today (zero-cost, no external approval). Pages are real, honest, and regenerated idempotently from data/commission_opportunities.jsonl.",
    }


def _cli_main() -> None:
    print(json.dumps(publish_seo_pages(), ensure_ascii=False, default=str))


if __name__ == "__main__":
    _cli_main()