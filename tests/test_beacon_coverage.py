import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import beacon_coverage as bc  # noqa: E402

TAG = '<script src="assets/gf-pageview.js" defer></script>'


def test_missing_duplicate_and_noindex_are_told_apart(tmp_path):
    d = tmp_path / "customer_site"
    d.mkdir()
    (d / "ok.html").write_text(f"<html>{TAG}</html>", encoding="utf-8")
    (d / "twice.html").write_text(f"<html>{TAG}{TAG}</html>", encoding="utf-8")
    (d / "none.html").write_text("<html></html>", encoding="utf-8")
    (d / "old_only.html").write_text('<html><script>fetch("/api/page-view")</script></html>', encoding="utf-8")
    (d / "hidden.html").write_text('<html><meta name="robots" content="noindex"></html>', encoding="utf-8")
    r = bc.scan(tmp_path)
    assert r["once"] == 1 and len(r["duplicate"]) == 1
    assert sorted(Path(p).name for p in r["missing"]) == ["none.html", "old_only.html"]
    assert [Path(p).name for p in r["noindex_missing"]] == ["hidden.html"]
