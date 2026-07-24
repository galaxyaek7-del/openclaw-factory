"""Galaxy Forge — Etsy arm (ADR-025).

A thin adapter implementing BaseArm on top of channels/etsy_publisher.py.
dry_run validates product shape only, exactly like GumroadArm — no
network call either way.

Unlike Payhip, Etsy's real API genuinely supports creating digital
listings — but obtaining a working ETSY_ACCESS_TOKEN requires a full
OAuth2 authorization flow this factory does not implement (a one-time
manual setup step, same category as obtaining GUMROAD_ACCESS_TOKEN
itself), and Etsy is independently documented as restrictive about
approving new developer apps since 2024 (ADR-025) — a real business risk
on top of the technical one.

Self-registers on import: `import channels.etsy_arm` is enough to make
the "etsy" arm available via channels.registry.get("etsy").
"""

from .base_arm import BaseArm, ArmStatus, PublishResult
from . import etsy_publisher
from . import registry


class EtsyArm(BaseArm):
    name = "etsy"

    def status(self) -> ArmStatus:
        return self._status_via(etsy_publisher.load_credentials, etsy_publisher.ConfigError)

    def publish(self, product, dry_run: bool = True) -> PublishResult:
        current_status = self.status()
        if current_status is not ArmStatus.READY:
            return self._not_ready_result(current_status, dry_run)

        if not self.supports(product):
            return self._not_supported_result(dry_run)

        if dry_run:
            return self._dry_run_result()

        try:
            api_key, access_token, shop_id = etsy_publisher.load_credentials()
            result = etsy_publisher.create_product(api_key, access_token, shop_id, {
                "title": product.title,
                "description": product.description,
                "price_usd": product.price_usd,
                "file_path": product.file_path,
            })
        except Exception as e:
            self._record_failure()
            return PublishResult(
                ok=False, platform=self.name, product_id=None, url=None, error=str(e), dry_run=False,
            )

        self._record_success()
        listing_id = result.get("listing_id") if isinstance(result, dict) else None
        url = result.get("url") if isinstance(result, dict) else None
        return PublishResult(
            ok=True, platform=self.name, product_id=listing_id, url=url, error=None, dry_run=False,
        )


registry.register(EtsyArm())
