"""OpenClaw Factory — BaseArm contract (OCTOPUS_ARCHITECTURE.md §3).

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
    """Abstract contract every platform arm must implement."""

    name: str  # e.g. "gumroad"

    @abstractmethod
    def status(self) -> ArmStatus:
        """Check secret/readiness. Missing secret -> UNAVAILABLE, never raise."""
        raise NotImplementedError

    @abstractmethod
    def supports(self, product) -> bool:
        """Whether this arm can handle the given Product (e.g. digital-only)."""
        raise NotImplementedError

    @abstractmethod
    def publish(self, product, dry_run: bool = True) -> PublishResult:
        """Upload the product. dry_run=True by default: validate and report,
        never call the live platform API."""
        raise NotImplementedError
