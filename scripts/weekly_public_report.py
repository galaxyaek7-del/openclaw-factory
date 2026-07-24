#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenClaw Factory — Weekly Public Report cron entrypoint (Build in
Public, 2026-07-24).

Real, thin CLI wrapper — reuses build_in_public.py directly, adds no
new logic. Generates the real weekly progress report and queues it for
the founder's approval via the real, already-live Telegram integration
— never auto-publishes anything.

Intended to be invoked by a real, durable OS-level scheduler (Windows
Task Scheduler — see ADR-119) every Friday, NOT by any live process
inside this factory's own code. This factory's own architecture still
has no internal scheduler (CLAUDE.md); this script is invoked from
outside it, exactly like scripts/poll_sales.py already is expected to
be run manually or by an external trigger.

    python scripts/weekly_public_report.py
"""

import sys
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

import build_in_public as bip


def main():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    report = bip.build_weekly_progress_report()
    result = bip.queue_draft_for_approval(
        "weekly_report",
        "Weekly Progress Report",
        report["report_markdown"],
        (
            "📊 مسوّدة تقرير التقدّم الأسبوعي (تلقائي — كل جمعة)، بانتظار موافقتك.\n"
            f"الأرقام الحقيقية: {report['scored']} فرصة قُيِّمت، {report['accepted']} مقبولة، "
            f"{report['rejected']} مرفوضة، إيراد حقيقي هذا الأسبوع: ${report['real_revenue_this_week']:.2f}.\n"
            "راجع الملف الكامل قبل النشر — لم يُنشَر بعد."
        ),
    )
    print(f"queued: {result['draft_path']}")
    print(f"telegram sent: {result['telegram']['sent']}")
    if not result["telegram"]["sent"]:
        print(f"telegram error: {result['telegram']['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
