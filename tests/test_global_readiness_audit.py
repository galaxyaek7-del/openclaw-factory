import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import global_readiness_audit as ga  # noqa: E402


def page(site, name, body, lang='lang="en"', head=""):
    (site / name).write_text(f"<!doctype html><html {lang}><head>{head}</head><body>{body}</body></html>", encoding="utf-8")


def test_audit_finds_missing_lang_trust_link_sitemap_and_broken_link(tmp_path):
    site = tmp_path / "customer_site"; (site / "trust").mkdir(parents=True)
    page(site, "a.html", '<a href="b.html">b</a><a href="trust/privacy-policy.html">p</a><a href="missing.html">x</a><a href="https://x.com/y">ext</a>')
    page(site, "b.html", "no links", lang="")
    page(site, "hidden.html", "x", head='<meta name="robots" content="noindex">')
    page(site / "trust", "privacy-policy.html", "DRAFT TEMPLATE")
    sm = tmp_path / "sitemap.xml"
    sm.write_text("<urlset><url><loc>https://h/s/a.html</loc></url></urlset>")
    r = ga.run(site, sm, "https://h/s/")
    assert r["pages"] == 2 and r["no_lang"] == ["b.html"] and r["no_trust_link"] == ["b.html"]
    assert r["not_in_sitemap"] == ["b.html"] and r["broken_internal_links"] == ["a.html -> missing.html"]
    assert r["trust_pages_still_draft"] == ["privacy-policy.html"] and "DRAFT" in r["no_trust_link_blocker"]


def test_template_and_api_paths_are_not_reported_as_broken(tmp_path):
    site = tmp_path / "s"; site.mkdir()
    page(site, "a.html", '<a href="{{ x }}">t</a><a href="${y}">t</a><script src="mailto:a@b.c"></script>')
    sm = tmp_path / "sm.xml"; sm.write_text("")
    assert ga.run(site, sm, "https://h/")["broken_internal_links"] == []
