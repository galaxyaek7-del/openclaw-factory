# -*- coding: utf-8 -*-
"""Modular tool registry + product-type QA stack selector.

This is the configuration/registry layer the founder directive asks for: the
factory can later add Language/Content/Originality/Visual/Design/Game/
PDF/Document/Data/Security/Performance tools by (a) adding an adapter in
quality_toolchain/adapters/, (b) declaring the tool in
config/quality_toolchain.json, (c) mapping it to a QA layer — WITHOUT
rewriting the production engine.

Key properties:
  - is_disabled(tool) is the single safe way to turn a tool off.
  - stack_for(product_type) returns the QA layers that apply to that product
    type (product-aware, not one universal checker).
  - tools_for_layer(layer) returns enabled tools implementing that layer.
  - a disabled/unavailable tool contributes NOTHING to a decision; it is
    recorded as skipped, never silently as a pass or a fail of its own.
"""

import json
import os

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, "config", "quality_toolchain.json"
)
CONFIG_PATH = os.path.normpath(CONFIG_PATH)


def load_config(path=None):
    path = path or CONFIG_PATH
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg


_cfg_cache = {}


def get_config(path=None):
    key = path or CONFIG_PATH
    if key not in _cfg_cache:
        _cfg_cache[key] = load_config(key)
    return _cfg_cache[key]


def all_tools(path=None):
    return dict(get_config(path).get("tools", {}))


def get_tool(tool_id, path=None):
    return all_tools(path).get(tool_id)


def is_disabled(tool_id, path=None):
    t = get_tool(tool_id, path)
    if not t:
        return True  # unknown tool is disabled by default
    return not bool(t.get("enabled", False))


def is_available(tool_id, env=None, path=None):
    """Availability = not disabled by config AND its capability is actually
    present in this environment (OBSERVED), unless the tool is explicitly
    marked stdlib-only/derived."""
    if is_disabled(tool_id, path):
        return False
    t = get_tool(tool_id, path)
    env = env if env is not None else _probe_env(tool_id)
    return bool(env)


def _probe_env(tool_id):
    import importlib.util as _u
    t = get_tool(tool_id)
    if not t:
        return False
    provider = t.get("provider", "")
    if provider == "stdlib":
        return True  # pure stdlib capability is always present
    if provider.startswith("pypi:"):
        pkg = provider.split(":", 1)[1]
        try:
            return bool(_u.find_spec(pkg))
        except Exception:
            return False
    return False


def stack_for(product_type, path=None):
    """Return the ordered QA layer names for a product type, per config.
    Unknown product types fall back to a conservative default stack (never
    empty — production must not silently skip all QA)."""
    cfg = get_config(path)
    start = cfg.get("product_types", {}).get(str(product_type or ""))
    if not start:
        start = cfg.get("product_types", {}).get("_fallback")
    return list((start or {}).get("stack", []))


def tools_for_layer(layer, path=None):
    """Enabled tool ids whose category/implementation map to a QA layer."""
    cfg = get_config(path)
    tools = all_tools(path)
    impls = (cfg.get("layers", {}).get(layer, {}) or {}).get("implements", [])
    out = []
    for tid in impls:
        t = tools.get(tid)
        if t and not is_disabled(tid, path):
            out.append(tid)
    return out


def list_layers(path=None):
    return sorted(get_config(path).get("layers", {}).keys())


def registry_summary(path=None):
    """Read-only registry snapshot used for reports/tests."""
    tools = all_tools(path)
    return {
        tid: {
            "category": t.get("category"),
            "classification": t.get("classification"),
            "license": t.get("license"),
            "enabled": not is_disabled(tid, path),
            "available": is_available(tid, path=path),
            "windows_compatible": t.get("windows_compatible"),
            "purpose": t.get("purpose"),
        }
        for tid, t in tools.items()
    }