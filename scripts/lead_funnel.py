#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Founder tool: track real prospects (e.g. Umrah agencies you contacted) through the funnel.

A thin wrapper over lead_discovery.transition_lead / funnel_summary. It sends nothing to anyone.

    python scripts/lead_funnel.py show
    python scripts/lead_funnel.py move --lead agence-x --to QUALIFIED --source "met at the fair 2026-11-12"
    python scripts/lead_funnel.py move --lead agence-x --to QUALIFIED --source "..." --apply

Stages: NEW -> QUALIFIED -> CONTACTED -> REPLIED -> PROPOSAL -> WON, or LOST from any stage.
A lead enters the funnel only with a real --source. `move` is a dry run unless --apply is given.
WON means a real customer who paid: write it only when it happened.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lead_discovery as ld  # noqa: E402


def build_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("show", "move"):
        s = sub.add_parser(name)
        s.add_argument("--path", default=None, help="funnel file (tests); default data/prospect_pipeline.jsonl")
    sub.choices["show"].add_argument("--lead", default=None, help="history of one lead")
    m = sub.choices["move"]
    m.add_argument("--lead", required=True)
    m.add_argument("--to", required=True, choices=ld.FUNNEL_STAGES)
    m.add_argument("--source", default=None, help="real source of the lead (required the first time)")
    m.add_argument("--reason", default=None)
    m.add_argument("--apply", action="store_true", help="actually record (default: dry run)")
    return p.parse_args(argv)


def run(args) -> int:
    if args.cmd == "show":
        if args.lead:
            print(json.dumps(ld.lead_funnel(args.lead, args.path), ensure_ascii=False, indent=1))
        else:
            print(json.dumps(ld.funnel_summary(args.path), ensure_ascii=False, indent=1))
        return 0
    current = ld.lead_stage(args.lead, args.path)
    plan = {"lead": args.lead, "from": current or "(not in funnel)", "to": args.to, "source": args.source}
    if not args.apply:
        print(json.dumps({"dry_run": True, "would_record": plan}, ensure_ascii=False, indent=1))
        print("Nothing written. Add --apply to record it.")
        return 0
    try:
        ev = ld.transition_lead(args.lead, args.to, source_ref=args.source, reason=args.reason, path=args.path)
    except (ld.IllegalFunnelTransition, ld.MissingLeadSource, ValueError) as e:
        print("REFUSED: %s" % e)
        return 2
    print("RECORDED: %s %s -> %s" % (ev["lead_id"], ev["from_stage"], ev["to_stage"]))
    return 0


if __name__ == "__main__":
    sys.exit(run(build_args()))
