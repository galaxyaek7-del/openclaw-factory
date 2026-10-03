"""Galaxy Forge — Systeme.io Affiliate Path.

Reads SYSTEME_AFFILIATE_ID from .env, validates format, and constructs
the traceable affiliate URL. Fails closed when the ID is missing, empty,
or a placeholder.

Security:
  - Never prints, logs, or exposes the Affiliate ID.
  - Never writes the ID to reports, exceptions, or source code.
  - Never silently substitutes a fake/default ID.
  - .env is never modified by this module.

Usage:
    from systeme_affiliate import get_affiliate_url, ConfigError

    try:
        url = get_affiliate_url()       # returns "https://systeme.io/?sa=..."
        # url is safe to use — the ID is inside it but never printed separately
    except ConfigError as e:
        print(f"Configuration error: {e}")
"""

import os
from pathlib import Path

FACTORY_DIR = Path(__file__).resolve().parent
DEFAULT_ENV_PATH = FACTORY_DIR / ".env"
AFFILIATE_ID_VAR = "SYSTEME_AFFILIATE_ID"
BASE_URL = "https://systeme.io/"
QUERY_PARAM = "sa"


class ConfigError(Exception):
    """Missing or invalid local configuration — never an external API error."""
    pass


def _read_env_var(name, env_path):
    """Read a variable from os.environ first, then from the .env file.

    Returns None if not found or empty. Never raises."""
    value = os.environ.get(name)
    if value:
        return value.strip()
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith(name + "="):
                    v = line.split("=", 1)[1].strip()
                    if v:
                        return v
    return None


def _is_placeholder(value):
    """Detect common placeholder patterns that indicate the ID was never set."""
    if not value:
        return True
    upper = value.upper()
    placeholders = {"YOUR_SA_ID", "YOUR_SA_ID_HERE", "PLACEHOLDER", "TODO", "TBD", "FILLME", "XXX"}
    if upper in placeholders:
        return True
    if upper.startswith("YOUR_"):
        return True
    if "{{" in value or "<" in value:
        return True
    return False


def load_affiliate_id(env_path=None):
    """Return the raw SYSTEME_AFFILIATE_ID from .env.

    Raises ConfigError if missing, empty, placeholder, or invalid format.

    NEVER prints, logs, or exposes the value."""
    env_path = Path(env_path) if env_path else DEFAULT_ENV_PATH
    raw = _read_env_var(AFFILIATE_ID_VAR, env_path)

    if raw is None:
        raise ConfigError(
            f"{AFFILIATE_ID_VAR} is not set in .env. "
            "Add your Systeme.io affiliate ID (starts with 'sa') to .env."
        )

    if _is_placeholder(raw):
        raise ConfigError(
            f"{AFFILIATE_ID_VAR} appears to be a placeholder. "
            "Replace it with your real Systeme.io affiliate ID from "
            "https://systeme.io/dashboard/affiliate-dashboard"
        )

    if not raw.startswith("sa"):
        raise ConfigError(
            f"{AFFILIATE_ID_VAR} must start with 'sa'. "
            "Found a value that does not match the expected format."
        )

    return raw


def get_affiliate_url(env_path=None):
    """Construct the Systeme.io affiliate URL.

    Returns the full URL string (e.g. "https://systeme.io/?sa=saXXXXXX").

    NEVER prints, logs, or exposes the ID separately from the URL.
    NEVER writes the URL to any file.

    Raises ConfigError if the ID cannot be loaded."""
    affiliate_id = load_affiliate_id(env_path)
    return f"{BASE_URL}?{QUERY_PARAM}={affiliate_id}"


def validate_config(env_path=None):
    """Validate the affiliate configuration without exposing the ID.

    Returns a dict with validation results. Safe for logging/reporting."""
    env_path = Path(env_path) if env_path else DEFAULT_ENV_PATH
    result = {
        "affiliate_id_present": False,
        "affiliate_id_format_valid": False,
        "affiliate_id_is_placeholder": True,
        "config_error": None,
    }

    try:
        raw = _read_env_var(AFFILIATE_ID_VAR, env_path)
    except Exception as e:
        result["config_error"] = "READ_ERROR"
        return result

    if raw is None:
        result["config_error"] = "MISSING"
        return result

    result["affiliate_id_present"] = True
    result["affiliate_id_is_placeholder"] = _is_placeholder(raw)

    if not result["affiliate_id_is_placeholder"] and raw.startswith("sa"):
        result["affiliate_id_format_valid"] = True
    else:
        result["config_error"] = "INVALID_FORMAT"

    return result
