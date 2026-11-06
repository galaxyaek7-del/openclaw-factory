# -*- coding: utf-8 -*-
"""Digital-product discovery for the Golden Hunter (2026-11-06, founder: move the hunter from books to the other digital products).

The hunter's pool came from 10 fixed seeds (one of them a printable book), Sensing Engine trends and Pioneer's raw Hacker News /
GitHub / Stack Overflow headlines. Raw headlines are questions, not products ("Can I stop Google showing my site as docs?"), so the
JS selector drops them. This module does the missing step: it TRANSLATES a real signal into a concrete digital product proposal, or
honestly declines when there is no recurring decision behind it.

    python golden_hunter/digital_discovery.py          # one run: process up to GF_DISCOVERY_MAX new signals, write the candidates file
    (loop step: scripts/digital_discovery_daily.py, at most once a day)

Product types it may propose (what the factory can package or build): excel_workbook, google_sheets_template, document_template_pack,
checklist_kit, dataset_brief. Price is a whole number from 9 to 49 USD. Every proposal is checked against the LIVE catalog (a proposal that
overlaps a title already on sale is marked duplicate) and nothing here builds, prices on a store or publishes anything: the output is
data/digital_candidates.json, read by the hunter, which then runs its own gates and the agent chain (founder-review package).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CANDIDATES = ROOT / "data" / "digital_candidates.json"
STATE = ROOT / "data" / "digital_discovery_state.json"
CATALOG = ROOT / "customer_site" / "catalog.json"
TYPES = ("excel_workbook", "google_sheets_template", "document_template_pack", "checklist_kit", "dataset_brief")
MAX_KEEP = 300
STOP = {"calculator", "tracker", "planner", "model", "template", "workbook", "excel", "small", "business", "tool", "with", "your", "for", "and", "the",
        "templates", "pack", "kit", "checklist", "sheet", "sheets", "google", "document", "dataset", "brief"}

SYSTEM = ("You are the discovery analyst of Galaxy Forge, which sells digital products to small-business owners, freelancers and households at "
          "$9 to $49. You turn a real signal (a question people asked, a trend, a market-evidence note) into ONE concrete digital product, "
          "or you decline. Company mission: earn real, verified revenue; never invent demand, numbers or sources. A product must answer a "
          "recurring money or operations decision for a named buyer; a signal with no such decision behind it gets a decline.")


def prompt(signal):
    return f"""Signal: {signal}

Propose ONE digital product that helps a named buyer with the recurring decision behind this signal.
Allowed types: {', '.join(TYPES)}.
Rules:
- Work from the problem behind the signal, not its topic. News, entertainment, opinion or purely technical trivia has no decision behind it: decline.
- To decline answer exactly:
##TITLE##
NONE
##TYPE##
none
##TOPIC##
no recurring decision behind this signal
##AUDIENCE##
none
##PRICE##
0
- Otherwise: an English title that says what the buyer gets or computes, the type, one sentence on the decision, the buyer, and a whole-number USD price from 9 to 49 justified by the cost of a wrong decision.

Use exactly this format and nothing else:
##TITLE##
<title>
##TYPE##
<one allowed type>
##TOPIC##
<one sentence>
##AUDIENCE##
<the buyer>
##PRICE##
<integer 9-49>"""


def _section(text, tag):
    m = re.search(rf"##{tag}##\s*([\s\S]*?)(?=##[A-Z]+##|$)", str(text or ""), re.I)
    return m.group(1).strip() if m else ""


def parse(text):
    """-> {'declined': True, 'reason': str} | {'title','type','topic','audience','price'} | None (contract not met)."""
    title = _section(text, "TITLE")
    if not title:
        return None
    if re.match(r"none\b", title, re.I):
        return {"declined": True, "reason": _section(text, "TOPIC")[:160]}
    typ = _section(text, "TYPE").lower().strip()
    typ = next((t for t in TYPES if t in typ), None)
    try:
        price = int(re.sub(r"[^0-9]", "", _section(text, "PRICE")) or "0")
    except ValueError:
        price = 0
    topic, audience = _section(text, "TOPIC"), _section(text, "AUDIENCE")
    if len(title) < 5 or len(title) > 140 or not typ or not topic or not audience or not (9 <= price <= 49):
        return None
    return {"title": title, "type": typ, "topic": topic[:300], "audience": audience[:160], "price": price}


MONEY_RE = re.compile(r"(cost|price|pricing|budget|cash|profit|margin|tax|invoice|payment|revenue|saving|loan|debt|rent|payroll|hours|rate|fee|compliance|penalt|forecast|break-?even|roi|expense|income|allocation|annuity|retirement|invest|currency|transfer|escrow|billing|quote|estimate|commission|refund|subscription|inventory|pipeline|utili[sz]ation)", re.I)
NOT_A_PRODUCT_RE = re.compile(r"(interview|career|promotion|accusation|colleague|manager|leadership|dunning|pseudonym|relationship|dating|motivation|mindset|confidence|burnout)", re.I)


def quality(cand):
    """Deterministic buyer-relevance check on the PROPOSAL (not the model's opinion): strong = a money or operations decision is in the
    title or topic and it is not personal-workplace advice; weak candidates are kept but never reach the hunter. The first live run proposed
    a product for 18 of 19 signals (FAANG prep, a colleague conflict), so eagerness alone proves nothing about demand."""
    text = f"{cand.get('niche', '')} {cand.get('topic', '')}"
    if NOT_A_PRODUCT_RE.search(text):
        return "weak"
    return "strong" if MONEY_RE.search(text) else "weak"


def _tokens(text):
    return {w for w in re.findall(r"[a-z]{4,}", str(text).lower()) if w not in STOP}


def live_titles(path=CATALOG):
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        return [p["title"] for p in (d.get("data") or d).get("products", []) if p.get("title")]
    except (OSError, ValueError, KeyError):
        return []


def duplicate_of(title, titles, threshold=0.5):
    a = _tokens(title)
    if len(a) < 2:
        return None
    best = None
    for t in titles:
        b = _tokens(t)
        shared = len(a & b)
        score = shared / len(a)
        if shared >= 2 and score >= threshold and (best is None or score > best[1]):
            best = (t, round(score, 2))
    return best


def sid(signal):
    return hashlib.sha1(str(signal).strip().lower().encode("utf-8")).hexdigest()[:12]


def looks_like_headline(n):
    n = str(n or "").strip()
    return "?" in n or "؟" in n or len(n) > 80 or bool(re.match(r"(how|why|what|when|should|can i|do you|am i|is it|apply|breaking|building|alternatives to)\b", n, re.I))


def collect_signals(root=ROOT, limit_per_source=60):
    """Real signals only, tagged with their source: raw Pioneer/Sensing headlines in the hunter's pool, recent OPPORTUNITIES.md trends,
    and the buyer-side market evidence notes. Nothing is invented here."""
    out = []
    try:
        pool = json.loads((Path(root) / "golden_opportunities.json").read_text(encoding="utf-8")).get("results", [])
        seen = set()
        for r in pool:
            n = r.get("niche")
            if n and n not in seen and looks_like_headline(n):
                seen.add(n)
                out.append(("hunter_headline", n))
    except (OSError, ValueError):
        pass
    try:
        txt = (Path(root) / "OPPORTUNITIES.md").read_text(encoding="utf-8", errors="ignore")
        titles = []
        for m in re.finditer(r"^- \[\d{4}-\d{2}-\d{2}T[^\]]*\] (.+?) — ", txt, re.M):
            titles.append(m.group(1).strip())
        for t in list(dict.fromkeys(reversed(titles)))[:limit_per_source]:
            out.append(("sensing_trend", t))
    except OSError:
        pass
    try:
        for line in (Path(root) / "data" / "market_evidence.jsonl").read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("{"):
                d = json.loads(line)
                if d.get("niche"):
                    out.append(("market_evidence", f"{d['niche']} ({str(d.get('event_type', '')).replace('_', ' ')})"))
    except (OSError, ValueError):
        pass
    seen_ids, uniq = set(), []
    for src, sig in out:
        i = sid(sig)
        if i not in seen_ids:
            seen_ids.add(i)
            uniq.append((src, sig))
    return uniq


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def run(max_signals=None, generate=None, signals=None, titles=None, now=None, candidates_path=CANDIDATES, state_path=STATE):
    """Process up to max_signals NEW signals. -> summary dict. `generate(system, user) -> text` is injectable (tests)."""
    now = now or datetime.now(timezone.utc)
    max_signals = int(os.environ.get("GF_DISCOVERY_MAX", "20")) if max_signals is None else max_signals
    state = load_json(state_path, {"processed": {}})
    done = state.setdefault("processed", {})
    cands = load_json(candidates_path, [])
    titles = live_titles() if titles is None else titles
    todo = [(s, g) for s, g in (signals if signals is not None else collect_signals()) if sid(g) not in done][:max_signals]
    if generate is None:
        from ai_capability import orchestrator

        def generate(system, user):
            return orchestrator.generate("analysis", system, user, max_tokens=2500, timeout=90, retries=2)["content"]
    counts = {"processed": 0, "proposed": 0, "declined": 0, "duplicate": 0, "contract_failed": 0, "errors": 0}
    for src, sig in todo:
        try:
            parsed = parse(generate(SYSTEM, prompt(sig)))
        except Exception:  # noqa: BLE001 a model/network failure is retried on a later run, never recorded as an outcome
            counts["errors"] += 1
            continue
        counts["processed"] += 1
        if parsed is None:
            done[sid(sig)] = {"outcome": "contract_failed", "at": now.isoformat(timespec="seconds")}
            counts["contract_failed"] += 1
        elif parsed.get("declined"):
            done[sid(sig)] = {"outcome": "declined", "at": now.isoformat(timespec="seconds")}
            counts["declined"] += 1
        else:
            dup = duplicate_of(parsed["title"], titles)
            done[sid(sig)] = {"outcome": "duplicate" if dup else "proposed", "at": now.isoformat(timespec="seconds")}
            if dup:
                counts["duplicate"] += 1
                continue
            counts["proposed"] += 1
            cands.append({"niche": parsed["title"], "product_type": parsed["type"], "topic": parsed["topic"], "audience": parsed["audience"],
                          "price": parsed["price"], "source": src, "signal": sig[:200], "created_at": now.isoformat(timespec="seconds"), "status": "candidate"})
            cands[-1]["quality"] = quality(cands[-1])
            titles.append(parsed["title"])  # two signals can not propose the same product in one run
    for c in cands:  # candidates stored before the quality field existed
        c.setdefault("quality", quality(c))
    cands = cands[-MAX_KEEP:]
    for path, doc in ((candidates_path, cands), (state_path, state)):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(str(path) + ".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, path)
    counts["signals_waiting"] = max(0, len([1 for s, g in (signals if signals is not None else collect_signals()) if sid(g) not in done]))
    counts["candidates_total"] = len(cands)
    counts["strong"] = sum(1 for c in cands if c.get("quality") == "strong")
    return counts


def main():
    r = run()
    sys.stdout.write(json.dumps(r, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
