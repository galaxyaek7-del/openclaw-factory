import json, sys, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_bundle as bb


def _prod(i, cents):
    return {"id": i, "title": "Tool " + i, "price_cents": cents}


def test_bundle_contains_unchanged_member_zips_and_manifest(tmp_path):
    for i in ("B90-001", "B90-002"):
        d = tmp_path / "books" / "batch90" / i
        d.mkdir(parents=True)
        (d / "x_bundle.zip").write_bytes(b"zip-" + i.encode())
    r = bb.build("B90", root=tmp_path, products=[_prod("B90-001", 1000), _prod("B90-002", 2000), _prod("B91-001", 900)])
    assert r["ok"] and r["members"] == 2 and r["individual_total_usd"] == 30.0
    assert r["price_usd"] == 18  # 60% of 30
    with zipfile.ZipFile(r["zip"]) as z:
        names = z.namelist()
        assert "README.txt" in names and "MANIFEST.json" in names
        man = json.loads(z.read("MANIFEST.json"))
        assert [m["id"] for m in man] == ["B90-001", "B90-002"]
        assert z.read("B90-001_x_bundle.zip") == b"zip-B90-001"


def test_missing_files_are_reported_not_invented(tmp_path):
    d = tmp_path / "books" / "batch90" / "B90-001"
    d.mkdir(parents=True)
    (d / "a_bundle.zip").write_bytes(b"1")
    r = bb.build("B90", root=tmp_path, products=[_prod("B90-001", 1000), _prod("B90-002", 1000)])
    assert r["members"] == 1 and r["missing"] == ["B90-002"]
    assert bb.build("B77", root=tmp_path, products=[])["ok"] is False
