"""
AutoPublisher -- autonomous publish gated on 5 hard gates.

Founder authorization: 2026-10-17 ("المصنع ينشر تلقائياً كل منتج يجتاز معايير
الجودة الخمسة"). Autonomous, permanent. No per-product approval.

Publishes ONLY when all 5 gates pass. No overrides, no bypass, no exceptions.

Cycle 91 security recovery (2026-10-17): the original version called the
Gumroad REST API directly (urllib), bypassing channels/write_gate.py, never
checking FACTORY_LIVE_PUBLISH, and creating a published product with no file
attached. The live step now goes through distributor.distribute() and
channels/gumroad_publisher.create_product() only, so every factory control
applies (write gate, scoped upload authorization, daily caps, duplicate
checks). The founder authorization cited above is recorded as stated by the
parallel session; it is unconfirmed in the reviewing session
(reports/governance/AUTO_PUBLISHER_REVIEW_CYCLE88.md).
"""
from src.quality.quality_enforcer import QualityEnforcer
from src.pricing.dynamic_pricer import DynamicPricer
import os, json
from datetime import datetime


def _load_dotenv(path: str = ".env") -> None:
    """Populate os.environ from .env without overriding real env vars."""
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    except OSError:
        pass


_load_dotenv()


def _live_publish_enabled() -> bool:
    """The factory-wide live-publish switch.

    Same convention as channels/write_gate.py and server.js/factory_loop.js.
    Fail closed: anything other than an explicit truthy value keeps live
    publishing disabled. This module previously had NO such check, so a
    product passing all 5 gates would POST live regardless of the factory
    switch (CYCLE 90 publish-safety recovery).
    """
    return str(os.environ.get("FACTORY_LIVE_PUBLISH", "")).strip().lower() in (
        "1", "true", "yes", "on")


def _say(msg: str) -> None:
    """print() that cannot crash the publisher: a Windows cp1252 console
    raises UnicodeEncodeError on the emoji below (found in the Cycle 88
    review, where it aborted publish() right after logging)."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))


class AutoPublisher:
    """
    Publishes automatically ONLY when
    all 5 gates pass.
    No exceptions. No overrides.
    No bypass.
    Founder authorization: 2026-10-17
    """

    def __init__(self, log_path: str = "data/publish_log.jsonl"):
        self.enforcer = QualityEnforcer()
        self.pricer   = DynamicPricer()
        self.log_path = log_path

    # Declared product files are bare basenames; resolve against known dirs.
    _FILE_BASES = ("", "books/batch12/", "books/", "reports/")

    def _resolve_files(self, files) -> list:
        """Resolve declared product files to real paths.

        Batch records declare bare filenames (see
        tests/test_distributor.py::_b12_product, which prefixes
        'books/batch12/'), while QualityEnforcer resolves 'files' relative to
        the repo root. Try the real product dirs first; an unresolvable name
        is passed through unchanged so the enforcer still reports it missing.
        """
        out = []
        for f in files or []:
            if os.path.isabs(f):
                out.append(f)
                continue
            for base in self._FILE_BASES:
                cand = os.path.join(base, f) if base else f
                if os.path.exists(cand):
                    out.append(cand)
                    break
            else:
                out.append(f)
        return out

    # ══════════════════════════════
    # THE 5 GATES
    # ══════════════════════════════

    def gate_1_quality(self, product: dict, content: str) -> dict:
        """Layer 1-3 quality inspection"""
        result = self.enforcer.full_inspection(
            product, content, files=self._resolve_files(product.get("files"))
        )
        scores = result.get("scores") or {}
        numeric = [v for v in scores.values() if isinstance(v, (int, float))]
        overall = round(sum(numeric) / len(numeric), 1) if numeric else 0
        return {
            "gate": 1,
            "name": "QUALITY_3_LAYERS",
            "passed": result["allowed_to_publish"],
            "score": overall,
            "verdict": result["final_verdict"],
            "detail": result.get("reason", "")
        }

    def gate_2_price(self, product: dict) -> dict:
        """Price must have real competitor source"""
        basis = product.get("price_basis", "")
        evidence = product.get("demand_evidence", {})
        evidence_type = evidence.get("type", "NONE")

        passed = (
            basis in [
                "MARKET_MINUS_10_PERCENT",
                "MARGIN_FLOOR"
            ] and
            evidence_type in ["REAL", "DERIVED"] and
            product.get("price_usd", 0) > 0
        )

        return {
            "gate": 2,
            "name": "PRICE_EVIDENCE_BASED",
            "passed": passed,
            "price": product.get("price_usd"),
            "basis": basis,
            "evidence_type": evidence_type,
            "detail": "" if passed else
                "Price needs real competitor source"
        }

    def gate_3_cover(self, product: dict) -> dict:
        """Cover image must exist at 1280x720"""
        product_id = product.get("id", "")
        slug = product.get("slug", "")

        cover_paths = [
            f"books/covers/{product_id}.png",
            f"books/covers/{slug}.png",
            f"reports/{product_id}/cover.png",
        ]

        found_path = None
        for path in cover_paths:
            if os.path.exists(path):
                found_path = path
                break

        if not found_path:
            return {
                "gate": 3,
                "name": "COVER_EXISTS",
                "passed": False,
                "detail": "No cover image found"
            }

        # Verify dimensions
        try:
            from PIL import Image
            img = Image.open(found_path)
            w, h = img.size
            correct = (w == 1280 and h == 720)
        except Exception:
            # Fail closed (Cycle 88 review): an unreadable cover is not a
            # verified 1280x720 cover. This used to pass the gate.
            w = h = None
            correct = False

        return {
            "gate": 3,
            "name": "COVER_EXISTS",
            "passed": correct,
            "path": found_path,
            "detail": "" if correct else
                f"Cover is {w}x{h}, needs 1280x720"
        }

    def gate_4_description(self, content: str) -> dict:
        """Description must be 300+ words"""
        word_count = len(content.split()) if content else 0
        passed = word_count >= 300

        return {
            "gate": 4,
            "name": "DESCRIPTION_300_WORDS",
            "passed": passed,
            "word_count": word_count,
            "detail": "" if passed else
                f"Only {word_count} words, need 300+"
        }

    def gate_5_complete(self, product: dict, content: str) -> dict:
        """No placeholders or incomplete content"""
        placeholders = [
            "[TODO]", "[ADD]", "[FILL]",
            "[INSERT]", "[TBD]", "[PLACEHOLDER]",
            "...", "[COMING SOON]"
        ]

        all_text = content + json.dumps(product)
        found = [p for p in placeholders if p in all_text]

        return {
            "gate": 5,
            "name": "NO_PLACEHOLDERS",
            "passed": len(found) == 0,
            "found": found,
            "detail": "" if not found else
                f"Incomplete content: {found}"
        }

    # ══════════════════════════════
    # MAIN PUBLISH FLOW
    # ══════════════════════════════

    def evaluate(self, product: dict, content: str) -> dict:
        """Run all 5 gates. Returns publish decision."""
        gates = [
            self.gate_1_quality(product, content),
            self.gate_2_price(product),
            self.gate_3_cover(product),
            self.gate_4_description(content),
            self.gate_5_complete(product, content),
        ]

        passed_count = sum(1 for g in gates if g["passed"])
        all_passed = passed_count == 5
        failed = [g for g in gates if not g["passed"]]

        return {
            "product_id": product.get("id"),
            "product_name": product.get("name") or product.get("title"),
            "price": product.get("price_usd"),
            "gates": gates,
            "gates_passed": passed_count,
            "gates_failed": len(failed),
            "all_passed": all_passed,
            "decision": "PUBLISH" if all_passed else "HOLD",
            "failed_gates": [f["name"] for f in failed],
            "evaluated_at": datetime.utcnow().isoformat()
        }

    def publish(self, product: dict, content: str) -> dict:
        """Publish to Gumroad if all 5 gates pass. Logs everything."""
        evaluation = self.evaluate(product, content)

        log_entry = {**evaluation, "action": None, "gumroad_response": None}

        if not evaluation["all_passed"]:
            log_entry["action"] = "HELD"
            log_entry["reason"] = f"Failed gates: {evaluation['failed_gates']}"
            self._log(log_entry)
            _say(
                f"⏸️  HELD: {product.get('name') or product.get('title')}"
                f"\n   Failed: {evaluation['failed_gates']}"
            )
            return log_entry

        # All 5 gates passed, but the factory-wide live-publish switch must
        # also be on. Fail closed: absent/false => held, never a live POST.
        if not _live_publish_enabled():
            log_entry["action"] = "HELD"
            log_entry["reason"] = (
                "all 5 gates passed, but live publish is disabled "
                "(FACTORY_LIVE_PUBLISH is not true)")
            self._log(log_entry)
            _say(
                f"⏸️  HELD: {product.get('name') or product.get('title')}"
                f"\n   Passed all 5 gates; live publish disabled"
            )
            return log_entry


        # All 5 gates passed -> publish
        gumroad_result = self._publish_to_gumroad(product, content)

        log_entry["action"] = (
            "PUBLISHED" if gumroad_result["success"] else "PUBLISH_FAILED"
        )
        log_entry["gumroad_response"] = gumroad_result

        self._log(log_entry)

        if gumroad_result["success"]:
            _say(
                f"✅ PUBLISHED: {product.get('name') or product.get('title')}"
                f"\n   Price: ${product.get('price_usd')}"
                f"\n   URL: {gumroad_result.get('url')}"
            )
            self._notify_telegram(product, gumroad_result)
        else:
            _say(
                f"❌ PUBLISH FAILED: {product.get('name') or product.get('title')}"
                f"\n   Error: {gumroad_result.get('error')}"
            )

        return log_entry

    def _publish_to_gumroad(self, product: dict, content: str) -> dict:
        """Live create, through the factory's one controlled path (Cycle 91).

        The direct urllib POST that used to live here created a PUBLISHED
        product with no file attached and skipped every factory control. It
        is gone. A live attempt now goes distributor.distribute() ->
        channels.gumroad_arm -> channels.gumroad_publisher.create_product(),
        so it gets: the ledger duplicate check, publish_protection daily
        caps and cooldowns, the file-usability and claim-integrity gates, the
        write gate (FACTORY_LIVE_PUBLISH + verified credential), the
        single-use scoped upload authorization, the attachment readability
        check, and the live-catalog duplicate-title check.
        """
        # Defense in depth: never start a live attempt unless the
        # factory-wide live-publish switch is explicitly on.
        if not _live_publish_enabled():
            return {"success": False,
                    "error": "live publish disabled (FACTORY_LIVE_PUBLISH is not true)"}
        files = self._resolve_files(product.get("files"))
        if not files or not os.path.isfile(files[0]):
            return {"success": False, "error": "no deliverable file resolved; not creating a listing"}
        try:
            price = float(product.get("price_usd") or product.get("price") or 0)
        except (TypeError, ValueError):
            price = 0.0
        if price <= 0:
            return {"success": False, "error": "no valid price; not creating a listing"}
        if product.get("file_sha256"):
            from channels import gumroad_publisher
            try:
                gumroad_publisher._check_attachment(files[0], product["file_sha256"])
            except Exception as e:  # noqa: BLE001
                return {"success": False, "error": str(e)}

        import distributor
        from schemas.product import Product
        title = product.get("name") or product.get("title") or ""
        item = Product(
            title=title, subtitle="", description=content[:3000] if content else "",
            price_usd=price, file_path=files[0], cover_path=None,
            tags=list(product.get("tags") or []), language="en",
            source_id=str(product.get("id") or ""), raw_price_hint=price,
            needs_pricing=False, price_source="registry_verified",
        )
        outcomes = distributor.distribute(item, arm_names=["gumroad"], dry_run=False)
        o = outcomes[0] if outcomes else {}
        res = o.get("result")
        if o.get("ok") and res is not None and getattr(res, "ok", False):
            return {"success": True, "gumroad_id": res.product_id, "url": res.url,
                    "name": title, "published_at": datetime.utcnow().isoformat()}
        reason = o.get("skip_reason") or (getattr(res, "error", None) if res is not None else None) or "not attempted"
        return {"success": False, "error": reason}

    def _notify_telegram(self, product: dict, result: dict):
        """Send Telegram notification on publish"""
        webhook = os.getenv("N8N_TELEGRAM_WEBHOOK_URL")
        if not webhook:
            return

        import urllib.request, urllib.parse
        msg = (
            f"✅ منتج جديد منشور تلقائياً!\n"
            f"الاسم: {product.get('name') or product.get('title')}\n"
            f"السعر: ${product.get('price_usd')}\n"
            f"الرابط: {result.get('url')}"
        )

        try:
            data = urllib.parse.urlencode({"message": msg}).encode()
            req = urllib.request.Request(webhook, data=data)
            urllib.request.urlopen(req, timeout=10)
        except Exception:
            pass

    def _log(self, entry: dict):
        """Append to publish log"""
        os.makedirs(os.path.dirname(self.log_path) or ".", exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def run_batch(self, products_dir: str = "data"):
        """Scan all products and publish those that pass all 5 gates."""
        import glob

        product_files = (
            glob.glob(f"{products_dir}/product_batch_*.json") +
            glob.glob(f"{products_dir}/products/*.json")
        )

        _say(f"Found {len(product_files)} products")
        _say("Running 5-gate evaluation...\n")

        published, held, failed = [], [], []

        for pf in product_files:
            try:
                with open(pf) as f:
                    raw = json.load(f)

                # Accept either a single product object or a batch wrapper.
                products = raw.get("products") if isinstance(raw, dict) else None
                if not products:
                    products = [raw]

                for product in products:
                    product_id = product.get("id", "")
                    content = ""
                    for cp in [
                        f"books/{product_id}.md",
                        f"books/{product_id}/main.md",
                        f"reports/{product_id}/listing_content.md",
                        pf.replace(".json", ".md"),
                    ]:
                        if os.path.exists(cp):
                            with open(cp) as f:
                                content = f.read()
                            break

                    result = self.publish(product, content)

                    if result["action"] == "PUBLISHED":
                        published.append(product.get("name") or product.get("title"))
                    elif result["action"] == "HELD":
                        held.append({
                            "name": product.get("name") or product.get("title"),
                            "failed": result.get("reason", "")
                        })

            except Exception as e:
                failed.append({"file": pf, "error": str(e)})

        _say(f"\n═══ BATCH COMPLETE ═══")
        _say(f"✅ Published: {len(published)}")
        _say(f"⏸️  Held:      {len(held)}")
        _say(f"❌ Errors:    {len(failed)}")

        if published:
            _say("\nPublished:")
            for p in published:
                _say(f"  ✅ {p}")

        if held:
            _say("\nHeld (failed gates):")
            for h in held:
                _say(f"  ⏸️  {h['name']}: {h['failed']}")

        return {
            "published": len(published),
            "held": len(held),
            "errors": len(failed),
            "published_names": published
        }
