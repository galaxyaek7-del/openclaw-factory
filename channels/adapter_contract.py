"""Universal Distribution Fabric — Platform Adapter Contract

Defines the standardized interface every platform adapter must implement.
Adapters transform canonical products into platform-specific formats.

Architecture principle: ONE factory, ONE product system, MANY platform adapters.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import time


class ArmStatus(Enum):
    READY = "READY"
    UNAVAILABLE = "UNAVAILABLE"
    COOLDOWN = "COOLDOWN"
    BLOCKED = "BLOCKED"


class ExecutionMode(Enum):
    DRY_RUN = "DRY_RUN"
    SIMULATED = "SIMULATED"
    AUTHORIZED = "AUTHORIZED"


class ErrorClass(Enum):
    AUTH_ERROR = "AUTH_ERROR"
    ACCOUNT_ERROR = "ACCOUNT_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PLATFORM_ERROR = "PLATFORM_ERROR"
    RATE_LIMIT = "RATE_LIMIT"
    TIMEOUT = "TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"
    DUPLICATE = "DUPLICATE"
    POLICY_BLOCK = "POLICY_BLOCK"
    PAYMENT_BLOCK = "PAYMENT_BLOCK"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class LifecycleState(Enum):
    DISCOVERED = "DISCOVERED"
    SELECTED = "SELECTED"
    PRODUCED = "PRODUCED"
    QA_PENDING = "QA_PENDING"
    QA_PASSED = "QA_PASSED"
    ECONOMICS_PENDING = "ECONOMICS_PENDING"
    ECONOMICS_PASSED = "ECONOMICS_PASSED"
    PLATFORM_READY = "PLATFORM_READY"
    AUTHORIZATION_REQUIRED = "AUTHORIZATION_REQUIRED"
    AUTHORIZED = "AUTHORIZED"
    PUBLISHING = "PUBLISHING"
    PUBLISHED = "PUBLISHED"
    VERIFICATION_PENDING = "VERIFICATION_PENDING"
    VERIFIED = "VERIFIED"
    # Commercial execution — post-verification (Real Commercial Factory, §9 +
    # Commercial Activation & Real Transaction Gate stage — extends to close
    # PRODUCE→RECONCILED loop with activation/purchasability granularity).
    ORDER_RECEIVED = "ORDER_RECEIVED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAYMENT_CONFIRMED = "PAYMENT_CONFIRMED"
    PAYOUT_PENDING = "PAYOUT_PENDING"
    PAYOUT_RECEIVED = "PAYOUT_RECEIVED"
    BANK_SETTLED = "BANK_SETTLED"
    # Commercial-activation layer (§7): platform activation → purchasability
    ACTIVATION_PENDING = "ACTIVATION_PENDING"
    ACTIVE = "ACTIVE"
    PURCHASABLE = "PURCHASABLE"
    TRANSACTION_VERIFIED = "TRANSACTION_VERIFIED"
    RECONCILED = "RECONCILED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    UNKNOWN = "UNKNOWN"


VALID_TRANSITIONS = {
    LifecycleState.DISCOVERED: [LifecycleState.SELECTED, LifecycleState.BLOCKED],
    LifecycleState.SELECTED: [LifecycleState.PRODUCED, LifecycleState.BLOCKED],
    LifecycleState.PRODUCED: [LifecycleState.QA_PENDING],
    LifecycleState.QA_PENDING: [LifecycleState.QA_PASSED, LifecycleState.FAILED],
    LifecycleState.QA_PASSED: [LifecycleState.ECONOMICS_PENDING],
    LifecycleState.ECONOMICS_PENDING: [LifecycleState.ECONOMICS_PASSED, LifecycleState.FAILED],
    LifecycleState.ECONOMICS_PASSED: [LifecycleState.PLATFORM_READY],
    LifecycleState.PLATFORM_READY: [LifecycleState.AUTHORIZATION_REQUIRED],
    LifecycleState.AUTHORIZATION_REQUIRED: [LifecycleState.AUTHORIZED, LifecycleState.BLOCKED],
    LifecycleState.AUTHORIZED: [LifecycleState.PUBLISHING, LifecycleState.ACTIVATION_PENDING],
    LifecycleState.PUBLISHING: [LifecycleState.PUBLISHED, LifecycleState.FAILED],
    LifecycleState.PUBLISHED: [LifecycleState.VERIFICATION_PENDING, LifecycleState.ROLLED_BACK],
    LifecycleState.VERIFICATION_PENDING: [LifecycleState.VERIFIED, LifecycleState.FAILED],
    # Commercial-activation (§7) + extended commercial (§9): two paths converge at ORDER_RECEIVED
    LifecycleState.VERIFIED: [LifecycleState.ORDER_RECEIVED, LifecycleState.ACTIVATION_PENDING, LifecycleState.PURCHASABLE, LifecycleState.BLOCKED],
    LifecycleState.ACTIVATION_PENDING: [LifecycleState.ACTIVE, LifecycleState.FAILED, LifecycleState.BLOCKED],
    LifecycleState.ACTIVE: [LifecycleState.PURCHASABLE, LifecycleState.FAILED, LifecycleState.BLOCKED],
    LifecycleState.PURCHASABLE: [LifecycleState.ORDER_RECEIVED, LifecycleState.FAILED, LifecycleState.BLOCKED],
    LifecycleState.ORDER_RECEIVED: [LifecycleState.PAYMENT_PENDING, LifecycleState.PAYMENT_CONFIRMED, LifecycleState.FAILED],
    LifecycleState.PAYMENT_PENDING: [LifecycleState.PAYMENT_CONFIRMED, LifecycleState.FAILED],
    LifecycleState.PAYMENT_CONFIRMED: [LifecycleState.TRANSACTION_VERIFIED, LifecycleState.PAYOUT_PENDING, LifecycleState.FAILED],
    LifecycleState.TRANSACTION_VERIFIED: [LifecycleState.RECONCILED, LifecycleState.FAILED],
    LifecycleState.RECONCILED: [],
    LifecycleState.PAYOUT_PENDING: [LifecycleState.PAYOUT_RECEIVED, LifecycleState.FAILED],
    LifecycleState.PAYOUT_RECEIVED: [LifecycleState.BANK_SETTLED, LifecycleState.FAILED],
    LifecycleState.BANK_SETTLED: [],
    LifecycleState.RECOVERY_REQUIRED: [LifecycleState.PUBLISHING, LifecycleState.ACTIVATION_PENDING, LifecycleState.FAILED],
    LifecycleState.BLOCKED: [LifecycleState.DISCOVERED],
    LifecycleState.FAILED: [LifecycleState.DISCOVERED, LifecycleState.ROLLED_BACK, LifecycleState.RECOVERY_REQUIRED],
    LifecycleState.ROLLED_BACK: [],
    LifecycleState.UNKNOWN: [LifecycleState.DISCOVERED],
}


def validate_transition(from_state: LifecycleState, to_state: LifecycleState) -> bool:
    return to_state in VALID_TRANSITIONS.get(from_state, [])


@dataclass
class PublishResult:
    ok: bool
    platform: str
    product_id: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None
    error_class: Optional[ErrorClass] = None
    dry_run: bool = True
    execution_mode: str = "DRY_RUN"
    timestamp: float = field(default_factory=time.time)
    evidence: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CanonicalProduct:
    product_id: str
    product_name: str
    product_type: str
    target_customer: str
    niche: str
    description: str
    benefits: List[str] = field(default_factory=list)
    files: List[Dict[str, Any]] = field(default_factory=list)
    file_formats: List[str] = field(default_factory=list)
    preview_assets: List[str] = field(default_factory=list)
    thumbnail: Optional[str] = None
    price: float = 0.0
    currency: str = "USD"
    licensing: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    keywords: List[str] = field(default_factory=list)
    category: Optional[str] = None
    author: Optional[str] = None
    brand: Optional[str] = None
    support_info: Optional[str] = None
    qa_status: Optional[str] = None
    economics_status: Optional[str] = None
    governance_status: Optional[str] = None
    evidence_status: Optional[str] = None
    lifecycle_state: LifecycleState = LifecycleState.DISCOVERED
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_arm_spec(self, platform: str) -> Dict[str, Any]:
        return {
            "title": self.product_name,
            "description": self.description,
            "price_cents": int(self.price * 100),
            "file_path": self.files[0]["path"] if self.files else None,
            "tags": self.keywords,
            "category": self.category,
            "platform": platform,
        }


class PlatformAdapter(ABC):
    name: str = "unknown"
    display_name: str = "Unknown"
    payout_route: str = "UNKNOWN"
    payout_destination: str = "UNKNOWN"
    payout_currency: str = "UNKNOWN"

    @abstractmethod
    def status(self) -> ArmStatus:
        pass

    @abstractmethod
    def publish(self, product, dry_run: bool = True) -> PublishResult:
        pass

    def health_check(self) -> Dict[str, Any]:
        try:
            s = self.status()
            return {"platform": self.name, "status": s.value, "healthy": s == ArmStatus.READY, "timestamp": time.time()}
        except Exception as e:
            return {"platform": self.name, "status": "ERROR", "healthy": False, "error": str(e), "timestamp": time.time()}

    def authentication_check(self) -> Dict[str, Any]:
        return {"authenticated": False, "reason": "not_implemented", "platform": self.name}

    def account_check(self) -> Dict[str, Any]:
        return {"account_ready": False, "reason": "not_implemented", "platform": self.name}

    def capability_check(self) -> Dict[str, Any]:
        return {"capabilities": [], "platform": self.name}

    def product_validate(self, product) -> Dict[str, Any]:
        return {"valid": True, "platform": self.name, "issues": []}

    def metadata_map(self, product) -> Dict[str, Any]:
        return {"mapped": True, "platform": self.name}

    def asset_validate(self, product) -> Dict[str, Any]:
        return {"valid": True, "platform": self.name, "issues": []}

    def pricing_validate(self, product) -> Dict[str, Any]:
        return {"valid": True, "platform": self.name, "issues": []}

    def draft_create(self, product) -> Dict[str, Any]:
        return {"status": "NOT_SUPPORTED", "platform": self.name}

    def draft_update(self, product_id, updates) -> Dict[str, Any]:
        return {"status": "NOT_SUPPORTED", "platform": self.name}

    def retrieve(self, product_id) -> Dict[str, Any]:
        return {"status": "NOT_SUPPORTED", "platform": self.name}

    def verify(self, product_id) -> Dict[str, Any]:
        return {"status": "NOT_SUPPORTED", "platform": self.name}

    def error_classify(self, error) -> ErrorClass:
        return ErrorClass.UNKNOWN_ERROR

    def retry(self, operation, max_attempts=3) -> Dict[str, Any]:
        return {"status": "NOT_SUPPORTED", "platform": self.name}

    def rollback_or_recovery(self, product_id, operation) -> Dict[str, Any]:
        return {"status": "NOT_SUPPORTED", "platform": self.name}

    def audit(self) -> Dict[str, Any]:
        return {"platform": self.name, "payout_route": self.payout_route, "status": self.status().value}
