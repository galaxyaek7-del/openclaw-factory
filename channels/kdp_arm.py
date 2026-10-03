"""KDP (Kindle Direct Publishing) arm — Universal Distribution Fabric adapter.

KDP has NO public publishing API. This adapter is an honest, credential-gated
manual-upload adapter. The adapter validates products against KDP requirements,
maps metadata, detects duplicates, classifies errors, and provides a dry-run
path — but real publication ALWAYS requires human upload to kdp.amazon.com.

Credential model:
  KDP uses cookie-based session authentication (not API keys).
  No credentials are stored in code. All credential checks require:
    1. KDP_USERNAME env var (Amazon account email)
    2. KDP_SESSION_COOKIE env var (session cookie from browser)
  Both must be set for status() to return READY.

Status model:
  UNAVAILABLE — credentials not configured (safe default)
  READY       — credentials present, adapter operational
  COOLDOWN    — too many consecutive failures

Publication model:
  dry_run=True  — validation + metadata mapping only (no external call)
  dry_run=False — BLOCKED: requires human upload, never executes automatically

Architecture:
  Follows BaseArm contract exactly (same pattern as gumroad_arm, paddle_arm).
  Self-registers as "kdp" in channels.registry on import.
"""

import os
import time
from channels.base_arm import BaseArm, ArmStatus, PublishResult
from channels.registry import register
from channels.adapter_contract import ErrorClass
from channels.error_classification import classify_error, error_summary
from channels.duplicate_protection import DuplicateProtection

# KDP does not have a public API. Real publishing requires human upload.
KDP_HAS_API = False

# KDP-supported ebook file formats
KDP_EBOOK_FORMATS = {
    ".epub", ".doc", ".docx", ".pdf", ".html", ".htm", ".rtf", ".txt", ".mobi"
}

# KDP paperback trim sizes (width_in, height_in) — common US sizes
KDP_PAPERBACK_TRIM_SIZES = {
    (5.0, 8.0), (5.06, 7.81), (5.25, 8.0), (5.5, 8.5),
    (6.0, 9.0), (6.14, 9.21), (6.69, 9.61), (7.0, 10.0),
    (7.44, 9.69), (7.5, 9.25), (8.0, 10.0), (8.0, 10.88),
    (8.25, 6.0), (8.25, 8.25), (8.5, 8.5), (8.5, 11.0),
}

# KDP pricing bounds
KDP_EBOOK_MIN_PRICE = 0.99
KDP_EBOOK_MAX_PRICE = 200.00
KDP_PAPERBACK_MIN_PRICE = 2.99
KDP_PAPERBACK_MAX_PRICE = 250.00


class KdpArm(BaseArm):
    """Kindle Direct Publishing adapter — manual upload only, no API."""

    name = "kdp"

    # --- credential loading (safe, never fabricates) ---

    @staticmethod
    def _load_credentials():
        """Load KDP credentials from environment. Returns (username, cookie) or raises."""
        username = os.environ.get("KDP_USERNAME", "").strip()
        cookie = os.environ.get("KDP_SESSION_COOKIE", "").strip()
        if not username:
            raise ConfigError("KDP_USERNAME not set in environment")
        if not cookie:
            raise ConfigError("KDP_SESSION_COOKIE not set in environment")
        return username, cookie

    # --- BaseArm contract implementation ---

    def status(self) -> ArmStatus:
        """READY if credentials present, UNAVAILABLE if not, COOLDOWN if failing."""
        return self._status_via(self._load_credentials, ConfigError)

    def supports(self, product) -> bool:
        """KDP supports: file_path required, price_usd required, no pending pricing."""
        if not super().supports(product):
            return False
        # Check file extension is KDP-compatible
        file_path = getattr(product, "file_path", None) or ""
        if file_path:
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in KDP_EBOOK_FORMATS:
                return False
        return True

    def publish(self, product, dry_run: bool = True) -> PublishResult:
        """
        KDP publish workflow:
        1. Check status — must be READY
        2. Check supports — product must be KDP-compatible
        3. If dry_run — validate + return metadata mapping (no external call)
        4. If not dry_run — BLOCKED: KDP requires human upload, never auto-execute

        KDP has no public API. Real publication requires logging into
        kdp.amazon.com and uploading the manuscript + cover manually.
        This adapter validates readiness and provides the metadata mapping
        a human needs to complete the upload.
        """
        current_status = self.status()
        if current_status != ArmStatus.READY:
            return self._not_ready_result(current_status, dry_run)

        if not self.supports(product):
            return self._not_supported_result(dry_run)

        if dry_run:
            return self._dry_run_result()

        # --- REAL PUBLISHING BLOCKED ---
        # KDP has no public API. This arm NEVER auto-publishes.
        # Real publication requires human upload to kdp.amazon.com.
        self._record_failure()
        return PublishResult(
            False,           # ok
            "kdp",           # platform
            None,            # product_id
            None,            # url
            (
                "KDP requires manual upload — no public API available. "
                "Log into kdp.amazon.com and upload the manuscript + cover manually. "
                "See reports/KDP_ADAPTER_IMPLEMENTATION_2026-09-09.md for details."
            ),               # error
            False,           # dry_run
        )

    # --- KDP-specific validation methods ---

    def validate_kdp_requirements(self, product) -> dict:
        """
        Validate product against KDP-specific requirements.
        Returns: {"valid": bool, "issues": list, "warnings": list}
        """
        issues = []
        warnings = []

        file_path = getattr(product, "file_path", None) or ""
        if not file_path:
            issues.append("No file_path set — cannot validate KDP format")

        ext = os.path.splitext(file_path)[1].lower() if file_path else ""
        if ext not in KDP_EBOOK_FORMATS:
            issues.append(
                f"File format '{ext}' not supported by KDP. "
                f"Supported: {', '.join(sorted(KDP_EBOOK_FORMATS))}"
            )

        price = getattr(product, "price_usd", None)
        if price is not None:
            if price < KDP_EBOOK_MIN_PRICE:
                issues.append(
                    f"Price ${price:.2f} below KDP minimum ${KDP_EBOOK_MIN_PRICE:.2f}"
                )
            elif price > KDP_EBOOK_MAX_PRICE:
                issues.append(
                    f"Price ${price:.2f} above KDP maximum ${KDP_EBOOK_MAX_PRICE:.2f}"
                )

        title = getattr(product, "title", "") or ""
        if len(title) > 200:
            warnings.append(
                f"Title length ({len(title)} chars) may exceed KDP limit (200 chars). "
                "KDP may truncate or reject."
            )

        description = getattr(product, "description", "") or ""
        if len(description) > 4000:
            warnings.append(
                f"Description length ({len(description)} chars) may exceed KDP limit. "
                "KDP description field has a 4000 character limit."
            )

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
        }

    def map_product_metadata(self, product) -> dict:
        """
        Map factory product to KDP metadata structure.
        Returns KDP-ready metadata dict for manual upload guidance.
        """
        price = getattr(product, "price_usd", None)
        return {
            "title": getattr(product, "title", "Untitled"),
            "description": getattr(product, "description", ""),
            "price_usd": price,
            "file_path": getattr(product, "file_path", None),
            "kdp_format": "ebook",
            "kdp_category": getattr(product, "category", "Nonfiction"),
            "kdp_keywords": getattr(product, "keywords", []),
            "kdp_language": "English",
            "kdp_isbn": getattr(product, "isbn", None),
            "pricing_note": (
                f"Set KDP list price to ${price:.2f} USD. "
                "Verify 70% royalty tier is available at this price point."
                if price else "Price must be set before KDP upload."
            ),
        }

    # ── PlatformAdapter contract — explicit REQUIRES_HUMAN_ACTION / UNSUPPORTED ──
    # KDP has no public API. Every operation requiring an API call honestly
    # reports its limitation rather than emulating success.

    display_name = "Amazon KDP"
    payout_route = "PAYONEER_HUB"
    payout_destination = "BADR EUR"
    payout_currency = "EUR"

    def health_check(self) -> dict:
        s = self.status()
        return {
            "platform": self.name,
            "status": s.value,
            "healthy": s == ArmStatus.READY,
            "checked_at": time.time(),
            "has_api": KDP_HAS_API,
            "note": "KDP has no public API — health reflects credential presence, not API reachability",
        }

    def authentication_check(self) -> dict:
        s = self.status()
        if s == ArmStatus.READY:
            return {"authenticated": True, "platform": self.name, "status": s.value}
        return {
            "authenticated": False,
            "platform": self.name,
            "status": s.value,
            "reason": "REQUIRES_HUMAN_ACTION — KDP uses browser session auth, not API key. Set KDP_USERNAME + KDP_SESSION_COOKIE",
        }

    def account_check(self) -> dict:
        s = self.status()
        if s == ArmStatus.READY:
            return {"account_ready": True, "platform": self.name, "status": s.value, "note": "credentials present; account verification requires browser login to kdp.amazon.com"}
        return {
            "account_ready": False,
            "platform": self.name,
            "status": s.value,
            "reason": "BLOCKED — credentials not configured",
        }

    def capability_check(self) -> dict:
        return {
            "platform": self.name,
            "has_api": KDP_HAS_API,
            "capabilities": [
                {"operation": "product_validate", "status": "SUPPORTED"},
                {"operation": "metadata_map", "status": "SUPPORTED"},
                {"operation": "asset_validate", "status": "SUPPORTED"},
                {"operation": "pricing_validate", "status": "SUPPORTED"},
                {"operation": "draft_create", "status": "REQUIRES_HUMAN_ACTION", "reason": "no public API"},
                {"operation": "draft_update", "status": "REQUIRES_HUMAN_ACTION", "reason": "no public API"},
                {"operation": "publish", "status": "REQUIRES_HUMAN_ACTION", "reason": "no public API — manual upload to kdp.amazon.com"},
                {"operation": "retrieve", "status": "REQUIRES_HUMAN_ACTION", "reason": "no public API"},
                {"operation": "verify", "status": "REQUIRES_HUMAN_ACTION", "reason": "no public API"},
                {"operation": "list_products", "status": "UNSUPPORTED", "reason": "no public API"},
                {"operation": "update_product", "status": "UNSUPPORTED", "reason": "no public API"},
            ],
        }

    def product_validate(self, product) -> dict:
        result = self.validate_kdp_requirements(product)
        return {"valid": result["valid"], "platform": self.name, "issues": result["issues"], "warnings": result["warnings"]}

    def metadata_map(self, product) -> dict:
        return {"mapped": True, "platform": self.name, "metadata": self.map_product_metadata(product)}

    def asset_validate(self, product) -> dict:
        file_path = getattr(product, "file_path", None) or ""
        issues = []
        if not file_path:
            issues.append("No file_path — no asset to validate")
        else:
            import os as _os
            ext = _os.path.splitext(file_path)[1].lower()
            if ext not in KDP_EBOOK_FORMATS:
                issues.append(f"File format '{ext}' not in KDP supported: {sorted(KDP_EBOOK_FORMATS)}")
            if not _os.path.exists(file_path):
                issues.append(f"File does not exist on disk: {file_path}")
        return {"valid": len(issues) == 0, "platform": self.name, "issues": issues}

    def pricing_validate(self, product) -> dict:
        price = getattr(product, "price_usd", None)
        issues = []
        if price is None:
            issues.append("No price set — cannot validate KDP pricing")
        elif price < KDP_EBOOK_MIN_PRICE:
            issues.append(f"Price ${price:.2f} below KDP minimum ${KDP_EBOOK_MIN_PRICE:.2f}")
        elif price > KDP_EBOOK_MAX_PRICE:
            issues.append(f"Price ${price:.2f} above KDP maximum ${KDP_EBOOK_MAX_PRICE:.2f}")
        return {"valid": len(issues) == 0, "platform": self.name, "issues": issues}

    def draft_create(self, product) -> dict:
        return {"status": "REQUIRES_HUMAN_ACTION", "platform": self.name, "reason": "KDP has no public API — create draft manually at kdp.amazon.com"}

    def draft_update(self, product_id, updates) -> dict:
        return {"status": "REQUIRES_HUMAN_ACTION", "platform": self.name, "reason": "KDP has no public API — update manually at kdp.amazon.com"}

    def retrieve(self, product_id) -> dict:
        return {"status": "REQUIRES_HUMAN_ACTION", "platform": self.name, "reason": "KDP has no public API — verify manually at kdp.amazon.com"}

    def verify(self, product_id) -> dict:
        return {"status": "REQUIRES_HUMAN_ACTION", "platform": self.name, "reason": "KDP has no public API — verify manually at kdp.amazon.com"}

    def error_classify(self, error) -> ErrorClass:
        return classify_error(error)

    def retry(self, operation, max_attempts=3) -> dict:
        return {"status": "UNSUPPORTED", "platform": self.name, "reason": "KDP has no public API — no retry against an API that does not exist"}

    def rollback_or_recovery(self, product_id, operation) -> dict:
        return {"status": "REQUIRES_HUMAN_ACTION", "platform": self.name, "reason": "KDP has no public API — rollback requires manual action at kdp.amazon.com"}

    def audit(self) -> dict:
        return {"platform": self.name, "payout_route": self.payout_route, "payout_destination": self.payout_destination, "status": self.status().value, "has_api": KDP_HAS_API}


class ConfigError(Exception):
    """Raised when KDP credentials are not configured."""
    pass


# --- self-registration (same pattern as gumroad_arm, paddle_arm) ---
register(KdpArm())
