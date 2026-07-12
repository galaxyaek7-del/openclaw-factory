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

# ADR-5: circuit breaker. Kept in-memory and per-process — no persistence
# needed yet at MVP scale (a single arm, never called automatically).
_COOLDOWN_THRESHOLD = 3


class GumroadArm(BaseArm):
    name = "gumroad"

    def __init__(self):
        self._consecutive_failures = 0

    def status(self) -> ArmStatus:
        if self._consecutive_failures >= _COOLDOWN_THRESHOLD:
            return ArmStatus.COOLDOWN
        try:
            gumroad_publisher.load_token()
        except gumroad_publisher.ConfigError:
            return ArmStatus.UNAVAILABLE
        return ArmStatus.READY

    def supports(self, product) -> bool:
        """Gumroad needs a real file and a resolved price. A Product still
        needing pricing (needs_pricing=True) is not supported yet — never
        invent a price here."""
        if not product.file_path:
            return False
        if product.price_usd is None or product.needs_pricing:
            return False
        return True

    def publish(self, product, dry_run: bool = True) -> PublishResult:
        current_status = self.status()
        if current_status is not ArmStatus.READY:
            return PublishResult(
                ok=False,
                platform=self.name,
                product_id=None,
                url=None,
                error=f"arm not ready: {current_status.value}",
                dry_run=dry_run,
            )

        if not self.supports(product):
            return PublishResult(
                ok=False,
                platform=self.name,
                product_id=None,
                url=None,
                error="product not supported (missing file_path or unresolved price)",
                dry_run=dry_run,
            )

        spec = {
            "title": product.title,
            "description": product.description,
            "price_cents": round(product.price_usd * 100),
            "file_path": product.file_path,
        }

        if dry_run:
            # Validate shape only. No network call, no gumroad_publisher
            # function is invoked — this is the safe default.
            return PublishResult(
                ok=True,
                platform=self.name,
                product_id=None,
                url=None,
                error=None,
                dry_run=True,
            )

        try:
            token = gumroad_publisher.load_token()
            result = gumroad_publisher.create_product(token, spec)
        except Exception as e:
            self._consecutive_failures += 1
            return PublishResult(
                ok=False,
                platform=self.name,
                product_id=None,
                url=None,
                error=str(e),
                dry_run=False,
            )

        self._consecutive_failures = 0
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
