import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import sales_path_audit as a  # noqa: E402

BASE = a.BASE


def site(tmp_path, sitemap_urls, pages, catalog):
    (tmp_path / "customer_site").mkdir(parents=True)
    (tmp_path / "sitemap.xml").write_text("".join(f"<url><loc>{BASE}{u}</loc></url>" for u in sitemap_urls), encoding="utf-8")
    (tmp_path / "customer_site" / "catalog.json").write_text(json.dumps({"data": {"products": catalog}}), encoding="utf-8")
    for name, body in pages.items():
        (tmp_path / "customer_site" / name).write_text(body, encoding="utf-8")


def test_clean_site_has_no_findings(tmp_path):
    cat = [{"id": "P1", "url": "https://x.gumroad.com/l/abc"}]
    site(tmp_path, ["customer_site/tool-p1.html"], {"tool-p1.html": '<a href="https://x.gumroad.com/l/abc">P1</a>'}, cat)
    assert a.audit(tmp_path) == []


def test_page_without_the_catalog_buy_url_is_high(tmp_path):
    cat = [{"id": "P1", "url": "https://x.gumroad.com/l/abc"}]
    site(tmp_path, ["customer_site/tool-p1.html"], {"tool-p1.html": "P1 no link"}, cat)
    assert [f["severity"] for f in a.audit(tmp_path)] == ["HIGH"]


def test_sitemap_url_without_file_and_noindex_page_are_reported(tmp_path):
    site(tmp_path, ["customer_site/gone.html", "customer_site/n.html"], {"n.html": '<meta name="robots" content="noindex">'}, [])
    sev = sorted(f["severity"] for f in a.audit(tmp_path))
    assert sev == ["HIGH", "MEDIUM"]
