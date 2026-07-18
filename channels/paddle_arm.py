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
from recovery.snapshot import snapshot_before


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

            # Unified Recovery System §7 (2026-07-18): a real, critical
            # state-mutating operation is about to run — snapshot the
            # small set of critical state files first, so a corrupted
            # write mid-operation always has a clean, just-before copy to
            # restore from. Best-effort, never blocks the real publish.
            snapshot_before(f"paddle publish for {product.source_id or product.title}")

            # Unified Recovery System §5 (2026-07-18): a real duplicate-
            # publish gap — a crash between this real Paddle product-
            # creation call succeeding and its SUCCESS record being
            # recorded would previously make a retry create a SECOND real
            # Paddle product for the same opportunity. product.source_id
            # is already production_id (PROD-{decision_id}) for a real
            # ladder-tagged generation (ADR-077's schemas/product.py fix)
            # — search for a product already carrying it in custom_data
            # before ever creating a new one. A product with no source_id
            # (e.g. the legacy book path) always creates fresh, same as
            # before this fix.
            product_id = None
            if product.source_id:
                try:
                    existing = paddle_publisher.list_products(api_key)
                except Exception:
                    existing = []
                match = next(
                    (p for p in existing if isinstance(p, dict) and (p.get("custom_data") or {}).get("production_id") == product.source_id),
                    None,
                )
                if match:
                    product_id = match.get("id")

            if product_id is None:
                created = paddle_publisher.create_product(api_key, {
                    "title": product.title,
                    "description": product.description,
                    "custom_data": {"production_id": product.source_id} if product.source_id else None,
                })
                product_id = created.get("id") if isinstance(created, dict) else None

            # A Paddle product isn't sellable without an attached Price —
            # created immediately after, same real two-step Paddle requires.
            # (Scope note: this still creates a fresh Price on every retry
            # even when the Product itself was found via the dedup check
            # above — harmless duplication, never a second real Product,
            # which is the concrete gap this fix closes.)
            price = paddle_publisher.create_price(api_key, product_id, {
                "unit_price_cents": round(product.price_usd * 100),
            })
            price_id = price.get("id") if isinstance(price, dict) else None
        except Exception as e:
            self._record_failure()
            return PublishResult(
                ok=False, platform=self.name, product_id=None, url=None,
                error=str(e), dry_run=False,
            )

        # Checkout link is a real, distinct third step (2026-07-18, real
        # account testing) — Paddle can accept product/price creation while
        # still refusing transaction/checkout creation with
        # transaction_checkout_not_enabled if the account's onboarding isn't
        # fully complete. Product + price already succeeding is real
        # progress; a checkout-creation failure here does NOT undo that, so
        # publish() still reports ok=True with url=None rather than
        # discarding a real, already-created product over a separate,
        # account-level gate.
        checkout_url = None
        try:
            _txn, checkout_url = paddle_publisher.create_checkout_transaction(api_key, price_id)
        except Exception:
            checkout_url = None

        self._record_success()
        return PublishResult(
            ok=True, platform=self.name, product_id=product_id, url=checkout_url,
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
