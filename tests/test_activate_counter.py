import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import activate_counter as ac  # noqa: E402

SRC = "x();\r\n  var GF_COUNTER_CODE = '';\r\n  y();\r\n"


def test_sets_the_code_keeps_line_endings_and_is_idempotent(tmp_path):
    f = tmp_path / "gf-pageview.js"
    f.write_bytes(SRC.encode("utf-8"))
    r = ac.apply("MySite.goatcounter.com", f)
    assert r["ok"] and r["changed"] and r["endpoint"] == "https://mysite.goatcounter.com/count"
    assert f.read_bytes().decode("utf-8") == SRC.replace("''", "'mysite'")
    assert ac.apply("mysite", f)["changed"] is False


def test_rejects_unsafe_values_and_dry_run_writes_nothing(tmp_path):
    f = tmp_path / "gf-pageview.js"
    f.write_bytes(SRC.encode("utf-8"))
    for bad in ("", "a", "x y", "evil';alert(1);//", "UP_PER"):
        assert ac.apply(bad, f)["ok"] is False
    assert ac.apply("okname", f, dry_run=True)["changed"] is True
    assert f.read_bytes().decode("utf-8") == SRC
