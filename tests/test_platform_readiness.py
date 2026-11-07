import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import platform_readiness as pr  # noqa: E402


def test_every_platform_has_every_field_and_a_known_evidence_class():
    for n, f in pr.PLATFORMS.items():
        assert {"fees", "api_create", "spend", "cls", "account", "payout", "path", "arm"} <= set(f), n
        assert f["cls"] in ("OBSERVED", "SECONDARY", "UNKNOWN") and f["api_create"] in ("YES", "NO", "UNKNOWN") and f["spend"] in ("NONE", "PAID", "UNKNOWN")
    assert set(pr.ORDER) == set(pr.PLATFORMS)


def test_a_paid_platform_is_never_reported_ready_and_a_free_one_without_account_needs_the_founder():
    ready_arm = "READY"
    assert pr.verdict(pr.PLATFORMS["shopify"], ready_arm) == "NEEDS_SPEND_APPROVAL"
    assert pr.verdict(pr.PLATFORMS["etsy"], ready_arm) == "NEEDS_SPEND_APPROVAL"
    assert pr.verdict(pr.PLATFORMS["payhip"], "UNAVAILABLE") == "MANUAL_PATH_NEEDS_ACCOUNT"
    assert pr.verdict(pr.PLATFORMS["gumroad"], "READY") == "READY"
    assert pr.verdict(pr.PLATFORMS["paddle"], "READY") == "UNKNOWN_COST"


def test_payhip_has_no_product_api_in_the_matrix_and_the_matrix_builds():
    assert pr.PLATFORMS["payhip"]["api_create"] == "NO"
    rows = pr.matrix()
    assert [r["platform"] for r in rows] == pr.ORDER and all("arm_status" in r and "verdict" in r for r in rows)


def test_kit_carries_price_files_and_the_approval_reminder(tmp_path):
    import json
    d = tmp_path / "books" / "batch18" / "B18-999"
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(json.dumps({"id": "B18-999", "title": "T", "price_cents": 2900, "category": "C", "tags": ["a", "b"],
                                                  "files": {"workbook": {"path": "books/batch18/B18-999/x.xlsx", "bytes": 5, "sha256": "ab" * 32}}}), encoding="utf-8")
    t = pr.kit_text("B18-999", "payhip", tmp_path)
    assert "Price: $29" in t and "x.xlsx" in t and "approved THIS product by name" in t
