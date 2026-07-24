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
