import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import constitution_wiring as cw  # noqa: E402


def tree(tmp_path):
    (tmp_path / "factory_loop.js").write_text("const a = require('./lib/wired_mod');", encoding="utf-8")
    (tmp_path / "server.js").write_text("// nothing", encoding="utf-8")
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "wired_mod.js").write_text("// reached from the loop", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "manual_tool.py").write_text("import dormant_mod", encoding="utf-8")
    (tmp_path / "dormant_mod.py").write_text("x = 1", encoding="utf-8")
    (tmp_path / "lonely.py").write_text("y = 2", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_lonely.py").write_text("import lonely", encoding="utf-8")


def test_wired_manual_dormant_and_missing_are_told_apart(tmp_path):
    tree(tmp_path)
    got = {r["module"]: r["status"] for r in cw.classify(["lib/wired_mod.js", "dormant_mod.py", "lonely.py", "gone.py"], tmp_path)}
    assert got == {"lib/wired_mod.js": "WIRED", "dormant_mod.py": "MANUAL", "lonely.py": "DORMANT", "gone.py": "MISSING"}


def test_citations_are_read_from_backticks(tmp_path):
    d = tmp_path / "doc.md"
    d.write_text("Article 1 is enforced by `brand_dna.py` and `lib/x.js`; ignore plain words.py", encoding="utf-8")
    assert set(cw.cited([d])) == {"brand_dna.py", "lib/x.js"}
