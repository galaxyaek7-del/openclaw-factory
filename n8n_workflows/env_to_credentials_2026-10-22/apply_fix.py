"""Apply the $env -> credentials fix to the LIVE n8n. Run only with founder approval.

Usage:  python apply_fix.py            (apply)
        python apply_fix.py --rollback BACKUP_DIR

Safety:
  * Backs up ~/.n8n/database.sqlite{,-wal,-shm} before touching anything.
  * Stops only the exact PID of `n8n start`, never node.exe by image name.
  * Plaintext credential JSON lives in a private temp dir and is deleted in a
    `finally` block, whether or not the import succeeds.
  * Telegram workflows are skipped (left exactly as they are) when
    OPENCLAW_TELEGRAM_CHAT_ID is not configured.
  * Restarts n8n through the same scheduled task that normally launches it.
"""
import json, os, re, shutil, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path(r"C:\openclaw-dasgboard")
N8N_DIR = Path.home() / ".n8n"
# Resolved from PATH, else the npm global bin under %APPDATA%; never a
# hardcoded user directory (tests/test_no_temp_dependencies.py).
N8N = shutil.which("n8n.cmd") or shutil.which("n8n") or os.path.join(os.environ.get("APPDATA", ""), "npm", "n8n.cmd")
TASK = "GalaxyForge-N8N-Autostart"
TELEGRAM_WF = {"03_Production_Notify.json", "04_Telegram_Notify.json"}
DB_FILES = ["database.sqlite", "database.sqlite-wal", "database.sqlite-shm"]


def env_value(name):
    v = os.environ.get(name, "").strip()
    if v:
        return v
    for line in (REPO / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[7:].strip()
        k, sep, val = line.partition("=")
        if sep and k.strip() == name:
            val = val.strip().strip("'\"")
            if val:
                return val
    return ""


def healthz():
    try:
        return urllib.request.urlopen("http://localhost:5678/healthz", timeout=5).status == 200
    except Exception:
        return False


def n8n_pid():
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "Get-CimInstance Win32_Process | ? { $_.CommandLine -match 'node_modules\\\\n8n\\\\bin\\\\n8n.* start' } | % { $_.ProcessId }"],
                         capture_output=True, text=True).stdout.split()
    return [int(p) for p in out if p.isdigit()]


def stop_n8n():
    for pid in n8n_pid():
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
    for _ in range(60):
        if not healthz() and not n8n_pid():
            return
        time.sleep(1)
    raise SystemExit("n8n did not stop; aborting before any import")


def start_n8n():
    subprocess.run(["powershell", "-NoProfile", "-Command", f"Start-ScheduledTask -TaskName '{TASK}'"], check=True)
    for _ in range(180):
        if healthz():
            return True
        time.sleep(2)
    return False


def cli(*args):
    env = dict(os.environ, N8N_DIAGNOSTICS_ENABLED="false")
    p = subprocess.run([N8N, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    tail = (p.stdout + p.stderr).strip().splitlines()[-2:]
    print("  n8n", args[0], "->", " | ".join(tail))
    if p.returncode != 0:
        raise RuntimeError(f"n8n {args[0]} failed")


def backup():
    dest = N8N_DIR / f"backup_gf_envfix_{time.strftime('%Y%m%d_%H%M%S')}"
    dest.mkdir()
    for f in DB_FILES:
        if (N8N_DIR / f).exists():
            shutil.copy2(N8N_DIR / f, dest / f)
    return dest


def rollback(src):
    src = Path(src)
    stop_n8n()
    for f in DB_FILES:
        if (src / f).exists():
            shutil.copy2(src / f, N8N_DIR / f)
        elif (N8N_DIR / f).exists():
            (N8N_DIR / f).unlink()
    print("restored from", src, "| n8n up:", start_n8n())


def main():
    token = env_value("INTERNAL_SERVICE_TOKEN")
    bot = env_value("TELEGRAM_BOT_TOKEN")
    chat = env_value("OPENCLAW_TELEGRAM_CHAT_ID")
    if not token:
        raise SystemExit("INTERNAL_SERVICE_TOKEN missing in .env; nothing applied")
    do_telegram = bool(bot and re.fullmatch(r"-?\d{5,20}", chat or ""))
    wf_dir = HERE / "fixed" if (HERE / "fixed").is_dir() else HERE
    files = sorted(p for p in wf_dir.glob("*.json") if do_telegram or p.name not in TELEGRAM_WF)
    print("telegram workflows:", "INCLUDED" if do_telegram else "SKIPPED (no valid OPENCLAW_TELEGRAM_CHAT_ID)")
    print("workflows to apply:", [p.stem for p in files])

    creds = [{"id": "GFinternalTokn01", "name": "GF Internal Service Token (X-Internal-Token)",
              "type": "httpHeaderAuth", "data": {"name": "X-Internal-Token", "value": token}}]
    if do_telegram:
        creds.append({"id": "GFtelegramBot001", "name": "GF Telegram Bot", "type": "telegramApi",
                      "data": {"accessToken": bot}})

    bdir = backup()
    print("backup:", bdir)
    stop_n8n()
    tmp = Path(tempfile.mkdtemp(prefix="gf_n8n_"))
    try:
        (tmp / "creds.json").write_text(json.dumps(creds), encoding="utf-8")
        cli("import:credentials", f"--input={tmp / 'creds.json'}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        print("plaintext credential file removed:", not tmp.exists())

    wdir = Path(tempfile.mkdtemp(prefix="gf_n8n_wf_"))
    try:
        for p in files:
            text = p.read_text(encoding="utf-8")
            if "__GF_TELEGRAM_CHAT_ID__" in text:
                text = text.replace("__GF_TELEGRAM_CHAT_ID__", chat)
            (wdir / p.name).write_text(text, encoding="utf-8")
        cli("import:workflow", "--separate", f"--input={wdir}")
    finally:
        shutil.rmtree(wdir, ignore_errors=True)
    for p in files:
        cli("publish:workflow", f"--id={json.loads(p.read_text(encoding='utf-8'))['id']}")
    up = start_n8n()
    print("n8n healthz after restart:", up)
    print("rollback command: python apply_fix.py --rollback", bdir)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--rollback":
        rollback(sys.argv[2])
    else:
        main()
