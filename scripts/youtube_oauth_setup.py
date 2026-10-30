#!/usr/bin/env python3
"""One-time YouTube sign-in for the children's channel (run by the founder).

Before running: in Google Cloud Console (your own account), create a project,
enable "YouTube Data API v3", configure the OAuth consent screen, and create an
OAuth client ID of type "Desktop app". Download its JSON.

    python scripts/youtube_oauth_setup.py path/to/client_secret.json

It opens Google's consent page in your browser (scope youtube.upload and
youtube.force-ssl for captions), receives the code on a one-time listener bound
to 127.0.0.1 (never exposed), exchanges it for a refresh token, and writes
YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET and YOUTUBE_REFRESH_TOKEN into .env.
No token is printed. Sign in with the account that owns the channel.
"""
import http.server
import json
import secrets
import sys
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.force-ssl"


def set_env_values(values, env_path=ROOT / ".env"):
    """Replace or append KEY=value lines; other lines are kept as they are."""
    env_path = Path(env_path)
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.is_file() else []
    keys = set(values)
    kept = [l for l in lines if l.split("=", 1)[0].strip() not in keys]
    kept += ["%s=%s" % (k, v) for k, v in values.items()]
    env_path.write_text("\n".join(kept) + "\n", encoding="utf-8")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 2
    cfg = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    cfg = cfg.get("installed") or cfg.get("web") or cfg
    client_id, client_secret = cfg["client_id"], cfg["client_secret"]
    state = secrets.token_urlsafe(16)
    got = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state", [""])[0] == state and q.get("code"):
                got["code"] = q["code"][0]
                msg = "Done. You can close this tab."
            else:
                msg = "Sign-in failed or was cancelled."
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(msg.encode())

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    redirect = "http://127.0.0.1:%d/" % server.server_port
    url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": client_id, "redirect_uri": redirect, "response_type": "code", "scope": SCOPES,
        "access_type": "offline", "prompt": "consent", "state": state})
    print("Opening Google sign-in. If it does not open, paste this address into your browser:\n" + url)
    webbrowser.open(url)
    server.timeout = 300
    server.handle_request()
    server.server_close()
    if "code" not in got:
        print("No authorization code received.")
        return 1
    body = urllib.parse.urlencode({"code": got["code"], "client_id": client_id, "client_secret": client_secret,
                                   "redirect_uri": redirect, "grant_type": "authorization_code"}).encode()
    with urllib.request.urlopen(urllib.request.Request(TOKEN_URL, data=body), timeout=60) as r:
        tok = json.loads(r.read())
    if not tok.get("refresh_token"):
        print("Google returned no refresh token; revoke the app's access in your Google account and run again.")
        return 1
    set_env_values({"YOUTUBE_CLIENT_ID": client_id, "YOUTUBE_CLIENT_SECRET": client_secret,
                    "YOUTUBE_REFRESH_TOKEN": tok["refresh_token"]})
    print("Saved the YouTube credentials to .env (values not shown).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
