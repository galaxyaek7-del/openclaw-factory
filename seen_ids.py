"""Seen-opportunity registry (efficiency): one append-only set of already-
processed Freelancer project IDs, replacing the per-cycle loading of ~15
scattered demand/hunt/sweep files to build the known-set.

Usage:
    from seen_ids import load_known, add_ids
    known = load_known()          # set[int]
    add_ids([40740001, ...])      # idempotent append
"""
import json
import os

PATH = "data/seen_opportunities.json"


def load_known():
    try:
        with open(PATH, encoding="utf-8") as fh:
            return set(json.load(fh).get("ids", []))
    except (OSError, ValueError):
        return set()


def add_ids(ids):
    known = load_known()
    before = len(known)
    for i in ids:
        if isinstance(i, int):
            known.add(i)
    with open(PATH, "w", encoding="utf-8") as fh:
        json.dump({"ids": sorted(known)}, fh)
    return len(known) - before


def build_from_legacy():
    """One-time migration: harvest every id from legacy demand files."""
    import glob

    found = set()
    files = ["data/global_pipeline.json"] + glob.glob("data/demand_*.json") + \
        glob.glob("data/hunt*.json") + glob.glob("data/*sweep*.json") + \
        ["data/escape_hunt.json"]
    for f in files:
        try:
            d = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        items = d if isinstance(d, list) else (
            d.get("active", []) + d.get("rejected", []) + d.get("held", []))
        for i in items:
            if isinstance(i, dict) and isinstance(i.get("id"), int):
                found.add(i["id"])
    return add_ids(found), len(found)
