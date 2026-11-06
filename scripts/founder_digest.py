#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One Arabic digest per day for the founder, from measured factory data only (2026-11-06).

Why: with Telegram working, the founder should not have to ask "what is the state?". Every line below is read from a
live file or check (stage check, demand gate, product registry, tool snapshot, Pinterest ledger); nothing is estimated.
A number that cannot be read is written as UNKNOWN, never guessed (Truth First).

    python scripts/founder_digest.py --once        # loop step: sends at most once a day, from 07:00 UTC
    python scripts/founder_digest.py --preview     # prints the message, sends nothing, writes nothing

Delivery goes through gf_ops.alerts (Telegram, with the local fallback ledger and secret redaction). A failed send
(the host loses its network some mornings) is retried on the next ticks, at most MAX_ATTEMPTS times per day.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

STATE = ROOT / "data" / "founder_digest_state.json"
SEND_FROM_HOUR_UTC = 7
MAX_ATTEMPTS = 4


def _json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _jsonl(path):
    out = []
    try:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    except OSError:
        pass
    return out


def pinterest_summary(rows, today):
    """Pins recorded in the manual ledger: how many are due on or before today, how many later, the next one."""
    seen, pins = set(), []
    for r in rows:
        key = r.get("offer_id")
        d = str(r.get("scheduled_for", ""))[:10]
        if not key or key in seen or len(d) != 10:
            continue
        seen.add(key)
        pins.append((d, r.get("title", key)))
    due = [p for p in pins if p[0] <= today]
    later = sorted(p for p in pins if p[0] > today)
    return {"due": len(due), "later": len(later), "next": later[0] if later else None}


_NEEDS = {"A1": "يلزم حساب Amazon Associates (منك)", "K1": "يلزم OAuth ليوتيوب وإقرار مراجعة الحلقة (منك)",
          "6": "يلزم إنشاء لوحة Pinterest (منك)", "9": "يلزم ربط Telegram (منك)"}
_TOOL_AR = {"tools DEGRADED": "متدهورة", "tools FAILED": "فاشلة", "tools UNKNOWN": "غير معروفة"}


def _need(s):
    return _NEEDS.get(str(s.get("stage")), s.get("owner", ""))


def build_message(*, today, stages, tools_counts, regressions, registry, demand, pins, tool_names=None, connectors=None, automation=None):
    pub = sum(1 for p in registry.get("products", []) if p.get("published")) if registry else None
    sales = sum(int(p.get("sales_count") or 0) for p in registry.get("products", []) if p.get("published")) if registry else None
    reg_age = str((registry or {}).get("generated_at", ""))[:16] or "UNKNOWN"
    blocked = [s for s in stages if s["status"] == "BLOCKED"]
    waiting = [s for s in stages if s["status"] == "WAITING"]
    ok = sum(1 for s in stages if s["status"] == "OK")
    L = [f"ملخص المصنع اليومي | {today}", ""]
    L.append(f"المال: {pub if pub is not None else 'UNKNOWN'} منتجاً منشوراً، {sales if sales is not None else 'UNKNOWN'} مبيعة (سجل {reg_age} UTC).")
    if demand is not None:
        sig = demand.get("signals", {})
        L.append("الطلب: بوابة الطلب " + ("مفتوحة" if demand.get("open") else "مغلقة") + " | " +
                 "، ".join(f"{k}={v}" for k, v in sig.items()))
    L.append(f"المراحل: {ok} سليمة، {len(blocked)} محجوبة، {len(waiting)} تنتظر الواقع.")
    for s in blocked[:4]:
        L.append(f"  - {s['name']}: {_need(s)}")
    if regressions:
        L.append("تراجع منذ آخر لقطة: " + "، ".join(g["name"] for g in regressions[:5]))
    else:
        L.append("لا تراجع منذ آخر لقطة.")
    if tools_counts:
        bad = {k: v for k, v in tools_counts.items() if k in ("tools DEGRADED", "tools FAILED", "tools UNKNOWN")}
        L.append("الأدوات: " + f"{tools_counts.get('tools OK', 0)} سليمة" + (("، " + "، ".join(f"{v} {_TOOL_AR[k]}" for k, v in bad.items())) if bad else ""))
        if tool_names:
            L.append("  المتدهور: " + "، ".join(tool_names[:4]))
    if pins is not None:
        nxt = f" | التالي: {pins['next'][1]} ({pins['next'][0]})" if pins.get("next") else ""
        L.append(f"Pinterest: {pins['due']} دبوساً حان موعده، {pins['later']} مجدولاً{nxt}.")
    if automation:
        L.append(f"الآلية: {automation['automatic_or_gated']} من {automation['capabilities']} قدرة آلية أو مشروطة ({automation['percent']}%)؛ الباقي بوابة بشرية أو ينتظر حساباً/قراراً منك.")
    if connectors is not None:
        rows = connectors.get("last_intake", [])
        if rows:
            newest = min(r["age_hours"] for r in rows)
            L.append(f"الموصلات: آخر جولة قبل {newest:.0f} ساعة | نقرات Pinterest الخارجة: {connectors.get('pin_outbound_clicks', 0)} "
                     f"({connectors.get('pins_measured', 0)} دبوساً مقيساً)" + (" | الجولة متأخرة" if newest > 48 else ""))
        else:
            L.append("الموصلات: لم تُسجَّل جولة بعد.")
    L.append("")
    L.append("المصدر: فحوص المصنع الحية، لا تقدير.")
    return "\n".join(L)


def gather(today):
    import autonomy_selfcheck
    stages = autonomy_selfcheck.collect()
    snap = _json(ROOT / "data" / "autonomy_status.json", {}) or {}
    regs = snap.get("regressions", [])
    counts = {k: v for k, v in (snap.get("counts") or {}).items() if k.startswith("tools ")}
    tool_names = [r["name"] for r in snap.get("rows", []) if str(r.get("stage", "")).startswith("T:") and r.get("status") in ("DEGRADED", "FAILED")]
    registry = _json(ROOT / "data" / "product_registry.json", None)
    try:
        import demand_gate
        demand = demand_gate.evaluate()
    except Exception:  # noqa: BLE001
        demand = None
    pins = pinterest_summary(_jsonl(ROOT / "data" / "pinterest_manual_posts.jsonl"), today)
    try:
        import connector_intake
        connectors = connector_intake.summary(ROOT / "data" / "connector_intake.jsonl")
    except Exception:  # noqa: BLE001
        connectors = None
    try:
        import company_scorecard
        automation = company_scorecard.score(company_scorecard.evaluate(*company_scorecard.gather()))
    except Exception:  # noqa: BLE001
        automation = None
    return dict(today=today, stages=stages, tools_counts=counts, regressions=regs, registry=registry, demand=demand,
                pins=pins, tool_names=tool_names, connectors=connectors, automation=automation)


def run_once(now=None, state_path=STATE, gather_fn=None, sender=None):
    now = now or datetime.now(timezone.utc)
    today = now.date().isoformat()
    st = _json(state_path, {}) or {}
    if st.get("sent_day") == today:
        return {"action": "none", "detail": f"digest already sent for {today}"}
    if now.hour < SEND_FROM_HOUR_UTC:
        return {"action": "none", "detail": f"waiting for {SEND_FROM_HOUR_UTC:02d}:00 UTC"}
    attempts = st.get("attempts", 0) if st.get("attempt_day") == today else 0
    if attempts >= MAX_ATTEMPTS:
        return {"action": "none", "detail": f"gave up for {today} after {attempts} failed sends"}
    msg = build_message(**(gather_fn or gather)(today))
    if sender is None:
        from gf_ops import alerts
        sender = lambda subject, body: alerts.send_alert(subject=subject, body=body, category="DIGEST",  # noqa: E731
                                                          evidence="data/autonomy_status.json", next_step="لا شيء مطلوب",
                                                          window_hours=1)
    r = sender("ملخص المصنع اليومي", msg)
    delivered = bool(r.get("delivered"))
    new = {"attempt_day": today, "attempts": attempts + (0 if delivered else 1)}
    if delivered:
        new["sent_day"] = today
    Path(state_path).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(state_path) + ".tmp")
    tmp.write_text(json.dumps(new), encoding="utf-8")
    tmp.replace(state_path)
    return {"action": "sent" if delivered else "retry", "detail": f"digest {'delivered' if delivered else 'not delivered (' + str(r.get('channel')) + '), will retry'}"}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--preview" in argv:
        sys.stdout.buffer.write((build_message(**gather(datetime.now(timezone.utc).date().isoformat())) + "\n").encode("utf-8"))
        return 0
    try:
        r = run_once()
    except Exception as e:  # reported to the loop, never thrown
        r = {"action": "failed", "detail": f"{type(e).__name__}: {str(e)[:200]}"}
    sys.stdout.write(json.dumps(r, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
