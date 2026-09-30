"""Galaxy Forge — X (Twitter) arm.

A thin adapter implementing BaseArm on top of the X API v2 tweet creation
endpoint. Self-registers on import: `import channels.x_arm` makes the "x"
arm available via channels.registry.get("x").

Safety:
  - dry_run=True by default (BaseArm contract).
  - Missing/invalid credentials → UNAVAILABLE, never raise.
  - Content validation: X enforces 280-char tweet limit; text is truncated
    and validated before the API call.
  - Rate limiting: publish_protection.py's pre-publish gate enforces
    daily/hourly caps; this arm does not duplicate that logic.
  - Idempotency: the distributor.py + publish_protection layer handles
    dedup via idempotency keys. This arm publishes exactly once per call.
  - Retry: bounded by distributor.py's factory_state.enqueue_retry() for
    transient failures. This arm does not implement its own retry loop.

Never performs real publication during dry_run. Never exposes credentials.
"""

import os
import json
from .base_arm import BaseArm, ArmStatus, PublishResult
from . import registry

_TWEET_MAX_CHARS = 280


class _ConfigError(Exception):
    """Raised when X API credentials are missing or empty."""
    pass


def _load_credentials():
    """Load and validate X API credentials. Raises _ConfigError if any
    required credential is missing or empty."""
    api_key = os.environ.get("X_API_KEY", "").strip()
    api_secret = os.environ.get("X_API_SECRET", "").strip()
    access_token = os.environ.get("X_ACCESS_TOKEN", "").strip()
    access_token_secret = os.environ.get("X_ACCESS_TOKEN_SECRET", "").strip()
    if not all([api_key, api_secret, access_token, access_token_secret]):
        raise _ConfigError(
            "X API credentials not configured "
            "(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET)"
        )
    return api_key, api_secret, access_token, access_token_secret


def _validate_tweet_text(text):
    """Validate and truncate text for X's 280-char limit. Returns
    (clean_text, warnings). Never raises."""
    if not text or not text.strip():
        return "", ["empty_text"]
    clean = text.strip()
    warnings = []
    if len(clean) > _TWEET_MAX_CHARS:
        clean = clean[:_TWEET_MAX_CHARS - 3] + "..."
        warnings.append(f"truncated_to_{_TWEET_MAX_CHARS}")
    return clean, warnings


def _field(product, name, default=None):
    """Read a product field from either a Product object (attribute) or a
    plain dict (JSON-job path). Distributor passes Product objects in every
    tested path, but JSON jobs arrive as dicts -- without this, supports()
    raises AttributeError inside the distributor's try/except instead of
    returning a clean supported/unsupported verdict (found live via dry-run
    probe, GAP-2 cycle). Never raises."""
    if isinstance(product, dict):
        return product.get(name, default)
    return getattr(product, name, default)


class XArm(BaseArm):
    """X (Twitter) distribution arm using OAuth 1.0a + v2 tweet creation."""

    name = "x"

    def status(self) -> ArmStatus:
        return self._status_via(_load_credentials, _ConfigError)

    def supports(self, product) -> bool:
        """X supports any product with text content. File_path is not
        required for tweets (text-only posts). Media upload requires v1.1
        and is not yet implemented."""
        if _field(product, "price_usd") is None or _field(product, "needs_pricing"):
            return False
        return True

    def publish(self, product, dry_run: bool = True) -> PublishResult:
        current_status = self.status()
        if current_status is not ArmStatus.READY:
            return self._not_ready_result(current_status, dry_run)

        if not self.supports(product):
            return self._not_supported_result(dry_run)

        if dry_run:
            return self._dry_run_result()

        # Build tweet text from product fields
        tweet_text = self._build_tweet_text(product)
        clean_text, warnings = _validate_tweet_text(tweet_text)
        if not clean_text:
            self._record_failure()
            return PublishResult(
                ok=False, platform=self.name, product_id=None, url=None,
                error="tweet_text_empty_after_validation", dry_run=False,
            )

        try:
            api_key, api_secret, access_token, access_token_secret = _load_credentials()
        except _ConfigError as e:
            self._record_failure()
            return PublishResult(
                ok=False, platform=self.name, product_id=None, url=None,
                error=str(e), dry_run=False,
            )

        try:
            import oauthlib.oauth1 as oauth1
            import requests as _requests
        except ImportError:
            self._record_failure()
            return PublishResult(
                ok=False, platform=self.name, product_id=None, url=None,
                error="oauthlib not installed (pip install oauthlib)", dry_run=False,
            )

        try:
            client = oauth1.Client(
                api_key,
                client_secret=api_secret,
                resource_owner_key=access_token,
                resource_owner_secret=access_token_secret,
            )

            tweet_url = "https://api.x.com/2/tweets"
            body = {"text": clean_text}

            uri, headers, body_bytes = client.sign(
                tweet_url, "POST",
                body=json.dumps(body),
                headers={"Content-Type": "application/json"},
            )

            resp = _requests.post(uri, headers=headers, data=body_bytes, timeout=30)
            if resp.status_code in (200, 201):
                data = resp.json()
                tweet_id = data.get("data", {}).get("id")
                self._record_success()
                return PublishResult(
                    ok=True,
                    platform=self.name,
                    product_id=tweet_id,
                    url=f"https://x.com/i/status/{tweet_id}" if tweet_id else None,
                    error=None,
                    dry_run=False,
                )
            else:
                self._record_failure()
                return PublishResult(
                    ok=False, platform=self.name, product_id=None, url=None,
                    error=f"HTTP {resp.status_code}: {resp.text[:200]}",
                    dry_run=False,
                )
        except Exception as e:
            self._record_failure()
            return PublishResult(
                ok=False, platform=self.name, product_id=None, url=None,
                error=str(e),
                dry_run=False,
            )

    def _build_tweet_text(self, product):
        """Build tweet text from product fields. Uses title + description,
        truncated to fit X's limit."""
        parts = []
        title = _field(product, "title")
        desc = _field(product, "description")
        if title:
            parts.append(title)
        if desc:
            parts.append(desc)
        return " — ".join(parts) if parts else ""


registry.register(XArm())
