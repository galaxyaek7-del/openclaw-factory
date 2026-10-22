"""Shared, hardened credential reader for the distribution arms.

Every arm needs the same thing: read one named secret from the process
environment, falling back to the factory's own `.env` file so a direct
Python entrypoint (CLI script, `python distributor.py`, a test harness)
sees the same configuration `server.js`/`factory_loop.js` see after their
own `dotenv` load.

Before this module, each publisher carried its own copy of the fallback,
and they had drifted apart:
  * gumroad_publisher.py had a hardened parser (exact key, `export`,
    quotes, inline comments) -- left untouched here, it has its own
    live-verified history;
  * payhip/paddle/etsy matched by bare PREFIX (`PADDLE_API_KEY_SANDBOX=`
    would be read as `PADDLE_API_KEY`), kept surrounding quotes (a quoted
    key was sent with literal quote characters -> a confusing 401), and
    raised IndexError on a key line with no `=`;
  * x_arm/kdp_arm had no `.env` fallback at all, so X reported
    UNAVAILABLE from any Python entrypoint even with all four keys
    configured.

Never logs or returns anything but the requested value. Never raises.
"""

import os
from pathlib import Path

FACTORY_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ENV_PATH = FACTORY_DIR / ".env"


def _clean(value):
    value = (value or "").strip()
    # Strip a trailing inline comment ("value # comment") before unquoting.
    if " #" in value:
        value = value.split(" #", 1)[0].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        value = value[1:-1].strip()
    return value


def read_env_value(name, env_path=None):
    """Return the non-empty value for `name`, or "" if not configured.

    Order: the process environment first (a non-empty value wins), then
    the `.env` file at `env_path` (default: the factory root `.env`).
    Only an EXACT key match counts -- `NAME=` or `export NAME=` -- so a
    longer key sharing the prefix is never mistaken for it."""
    env_value = _clean(os.environ.get(name, ""))
    if env_value:
        return env_value
    path = Path(env_path) if env_path else DEFAULT_ENV_PATH
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[len("export "):].strip()
                key, sep, value = line.partition("=")
                if not sep or key.strip() != name:
                    continue
                value = _clean(value)
                if value:
                    return value
    except OSError:
        pass
    return ""
