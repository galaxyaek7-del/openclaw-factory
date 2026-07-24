"""Galaxy Forge — Payhip arm (ADR-025).

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


class PayhipArm(BaseArm):
    name = "payhip"

    def status(self) -> ArmStatus:
        return self._status_via(payhip_publisher.load_token, payhip_publisher.ConfigError)

    def publish(self, product, dry_run: bool = True) -> PublishResult:
        current_status = self.status()
        if current_status is not ArmStatus.READY:
            return self._not_ready_result(current_status, dry_run)

        if not self.supports(product):
            return self._not_supported_result(dry_run)

        if dry_run:
            return self._dry_run_result()

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
            self._record_failure()
            return PublishResult(
                ok=False, platform=self.name, product_id=None, url=None, error=str(e), dry_run=False,
            )

        # Unreachable today, kept so this becomes a one-line fix if Payhip
        # ever ships a real product-creation endpoint.
        self._record_success()
        return PublishResult(ok=True, platform=self.name, product_id=None, url=None, error=None, dry_run=False)


registry.register(PayhipArm())
