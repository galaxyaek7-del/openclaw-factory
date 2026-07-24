#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Galaxy Forge — Payhip Publisher (ADR-025)
Reads PAYHIP_API_KEY from .env. Never logs the key.

IMPORTANT — verified via a real web search on 2026-07-12 against
help.payhip.com/article/347-public-api and payhip.com/api-reference:
Payhip's public API today covers ONLY coupon and license-key management.
There is NO endpoint to create or upload a digital product
programmatically. create_product() below exists solely to fail loudly and
honestly when called — it is never expected to succeed, and
channels/payhip_arm.py never treats it as if it could.

Standalone module. Does not import or modify any live factory file.
"""

import os
from pathlib import Path

FACTORY_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ENV_PATH = FACTORY_DIR / ".env"


class ConfigError(Exception):
    """A missing/invalid local configuration — never a Payhip API error."""
    pass


class UnsupportedOperationError(Exception):
    """Raised when asked to do something Payhip's real public API cannot do
    today (2026-07-12) — not a network failure, a documented platform limit."""
    pass


def load_token(env_path=None):
    env_path = Path(env_path) if env_path else DEFAULT_ENV_PATH
    token = os.environ.get("PAYHIP_API_KEY")
    if token:
        return token
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("PAYHIP_API_KEY"):
                    value = line.split("=", 1)[1].strip()
                    if value:
                        return value
    raise ConfigError(
        "PAYHIP_API_KEY not set. Get it from https://payhip.com/account/api"
    )


def create_product(token, product_spec):
    """Always raises (ADR-025) — Payhip's public API has no product-creation
    endpoint as of 2026-07-12 (see help.payhip.com/article/347-public-api:
    "We have an API available for managing coupons and license keys").
    Exists so a caller expecting Gumroad-style behavior fails honestly
    instead of silently doing nothing, and so this becomes a one-line fix
    if Payhip ever adds a real product endpoint."""
    raise UnsupportedOperationError(
        "Payhip's public API does not support creating products programmatically "
        "(verified 2026-07-12: only coupon/license-key endpoints exist — see "
        "https://help.payhip.com/article/347-public-api). Upload this product "
        "manually via the Payhip dashboard instead."
    )
