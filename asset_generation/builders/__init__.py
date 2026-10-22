"""Self-registering asset builders (Universal Production Engine).

Importing this package registers today's real implementations — thin
wrappers over book_generator.py's already-tested, already-real full
generation pipelines (generate_book()/generate_product_package()), which
already include PDF/cover rendering, Dual Inspection, and Factory Memory
logging. No new rendering logic lives here.
"""

from . import pdf_builder  # noqa: F401
from . import xlsx_builder  # noqa: F401  (2026-10-22: real .xlsx, not a PDF about one)
