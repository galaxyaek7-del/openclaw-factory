"""Read a Pinterest account's public boards and their real ids (read-only).

The Metricool connector has no board tool, and a boardId must never be typed
or guessed. Pinterest's public profile page embeds each board as a JSON object
({"type": "board", "id": ..., "url": "/<user>/<slug>/", "name": ...}); this
module extracts exactly those objects (brace-matched and parsed, not a nearby
number) and returns them. Only public boards are visible this way.
Parsing only: the package holds no network client (a tested rule); the page is
fetched by scripts/pinterest_queue.py.
"""
from __future__ import annotations

import json
import re

TARGET_BOARD_NAME = "Small Business Finance Tools"


def _enclosing_object(text: str, pos: int) -> str | None:
    depth, i = 0, pos
    while i > 0:
        i -= 1
        if text[i] == "}":
            depth += 1
        elif text[i] == "{":
            if depth == 0:
                break
            depth -= 1
    start, depth, in_str, esc = i, 0, False, False
    for j in range(start, len(text)):
        c = text[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start:j + 1]
    return None


def parse_boards(html: str, username: str) -> dict:
    """slug -> {"id", "name", "privacy", "url"}; a slug with conflicting ids is dropped."""
    found, conflict = {}, set()
    for m in re.finditer(r'"url"\s*:\s*"(/%s/([a-z0-9-]+)/)"' % re.escape(username), html):
        raw = _enclosing_object(html, m.start())
        try:
            obj = json.loads(raw) if raw else None
        except ValueError:
            continue
        if not isinstance(obj, dict) or obj.get("type") != "board" or obj.get("url") != m.group(1):
            continue
        rec = {"id": str(obj.get("id")), "name": obj.get("name"), "privacy": obj.get("privacy"), "url": m.group(1)}
        slug = m.group(2)
        if slug in found and found[slug]["id"] != rec["id"]:
            conflict.add(slug)
        found.setdefault(slug, rec)
    return {k: v for k, v in found.items() if k not in conflict and re.fullmatch(r"\d{10,20}", v["id"] or "")}


def find_board(boards: dict, name: str = TARGET_BOARD_NAME) -> dict | None:
    """The board whose name matches (case and spacing insensitive), public only."""
    want = re.sub(r"\s+", " ", name).strip().lower()
    for b in boards.values():
        if re.sub(r"\s+", " ", b.get("name") or "").strip().lower() == want and b.get("privacy") == "public":
            return b
    return None
