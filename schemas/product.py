"""OpenClaw Factory — Canonical Product schema.

The single translation point between books/_generation_log.jsonl (the real
production log written by book_generator.py) and every distribution channel.
Fixing a field-name mismatch belongs here, once — never inside an individual
arm.

Field mapping was derived by reading books/_generation_log.jsonl directly
(68 real records spanning three schema generations: no cover/inspection,
cover-only, and full cover+inspection), not guessed:

  Product field  <- JSONL field(s), in the order actually observed
  -------------  --------------------------------------------------
  title          <- inspection.title, else top-level "title" (failure-case
                     placeholder, e.g. "X"), else "topic", else ""
  subtitle       <- never present in any observed record -> ""
  description    <- "topic" (the niche/brief text — the closest thing to a
                     product description the log actually records) -> ""
  raw_price_hint <- "price" (float; missing on failed generations) -> 0.0.
                     Reference only — see price_usd below for why this is
                     never used as-is.
  file_path      <- "path" (absolute path to the generated PDF) -> ""
  cover_path     <- cover.path, if a "cover" object is present -> None
  tags           <- never present in any observed record -> []
  language       <- never present in any observed record; every record
                     inspected is Arabic content (arabic_shaping_available
                     checks confirm this), so "ar" is used as the safe
                     default rather than left unset
  source_id      <- top-level "timestamp" (the only field present on 100%
                     of observed records, including the one failure case
                     with no "path"/"price") -> ""

price_usd is NOT copied from the raw record. economics.py exists precisely
to replace the old hardcoded "$30 floor" with a real per-unit profit
calculation (Constitution §16, Butter Principle = a PROFIT floor, not a
price floor) — reading price straight off the JSONL log would just
reintroduce the bug economics.py was built to close. Instead:

  1. raw_price_hint is kept for reference only (what the log/Groq
     originally suggested).
  2. That hint is run through economics.evaluate(price, "kdp_ebook",
     config) — "kdp_ebook" specifically because it is the only platform in
     config/economics.json with real royalty_tiers (Gumroad/paperback are
     flat-rate), and because economics.py's own docstring frames itself as
     the KDP $30-floor replacement. Product has no platform field yet, so
     this is a documented assumption, not a guess about data: the tier
     table and profit floor it evaluates against are read from
     config/economics.json exactly as written, nothing invented.
  3. evaluate() is called with page_count from the record's "pages" field,
     so its market_realism_check (added on top of the existing profit-floor
     check) can actually run instead of skipping for lack of page data.
  4. If evaluate() approves the hint on profit grounds AND market_realistic
     is True, price_usd = raw_price_hint, price_source = "profit_raw".
  5. If evaluate() approves the hint on profit grounds but flags
     market_realistic = False (profitable on paper, not credible for the
     page count — e.g. $49 for a 12-page book), price_usd =
     suggested_realistic_price instead, price_source = "realistic". A
     blind profit-floor pass is never used once the engine itself says the
     price isn't believable.
  6. Any other outcome — economics.py/its config missing or malformed, the
     price matching no royalty tier, a clean "not approved" verdict, or
     market_realistic=False with no suggested_realistic_price to fall back
     on — leaves price_usd = None, price_source = None, needs_pricing =
     True. No fallback price is ever invented here; a Product that needs
     pricing says so honestly instead of carrying a fabricated number.

Standalone module. No imports from the rest of the factory except economics
(read-only, never modified by this module).
"""

import sys
from dataclasses import dataclass
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent


def _load_economics_module():
    """Import economics.py by absolute path, independent of the caller's
    cwd. economics.py itself still assumes cwd == factory root for its own
    config/economics.json read (unchanged, not our concern here) — this
    only fixes *import* resolution so `from schemas.product import Product`
    works no matter where the process was started from."""
    if str(_FACTORY_ROOT) not in sys.path:
        sys.path.insert(0, str(_FACTORY_ROOT))
    import economics  # noqa: E402
    return economics


@dataclass
class Product:
    title: str
    subtitle: str
    description: str
    price_usd: float | None
    file_path: str
    cover_path: str | None
    tags: list
    language: str
    source_id: str
    raw_price_hint: float
    needs_pricing: bool
    price_source: str | None
    # Added 2026-07-11 (OCTOPUS_ARCHITECTURE.md §4 generalization): which
    # kind of product this is. Defaults to "book" so every existing caller
    # (from_jsonl_record, any code already constructing a Product by keyword)
    # keeps working unchanged. Only book/template/image/audio/course are
    # meaningful today — other engines don't exist yet (CLAUDE.md's six
    # tracks), so this is just a label, not a dispatch table.
    product_type: str = "book"

    @staticmethod
    def from_jsonl_record(record: dict) -> "Product":
        """Translate one books/_generation_log.jsonl record into a Product.

        Defensive: any missing/malformed field falls back to a safe default
        instead of raising. A malformed record should never crash a
        distribution run — it should just produce a thin, honest Product.
        """
        if not isinstance(record, dict):
            record = {}

        inspection = record.get("inspection")
        if not isinstance(inspection, dict):
            inspection = {}

        title = inspection.get("title") or record.get("title") or record.get("topic") or ""

        description = record.get("topic") or ""

        price_raw = record.get("price")
        try:
            raw_price_hint = float(price_raw) if price_raw is not None else 0.0
        except (TypeError, ValueError):
            raw_price_hint = 0.0

        file_path = record.get("path") or ""

        cover = record.get("cover")
        cover_path = cover.get("path") if isinstance(cover, dict) else None

        # ADR-020/ADR-024: printables and premium bundles (product_type
        # written explicitly by book_generator.py's generate_printable()/
        # generate_book_from_content()) are distributed on Gumroad, never
        # KDP — their economics must be evaluated against "gumroad_digital"/
        # "gumroad_premium" (their own profit floors), not "kdp_ebook". Any
        # record without this field (every book produced before today)
        # keeps evaluating against "kdp_ebook" exactly as before — this is
        # purely additive, not a behavior change for books.
        product_type = record.get("product_type") or "book"
        if product_type == "printable":
            economics_platform = "gumroad_digital"
        elif product_type == "premium":
            economics_platform = "gumroad_premium"
        else:
            economics_platform = "kdp_ebook"

        price_usd = None
        needs_pricing = True
        price_source = None
        if price_raw is not None:
            try:
                economics = _load_economics_module()
                config = economics.load_config()
                page_count = record.get("pages")
                result = economics.evaluate(raw_price_hint, economics_platform, config, page_count=page_count)
                if result.get("approved"):
                    if result.get("market_realistic") is False:
                        suggested = result.get("suggested_realistic_price")
                        if suggested is not None:
                            price_usd = suggested
                            price_source = "realistic"
                            needs_pricing = False
                        # else: defensive — flagged unrealistic but no
                        # suggested_realistic_price to fall back on. Stay
                        # at price_usd=None/needs_pricing=True below rather
                        # than inventing a number.
                    else:
                        price_usd = raw_price_hint
                        price_source = "profit_raw"
                        needs_pricing = False
            except Exception:
                # economics.py missing/malformed config, no matching royalty
                # tier, or any other failure — never invent a price. Stays
                # price_usd=None, price_source=None, needs_pricing=True.
                price_usd = None
                price_source = None
                needs_pricing = True

        return Product(
            title=title,
            subtitle="",
            description=description,
            price_usd=price_usd,
            file_path=file_path,
            cover_path=cover_path,
            tags=[],
            language="ar",
            source_id=record.get("timestamp") or "",
            raw_price_hint=raw_price_hint,
            needs_pricing=needs_pricing,
            price_source=price_source,
            product_type=product_type,
        )
