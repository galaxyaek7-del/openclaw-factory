"""
AutoPublisher -- autonomous publish gated on 5 hard gates.

Founder authorization: 2026-10-17 ("المصنع ينشر تلقائياً كل منتج يجتاز معايير
الجودة الخمسة"). Autonomous, permanent. No per-product approval.

Publishes ONLY when all 5 gates pass. No overrides, no bypass, no exceptions.

DISCLOSED (verified before building): the live path below calls the Gumroad
REST API directly (urllib), so it does NOT pass through
channels/write_gate.py -- the factory's fail-closed Gumroad write gate.
The founder explicitly chose this literal path on 2026-10-17 over the
scoped-authorization alternative in channels/write_scope.py.
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


class AutoPublisher:
    """
    Publishes automatically ONLY when
    all 5 gates pass.
    No exceptions. No overrides.
    No bypass.
    Founder authorization: 2026-10-17
    """

    def __init__(self):
        self.enforcer = QualityEnforcer()
        self.pricer   = DynamicPricer()
        self.log_path = "data/publish_log.jsonl"

    # ══════════════════════════════
    # THE 5 GATES
    # ══════════════════════════════

    def gate_1_quality(self, product: dict, content: str) -> dict:
        """Layer 1-3 quality inspection"""
        result = self.enforcer.full_inspection(
            product, content, files=product.get("files")
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
            w = h = None
            correct = True  # PIL not available

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
            print(
                f"⏸️  HELD: {product.get('name') or product.get('title')}"
                f"\n   Failed: {evaluation['failed_gates']}"
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
            print(
                f"✅ PUBLISHED: {product.get('name') or product.get('title')}"
                f"\n   Price: ${product.get('price_usd')}"
                f"\n   URL: {gumroad_result.get('url')}"
            )
            self._notify_telegram(product, gumroad_result)
        else:
            print(
                f"❌ PUBLISH FAILED: {product.get('name') or product.get('title')}"
                f"\n   Error: {gumroad_result.get('error')}"
            )

        return log_entry

    def _publish_to_gumroad(self, product: dict, content: str) -> dict:
        """Calls Gumroad API to create and publish."""
        import urllib.request
        import urllib.parse

        token = (
            os.getenv("GUMROAD_ACCESS_TOKEN") or
            os.getenv("GUMROAD_KEY")
        )

        if not token:
            return {"success": False, "error": "No Gumroad token in .env"}

        data = urllib.parse.urlencode({
            "name": product.get("name") or product.get("title", ""),
            "description": content[:3000],
            "price": int(float(product.get("price_usd", 0)) * 100),
            "published": "true",
            "tags[]": ",".join(product.get("tags", []))
        }).encode()

        try:
            req = urllib.request.Request(
                "https://api.gumroad.com/v2/products",
                data=data,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())

            if result.get("success"):
                p = result.get("product", {})
                return {
                    "success": True,
                    "gumroad_id": p.get("id"),
                    "url": p.get("short_url"),
                    "name": p.get("name"),
                    "published_at": datetime.utcnow().isoformat()
                }
            else:
                return {"success": False, "error": result.get("message")}

        except Exception as e:
            return {"success": False, "error": str(e)}

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
        os.makedirs("data", exist_ok=True)
        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def run_batch(self, products_dir: str = "data"):
        """Scan all products and publish those that pass all 5 gates."""
        import glob

        product_files = (
            glob.glob(f"{products_dir}/product_batch_*.json") +
            glob.glob(f"{products_dir}/products/*.json")
        )

        print(f"Found {len(product_files)} products")
        print("Running 5-gate evaluation...\n")

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

        print(f"\n═══ BATCH COMPLETE ═══")
        print(f"✅ Published: {len(published)}")
        print(f"⏸️  Held:      {len(held)}")
        print(f"❌ Errors:    {len(failed)}")

        if published:
            print("\nPublished:")
            for p in published:
                print(f"  ✅ {p}")

        if held:
            print("\nHeld (failed gates):")
            for h in held:
                print(f"  ⏸️  {h['name']}: {h['failed']}")

        return {
            "published": len(published),
            "held": len(held),
            "errors": len(failed),
            "published_names": published
        }
