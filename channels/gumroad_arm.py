"""OpenClaw Factory — Gumroad arm (OCTOPUS_ARCHITECTURE.md ADR-2).

A thin adapter that implements BaseArm on top of the existing
gumroad_publisher.py. gumroad_publisher.py is not modified — every real
Gumroad API call still goes through create_product()/load_token() exactly
as written and audited.

Self-registers on import: `import channels.gumroad_arm` is enough to make
the "gumroad" arm available via channels.registry.get("gumroad").
"""

from .base_arm import BaseArm, ArmStatus, PublishResult
from . import gumroad_publisher
from . import registry


class GumroadArm(BaseArm):
    name = "gumroad"

    def status(self) -> ArmStatus:
        return self._status_via(gumroad_publisher.load_token, gumroad_publisher.ConfigError)

    def publish(self, product, dry_run: bool = True) -> PublishResult:
        current_status = self.status()
        if current_status is not ArmStatus.READY:
            return self._not_ready_result(current_status, dry_run)

        if not self.supports(product):
            return self._not_supported_result(dry_run)

        if dry_run:
            return self._dry_run_result()

        spec = {
            "title": product.title,
            "description": product.description,
            "price_cents": round(product.price_usd * 100),
            "file_path": product.file_path,
        }

        try:
            token = gumroad_publisher.load_token()
            result = gumroad_publisher.create_product(token, spec)
        except Exception as e:
            self._record_failure()
            return PublishResult(
                ok=False,
                platform=self.name,
                product_id=None,
                url=None,
                error=str(e),
                dry_run=False,
            )

        self._record_success()
        product_id = result.get("id") if isinstance(result, dict) else None
        url = result.get("short_url") if isinstance(result, dict) else None
        return PublishResult(
            ok=True,
            platform=self.name,
            product_id=product_id,
            url=url,
            error=None,
            dry_run=False,
        )

    def get_sales(self):
        """Fetch raw sales from Gumroad's /sales endpoint (ADR-016). Returns
        (sales: list, error: str|None) — never raises; a missing token or a
        failed request is reported as an error, same fail-safe style as
        publish(), so a poller can log it without crashing."""
        current_status = self.status()
        if current_status is not ArmStatus.READY:
            return [], f"arm not ready: {current_status.value}"
        try:
            token = gumroad_publisher.load_token()
            sales = gumroad_publisher.get_sales(token)
        except Exception as e:
            return [], str(e)
        return sales, None


registry.register(GumroadArm())
