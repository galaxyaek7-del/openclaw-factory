# -*- coding: utf-8 -*-
"""Galaxy Forge: Shopify arm (2026-11-07). A thin BaseArm on channels/shopify_publisher.py.

dry_run (the default) validates the product shape and the Shopify payload locally: no network call. A live attempt creates a DRAFT
only (never active) and only when the write gate, the publication clearance and both credentials allow it. Self-registers on import.
"""
from __future__ import annotations

from .base_arm import ArmStatus, BaseArm, PublishResult
from . import registry, shopify_publisher


class ShopifyArm(BaseArm):
    name = "shopify"

    def status(self) -> ArmStatus:
        return self._status_via(shopify_publisher.load_config, shopify_publisher.ConfigError)

    def _spec(self, product):
        return {"title": product.title, "description": product.description, "price_cents": int(round(float(product.price_usd) * 100)),
                "tags": list(getattr(product, "tags", None) or []), "file_path": product.file_path}

    def publish(self, product, dry_run: bool = True, publication_clearance=None, transport=None) -> PublishResult:
        if not self.supports(product):
            return self._not_supported_result(dry_run)
        spec = self._spec(product)
        try:
            shopify_publisher.build_product_input(spec)  # local validation in dry-run and live alike
        except shopify_publisher.ConfigError as e:
            return PublishResult(ok=False, platform=self.name, product_id=None, url=None, error=f"invalid product for Shopify: {e}", dry_run=dry_run)
        if dry_run:
            return self._dry_run_result()
        current = self.status()
        if current is not ArmStatus.READY:
            return self._not_ready_result(current, dry_run)
        try:
            kw = {"publication_clearance": publication_clearance}
            if transport is not None:
                kw["transport"] = transport
            out = shopify_publisher.create_draft_product(spec, **kw)
        except Exception as e:  # noqa: BLE001 every failure is reported, never raised into the loop
            self._record_failure()
            return PublishResult(ok=False, platform=self.name, product_id=None, url=None, error=f"{type(e).__name__}: {str(e)[:160]}", dry_run=False)
        self._record_success()
        return PublishResult(ok=True, platform=self.name, product_id=out["product_id"], url=None, error=None, dry_run=False)


registry.register(ShopifyArm())
