"""Apply ONLY the two Telegram relay workflows (03_Production_Notify, 04_Telegram_Notify) to the live n8n (2026-11-06).

Why a separate script: apply_fix.py re-imports all six files, including older copies of Sales_Poll and
Openclaw_Sensing_Engine, which would overwrite the later webhook hardening on the live instance. These two workflows
are the only ones still failing (29/29 runs since 2026-10-23: `$env` is blocked in n8n 2.x). Everything else is untouched.

  python apply_telegram_only.py              apply, then run the live check
  python apply_telegram_only.py --check      live check only (one test message to the founder's own chat)
  python apply_telegram_only.py --rollback BACKUP_DIR

Safety (same as apply_fix.py): database backup first; only the exact `n8n start` PID is stopped; the plaintext
credential file lives in a private temp dir deleted in `finally`; the bot token and webhook secret are read from .env
and never printed. The webhooks stay protected by header auth (credential GFwebhookSecr01 already in n8n).
"""
import json
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import apply_fix as af  # noqa: E402

FILES = ["03_Production_Notify.json", "04_Telegram_Notify.json"]
WEBHOOKS = {"04_Telegram_Notify.json": "golden-hunter-notify", "03_Production_Notify.json": "production-notify"}


def webhook_base():
    url = af.env_value("N8N_TELEGRAM_WEBHOOK_URL")
    m = re.match(r"(https?://[^/]+)/webhook/", url or "")
    return m.group(1) if m else "http://localhost:5678"


def post(url, payload, secret=None, timeout=60):
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["X-GF-Webhook-Secret"] = secret
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:  # noqa: BLE001
        return type(e).__name__


def live_check():
    """Local base URL (never the public tunnel): an unauthenticated call must be refused, an authenticated one accepted."""
    secret = af.env_value("N8N_WEBHOOK_SECRET")
    base = "http://localhost:5678/webhook/golden-hunter-notify"
    unauth = post(base, {"event": "golden_opportunity_accepted", "niche": "TEST", "opportunity_score": 0})
    auth = post(base, {"event": "golden_opportunity_accepted", "niche": "اختبار n8n", "opportunity_score": 99, "price": 0,
                       "reason": "SIMULATION: n8n relay check, no real opportunity", "generated_at": ""}, secret)
    print("unauthenticated call ->", unauth, "(expect 403)")
    print("authenticated call   ->", auth, "(expect 200)")
    return unauth in (401, 403) and auth == 200


def main():
    bot = af.env_value("TELEGRAM_BOT_TOKEN")
    chat = af.env_value("OPENCLAW_TELEGRAM_CHAT_ID")
    if not bot or not re.fullmatch(r"-?\d{5,20}", chat or ""):
        raise SystemExit("TELEGRAM_BOT_TOKEN or a valid OPENCLAW_TELEGRAM_CHAT_ID missing in .env; nothing applied")
    bdir = af.backup()
    print("backup:", bdir)
    af.stop_n8n()
    tmp = Path(tempfile.mkdtemp(prefix="gf_n8n_"))
    try:
        (tmp / "creds.json").write_text(json.dumps([{"id": "GFtelegramBot001", "name": "GF Telegram Bot", "type": "telegramApi",
                                                      "data": {"accessToken": bot}}]), encoding="utf-8")
        af.cli("import:credentials", f"--input={tmp / 'creds.json'}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        print("plaintext credential file removed:", not tmp.exists())
    wdir = Path(tempfile.mkdtemp(prefix="gf_n8n_wf_"))
    try:
        for name in FILES:
            text = (HERE / name).read_text(encoding="utf-8").replace("__GF_TELEGRAM_CHAT_ID__", chat)
            (wdir / name).write_text(text, encoding="utf-8")
        af.cli("import:workflow", "--separate", f"--input={wdir}")
    finally:
        shutil.rmtree(wdir, ignore_errors=True)
    for name in FILES:
        af.cli("publish:workflow", f"--id={json.loads((HERE / name).read_text(encoding='utf-8'))['id']}")
    print("n8n healthz after restart:", af.start_n8n())
    print("rollback command: python apply_telegram_only.py --rollback", bdir)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--rollback":
        af.rollback(sys.argv[2])
    elif "--check" in sys.argv:
        sys.exit(0 if live_check() else 1)
    else:
        main()
        sys.exit(0 if live_check() else 1)
