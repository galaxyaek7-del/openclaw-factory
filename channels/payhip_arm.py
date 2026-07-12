"""OpenClaw Factory — Payhip arm (ADR-025).

A thin adapter implementing BaseArm on top of channels/payhip_publisher.py.
dry_run validates product shape only, exactly like GumroadArm — no network
call either way. A live publish attempt (dry_run=False) always fails
safely and honestly: Payhip's public API has no product-creation endpoint
(verified 2026-07-12) — this never pretends otherwise or attempts a call
against an endpoint that doesn't exist.

Self-registers on import: `import channels.payhip_arm` is enough to make
the "payhip" arm available via channels.registry.get("payhip").
"""

from .base_arm import BaseArm, ArmStatus, PublishResult
from . import payhip_publisher
from . import registry

# ADR-5: circuit breaker, same pattern as GumroadArm.
_COOLDOWN_THRESHOLD = 3


class PayhipArm(BaseArm):
    name = "payhip"

    def __init__(self):
        self._consecutive_failures = 0

    def status(self) -> ArmStatus:
        if self._consecutive_failures >= _COOLDOWN_THRESHOLD:
            return ArmStatus.COOLDOWN
        try:
            payhip_publisher.load_token()
        except payhip_publisher.ConfigError:
            return ArmStatus.UNAVAILABLE
        return ArmStatus.READY

    def supports(self, product) -> bool:
        """Same shape requirements as GumroadArm: a real file and a
        resolved price. A Product still needing pricing is not supported."""
        if not product.file_path:
            return False
        if product.price_usd is None or product.needs_pricing:
            return False
        return True

    def publish(self, product, dry_run: bool = True) -> PublishResult:
        current_status = self.status()
        if current_status is not ArmStatus.READY:
            return PublishResult(
                ok=False, platform=self.name, product_id=None, url=None,
                error=f"arm not ready: {current_status.value}", dry_run=dry_run,
            )

        if not self.supports(product):
            return PublishResult(
                ok=False, platform=self.name, product_id=None, url=None,
                error="product not supported (missing file_path or unresolved price)", dry_run=dry_run,
            )

        if dry_run:
            # Validate shape only. No network call, no payhip_publisher
            # function is invoked — this is the safe default.
            return PublishResult(
                ok=True, platform=self.name, product_id=None, url=None, error=None, dry_run=True,
            )

        try:
            token = payhip_publisher.load_token()
            payhip_publisher.create_product(token, {
                "title": product.title,
                "description": product.description,
                "price_usd": product.price_usd,
                "file_path": product.file_path,
            })
        except Exception as e:
            # create_product() always raises UnsupportedOperationError today
            # (ADR-025) — this branch is the expected, honest outcome of
            # every live attempt until Payhip ships a real product API.
            self._consecutive_failures += 1
            return PublishResult(
                ok=False, platform=self.name, product_id=None, url=None, error=str(e), dry_run=False,
            )

        # Unreachable today, kept so this becomes a one-line fix if Payhip
        # ever ships a real product-creation endpoint.
        self._consecutive_failures = 0
        return PublishResult(ok=True, platform=self.name, product_id=None, url=None, error=None, dry_run=False)


registry.register(PayhipArm())
