"""Guards for B13-001's local listing payload builder.

These tests prove the asset builder (a) runs clean, (b) never claims a
publication that did not happen, (c) reports the price-realism arithmetic
exactly as the real economics module computes it, and (d) keeps its copy
tied to the real artefact facts rather than aspirational ones.

Run: python -m pytest tests/test_b13_001_listing_assets.py -q
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import economics

SCRIPT = ROOT / "scripts" / "build_b13_001_listing_assets.py"
PAYLOAD = ROOT / "reports" / "B13-001" / "LISTING_PAYLOAD_2026-10-20.json"
COPY = ROOT / "drafts" / "b13_001_listing_copy.txt"


def _load_module():
    spec = importlib.util.spec_from_file_location("b13_listing_assets", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def module():
    return _load_module()


@pytest.fixture(scope="module")
def payload(module):
    rc = module.main()
    assert rc == 0, "builder reported problems; it must be clean before these assertions mean anything"
    return json.loads(PAYLOAD.read_text(encoding="utf-8"))


def test_builder_reports_no_problems(payload):
    assert payload["problems"] == []


def test_payload_never_claims_publication(payload):
    assert payload["published"] is False
    assert payload["gumroad_call_made"] is False
    assert payload["state"] == "LOCAL_READY__AWAITS_FOUNDER_LISTING_AUTHORIZATION"


def test_price_is_marked_unauthorized(payload):
    assert payload["price_status"] == "PROPOSED_NOT_AUTHORIZED"
    assert payload["authorization_required"]["price_decision_required_first"] is True


def test_declared_hashes_match_the_real_files(payload):
    assert len(payload["files"]) == 2
    for row in payload["files"]:
        on_disk = ROOT / row["path"]
        assert on_disk.exists(), row["path"]
        assert hashlib.sha256(on_disk.read_bytes()).hexdigest() == row["sha256"]
        assert on_disk.stat().st_size == row["bytes"]


def test_cover_is_a_gumroad_landscape(payload):
    assert payload["cover"]["exists"] is True
    assert payload["cover"]["dimensions"] == [1280, 720]


def test_price_matrix_matches_the_economics_module(payload):
    cfg = economics.load_config()
    assert len(payload["price_realism"]["matrix"]) == 4
    for row in payload["price_realism"]["matrix"]:
        real = economics.evaluate(row["price_usd"], row["platform"], cfg, page_count=row["pages"])
        assert real["approved"] is row["approved"]
        assert real["market_realistic"] is row["market_realistic"]
        assert round(real["net_profit"], 2) == round(row["net_profit_usd"], 2)


def test_the_known_bind_is_still_true(payload):
    """$19 at the current depth is approved but unrealistic; $15 clears both."""
    rows = {(r["price_usd"], r["platform"], r["pages"]): r for r in payload["price_realism"]["matrix"]}
    pages = payload["verification_evidence"]["guide_pages"]
    non_premium = rows[(19.0, "gumroad_digital", pages)]
    premium = rows[(19.0, "gumroad_premium", pages)]
    fifteen = rows[(15.0, "gumroad_digital", pages)]
    assert non_premium["approved"] is True and non_premium["market_realistic"] is False
    assert premium["approved"] is False and premium["min_required_usd"] == 25.0
    assert fifteen["approved"] is True and fifteen["market_realistic"] is True


def test_listing_copy_cites_the_real_page_count(payload):
    pages = payload["verification_evidence"]["guide_pages"]
    assert pages >= 15, "the guide was expanded past the 15-page threshold; keep it honest"
    assert "%d-page" % pages in payload["listing_copy"]["text"]


def test_listing_copy_passes_the_brand_gate(payload):
    assert payload["brand_check"]["passed"] is True
    assert payload["brand_check"]["failed_checks"] == []


def test_listing_copy_makes_no_sales_claim(payload):
    text = payload["listing_copy"]["text"].lower()
    assert "no sales recorded yet" in text
    assert "no reviews" in text


def test_outputs_use_repo_newline_and_encoding_conventions(payload):
    """LF, no BOM, trailing newline -- the convention every reports/ JSON follows.

    Caught a real defect: Path.write_text() translates newlines on Windows, so
    the first two generated files landed as CRLF while their siblings are LF.
    """
    for path in (PAYLOAD, ROOT / "reports" / "B13-001" / "LISTING_PAYLOAD_2026-10-20.md"):
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), "%s has a BOM" % path.name
        assert b"\r" not in raw, "%s uses CRLF" % path.name
        assert raw.endswith(b"\n"), "%s has no trailing newline" % path.name


def test_builder_source_cannot_publish_or_spend():
    """A structural guard: the builder must never gain a network or publish path.

    Checked against the parsed AST, not raw text: the module's own docstring
    legitimately says it never calls Gumroad, and a substring match on the
    word would fail on that promise rather than verify it.
    """
    import ast

    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))

    network_modules = {"requests", "urllib", "urllib2", "http", "httpx", "aiohttp", "socket"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in network_modules, "no network import: %s" % alias.name
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            assert root not in network_modules, "no network import: %s" % node.module

    http_methods = {"post", "put", "patch", "delete", "request"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in http_methods, "no HTTP call: .%s()" % node.func.attr
