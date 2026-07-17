"""OpenClaw Factory — Paddle arm (ADR-065/MASTER_CHARTER.md §2, Step 4).

A thin adapter that implements BaseArm on top of paddle_publisher.py, same
role gumroad_arm.py plays for gumroad_publisher.py. paddle_publisher.py is
not modified — every real Paddle API call still goes through
create_product()/create_price() exactly as written.

Graceful "not configured" state (mission requirement): with no
PADDLE_API_KEY, status() returns ArmStatus.UNAVAILABLE via the same shared
_status_via() skeleton every other arm uses — publish() then returns
_not_ready_result() rather than raising. No PADDLE_API_KEY has ever existed
in this factory, so this arm has never made a real API call; it exists so
the moment a real key is added, publishing an AI SaaS/B2B product needs zero
additional code, exactly like Gumroad only needed GUMROAD_ACCESS_TOKEN.

Self-registers on import: `import channels.paddle_arm` is enough to make
the "paddle" arm available via channels.registry.get("paddle").
"""

from .base_arm import BaseArm, ArmStatus, PublishResult
from . import paddle_publisher
from . import registry


class PaddleArm(BaseArm):
    name = "paddle"

    def status(self) -> ArmStatus:
        return self._status_via(paddle_publisher.load_api_key, paddle_publisher.ConfigError)

    def publish(self, product, dry_run: bool = True) -> PublishResult:
        current_status = self.status()
        if current_status is not ArmStatus.READY:
            return self._not_ready_result(current_status, dry_run)

        if not self.supports(product):
            return self._not_supported_result(dry_run)

        if dry_run:
            return self._dry_run_result()

        try:
            api_key = paddle_publisher.load_api_key()
            created = paddle_publisher.create_product(api_key, {
                "title": product.title,
                "description": product.description,
            })
            product_id = created.get("id") if isinstance(created, dict) else None
            # A Paddle product isn't sellable without an attached Price —
            # created immediately after, same real two-step Paddle requires.
            paddle_publisher.create_price(api_key, product_id, {
                "unit_price_cents": round(product.price_usd * 100),
            })
        except Exception as e:
            self._record_failure()
            return PublishResult(
                ok=False, platform=self.name, product_id=None, url=None,
                error=str(e), dry_run=False,
            )

        self._record_success()
        return PublishResult(
            ok=True, platform=self.name, product_id=product_id, url=None,
            error=None, dry_run=False,
        )

    def get_sales(self):
        """Fetch raw transactions from Paddle's /transactions endpoint —
        Paddle's real-sales-data equivalent of GumroadArm.get_sales(). Same
        never-raises contract: a missing key or failed request is reported
        as an error, never an exception."""
        current_status = self.status()
        if current_status is not ArmStatus.READY:
            return [], f"arm not ready: {current_status.value}"
        try:
            api_key = paddle_publisher.load_api_key()
            transactions = paddle_publisher.get_transactions(api_key)
        except Exception as e:
            return [], str(e)
        return transactions, None


registry.register(PaddleArm())
