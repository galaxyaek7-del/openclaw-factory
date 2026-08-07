"""Galaxy Forge — BaseArm contract (OCTOPUS_ARCHITECTURE.md §3).

Every distribution arm (Gumroad, Payhip, ...) implements this contract so
the future distributor can call any arm without knowing which platform it
talks to. No arm subclass may change these method signatures.

Standalone module. No imports from the rest of the factory.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ArmStatus(Enum):
    READY = "ready"              # secret present, arm is usable
    UNAVAILABLE = "unavailable"  # secret missing — skip safely, never raise
    COOLDOWN = "cooldown"        # circuit breaker open after repeated failure


@dataclass
class PublishResult:
    ok: bool
    platform: str
    product_id: Optional[str]   # id of the product on the platform, if created
    url: Optional[str]          # sale/listing URL, if known
    error: Optional[str]
    dry_run: bool


class BaseArm(ABC):
    """Abstract contract every platform arm must implement.

    Also carries the boilerplate that was previously copy-pasted near-
    identically across GumroadArm/PayhipArm/EtsyArm — the cooldown+config-
    check skeleton of status(), the shape check in supports(), and the
    not-ready/not-supported/dry-run early returns in publish()
    (STRUCTURAL_DIAGNOSIS.md disease #3, ~35-40 duplicated lines x3). Only
    the genuinely platform-specific part — the live API call and its
    response parsing — stays in each subclass. No behavior change: every
    arm's status()/supports()/publish() still returns exactly what it did
    before, just built from shared helpers instead of copy-pasted ones.
    """

    name: str  # e.g. "gumroad"
    COOLDOWN_THRESHOLD = 3  # ADR-5: consecutive failures before COOLDOWN

    def __init__(self):
        self._consecutive_failures = 0

    def _record_failure(self) -> None:
        self._consecutive_failures += 1

    def _record_success(self) -> None:
        self._consecutive_failures = 0

    def _status_via(self, ready_check, config_error_cls) -> ArmStatus:
        """Shared status() skeleton: cooldown first, then a zero-arg,
        platform-specific readiness call (e.g. gumroad_publisher.load_token)
        that raises config_error_cls when the secret is missing."""
        if self._consecutive_failures >= self.COOLDOWN_THRESHOLD:
            return ArmStatus.COOLDOWN
        try:
            ready_check()
        except config_error_cls:
            return ArmStatus.UNAVAILABLE
        return ArmStatus.READY

    def supports(self, product) -> bool:
        """Shared shape requirement across every arm today: a real file and
        a resolved price. A Product still needing pricing (needs_pricing=True)
        is never supported — no arm may invent a price. A future arm with a
        genuinely different rule can still override this."""
        if not product.file_path:
            return False
        if product.price_usd is None or product.needs_pricing:
            return False
        return True

    def _not_ready_result(self, current_status: ArmStatus, dry_run: bool) -> PublishResult:
        return PublishResult(
            ok=False, platform=self.name, product_id=None, url=None,
            error=f"arm not ready: {current_status.value}", dry_run=dry_run,
        )

    def _not_supported_result(self, dry_run: bool) -> PublishResult:
        return PublishResult(
            ok=False, platform=self.name, product_id=None, url=None,
            error="product not supported (missing file_path or unresolved price)", dry_run=dry_run,
        )

    def _dry_run_result(self) -> PublishResult:
        # Validate shape only. No network call, no publisher function is
        # invoked — this is the safe default every arm shares.
        return PublishResult(ok=True, platform=self.name, product_id=None, url=None, error=None, dry_run=True)

    @abstractmethod
    def status(self) -> ArmStatus:
        """Check secret/readiness. Missing secret -> UNAVAILABLE, never raise."""
        raise NotImplementedError

    @abstractmethod
    def publish(self, product, dry_run: bool = True) -> PublishResult:
        """Upload the product. dry_run=True by default: validate and report,
        never call the live platform API."""
        raise NotImplementedError

    # ── Global Commercial Revenue Operating System (ADR-202, 2026-08-07) ──
    # Section 2's "common Marketplace Adapter architecture" named 14
    # conceptual methods. 4 already exist under different, established
    # names and are NOT duplicated here: authenticate/validate_connection
    # both map to the real status() above (a credential-presence/format
    # check, never a live network call -- this factory's own established
    # discipline for every arm since ADR-4); create_product/publish_product
    # both map to publish() (dry_run=False); retrieve_sales/
    # retrieve_transactions map to whichever ad-hoc get_sales() an arm
    # already defines (Paddle/Gumroad have one; Etsy/Payhip honestly
    # don't). retrieve_checkout_url is PaddleArm.publish()'s own real
    # PublishResult.url field, produced at publish time -- not a separate
    # retrievable-after-the-fact call, since no arm's publisher module
    # exposes one.
    #
    # The remaining 6 (list_products, update_product, verify_product,
    # retrieve_fees, retrieve_refunds, retrieve_affiliate_data) plus
    # health_check are genuinely new here -- added as safe, non-abstract,
    # default-NOT_IMPLEMENTED methods so adding them can never break any
    # of the 4 existing concrete arms (Gumroad/Etsy/Payhip/Paddle), which
    # override none of them unless a real underlying publisher function
    # already exists (paddle_publisher.py/gumroad_publisher.py both real
    # already have list_products()/update_product(); neither
    # etsy_publisher.py nor payhip_publisher.py does -- confirmed by
    # direct grep, not assumed). "Never invent endpoints" (directive's
    # own words): retrieve_fees/retrieve_refunds/retrieve_affiliate_data
    # stay NOT_IMPLEMENTED on every arm today -- no publisher module in
    # this factory has ever called a real fees/refunds/affiliate endpoint
    # on any platform, so none is fabricated here either.

    def list_products(self):
        """Real product list from the platform, when the arm's publisher
        module actually supports it. Default: honest gap, not a guess."""
        return {"status": "NOT_IMPLEMENTED", "platform": self.name, "reason": "no real list-products call wired for this arm"}

    def update_product(self, product_id, updates):
        """Real product update, when supported. Default: honest gap."""
        return {"status": "NOT_IMPLEMENTED", "platform": self.name, "reason": "no real update-product call wired for this arm"}

    def verify_product(self, product_id):
        """Confirms a previously-published product_id still exists on the
        platform by re-listing and matching -- never assumes success from
        the original publish() call alone. Built generically here (not
        per-arm) since the logic is identical wherever list_products() is
        real: any arm that implements list_products() gets this for free."""
        listing = self.list_products()
        if isinstance(listing, dict) and listing.get("status") == "NOT_IMPLEMENTED":
            return {"status": "NOT_IMPLEMENTED", "platform": self.name, "reason": "verification requires a real list_products() call, not wired for this arm"}
        products = listing if isinstance(listing, list) else listing.get("products", [])
        found = any(str(p.get("id")) == str(product_id) for p in products if isinstance(p, dict))
        return {"status": "VERIFIED" if found else "NOT_FOUND", "platform": self.name, "product_id": product_id}

    def retrieve_fees(self):
        """Real per-transaction platform fees, when the platform's own
        already-fetched transaction/sale payload actually carries a fee
        field. Default: honest gap -- no publisher module in this
        factory has ever parsed a fee field from any platform response."""
        return {"status": "NOT_IMPLEMENTED", "platform": self.name, "reason": "no real fee field parsed from this arm's transaction/sale data"}

    def retrieve_refunds(self):
        """Default: honest gap. No arm's publisher module calls a real
        refunds/adjustments endpoint anywhere in this factory today --
        confirmed by direct grep before this method was added, not
        assumed. Never call an unverified endpoint to fill this in."""
        return {"status": "NOT_IMPLEMENTED", "platform": self.name, "reason": "no real refunds endpoint is called by this arm's publisher module"}

    def retrieve_affiliate_data(self):
        """Default: honest gap. Distinct from affiliate_commerce/ (a
        separate, real Amazon Associates system, not part of any
        BaseArm) -- no distribution arm here has its own affiliate API."""
        return {"status": "NOT_IMPLEMENTED", "platform": self.name, "reason": "no real affiliate-program API is wired for this arm"}

    def health_check(self):
        """A real, safe, generic implementation: reuses status() exactly
        (never a second live network call) and adds a timestamp so a
        caller can distinguish a fresh check from a cached one."""
        from datetime import datetime, timezone
        current_status = self.status()
        return {
            "platform": self.name,
            "status": current_status.value,
            "healthy": current_status == ArmStatus.READY,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
