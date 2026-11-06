import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import data_integrity_check as d


def test_bom_and_utf16_parse(tmp_path):
    assert d.parse_json_bytes(b"\xef\xbb\xbf{\"a\":1}") == {"a": 1}
    assert d.parse_json_bytes('{"a":2}'.encode("utf-16")) == {"a": 2}


def test_scan_finds_bad_json_and_bad_jsonl_lines(tmp_path):
    (tmp_path / "data").mkdir(); (tmp_path / "config").mkdir()
    (tmp_path / "data" / "ok.json").write_text("{}", encoding="utf-8")
    (tmp_path / "data" / "bad.json").write_text("{oops", encoding="utf-8")
    (tmp_path / "data" / "l.jsonl").write_text('{"a":1}\nnot json\n{"b":2}\n', encoding="utf-8")
    bj, bl = d.scan(tmp_path)
    assert bj == ["data/bad.json"] and bl == {"data/l.jsonl": 1}


def test_known_files_are_tolerated_new_ones_flagged():
    known = {"json": ["data/old.json"], "jsonl": {"data/l.jsonl": 3}}
    assert d.compare(["data/old.json"], {"data/l.jsonl": 3}, known) == ([], {})
    assert d.compare(["data/old.json", "data/new.json"], {"data/l.jsonl": 4, "data/x.jsonl": 1}, known) == (["data/new.json"], {"data/l.jsonl": 4, "data/x.jsonl": 1})
