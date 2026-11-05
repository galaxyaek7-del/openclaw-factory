import json
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import telegram_bind as tb  # noqa: E402


def upd(chat_id, text, kind="private"):
    return {"message": {"chat": {"id": chat_id, "type": kind}, "text": text}}


def setup(tmp_path):
    p, b = tmp_path / "p.json", tmp_path / "b.json"
    return p, b, tb.issue(p)


def test_binds_only_with_the_right_code(tmp_path):
    p, b, code = setup(tmp_path)
    r = tb.run_once(p, b, fetch=lambda: [upd(1, "hello"), upd(2, "GF-00000000")], notify=lambda t: {"sent": True})
    assert r["action"] == "waiting" and not b.exists()
    r = tb.run_once(p, b, fetch=lambda: [upd(1, "hello"), upd(7, "/start " + code)], notify=lambda t: {"sent": True})
    assert r["action"] == "bound" and json.loads(b.read_text())["chat_id"] == "7" and not p.exists()


def test_group_message_with_the_code_does_not_bind(tmp_path):
    p, b, code = setup(tmp_path)
    r = tb.run_once(p, b, fetch=lambda: [upd(-100, code, kind="group")], notify=lambda t: {"sent": True})
    assert r["action"] == "waiting" and not b.exists()


def test_expired_code_is_discarded(tmp_path):
    p, b, code = setup(tmp_path)
    later = tb._now() + timedelta(hours=25)
    r = tb.run_once(p, b, fetch=lambda: [upd(7, code)], notify=lambda t: {"sent": True}, now=later)
    assert r["action"] == "expired" and not p.exists() and not b.exists()


def test_code_is_not_stored_in_clear(tmp_path):
    p, b, code = setup(tmp_path)
    assert code not in p.read_text()


def test_sender_uses_binding_when_env_has_no_chat(tmp_path):
    from channels import telegram_direct as td
    f = tmp_path / "b.json"
    f.write_text(json.dumps({"chat_id": "42"}))
    assert td.bound_chat_id(f) == "42" and td.bound_chat_id(tmp_path / "none.json") is None
