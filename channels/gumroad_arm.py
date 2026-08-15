"""Galaxy Forge — Gumroad arm (OCTOPUS_ARCHITECTURE.md ADR-2).

STATUS UPDATE (2026-08-15, CTO+COO audit closure): the earlier "ARCHIVED
(ADR-065)" framing below is now stale. GUMROAD_ACCESS_TOKEN IS set in .env
and a REAL live product was created on the account 2026-08-14 (EU AI Act
Compliance Toolkit, product id pzTmMb4v8cih3nbWTj5TeA==, short URL
https://aekraft.gumroad.com/l/iaiyt, $155). What remains: the product is a
DRAFT (enable_product needs the account's payment method connected —
founder action), and the publish-protection state still shows
has_ever_published_successfully:false because that out-of-band creation was
never written to sales_ledger. Deprioritized-vs-SaaS remains the *priority*
stance, but "never activated / token missing" is no longer true.

"Archived" here means deprioritized and frozen, NOT deleted or physically
relocated: 7+ real, already-tested modules (distributor.py,
production_factory/dossier.py, multi_source_intelligence/connectors/
gumroad.py, strategic_intelligence/channel_value.py, executive_intelligence/
inactivity.py + revenue_distance.py, scripts/poll_sales.py, and their
tests) import this exact module path for self-registration/sales-polling.
Moving the file would require updating every one of those import sites in
the same change with real risk of missing one and silently breaking working
code — exactly the "ceremony/risk ahead of evidence" this factory's own
governance warns against (STRUCTURAL_DIAGNOSIS.md). Kept fully functional
and registered so existing sales-polling/legacy-book-distribution keeps
working unchanged; simply no longer the arm a new product defaults to.

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

    # ── Global Commercial Revenue Operating System (ADR-202, 2026-08-07) ──
    # Real overrides of BaseArm's default-NOT_IMPLEMENTED methods, only
    # where gumroad_publisher.py already has the underlying real call.

    def list_products(self):
        current_status = self.status()
        if current_status is not ArmStatus.READY:
            return {"status": "NOT_READY", "platform": self.name, "reason": current_status.value}
        try:
            token = gumroad_publisher.load_token()
            products = gumroad_publisher.list_products(token)
        except Exception as e:
            return {"status": "ERROR", "platform": self.name, "error": str(e)}
        return {"status": "OK", "platform": self.name, "products": products}

    def update_product(self, product_id, updates):
        current_status = self.status()
        if current_status is not ArmStatus.READY:
            return {"status": "NOT_READY", "platform": self.name, "reason": current_status.value}
        try:
            token = gumroad_publisher.load_token()
            result = gumroad_publisher.update_product(token, product_id, updates)
        except Exception as e:
            return {"status": "ERROR", "platform": self.name, "error": str(e)}
        return {"status": "OK", "platform": self.name, "product": result}


registry.register(GumroadArm())
