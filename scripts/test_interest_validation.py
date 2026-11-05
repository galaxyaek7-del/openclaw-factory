"""GF-16 repair: missing-message validation WITHOUT a live POST.

The old version POSTed to the live endpoint believing it "writes nothing" —
but every rejection is persisted to customer_interest_rejected.jsonl, so each
run polluted the commercial ledger. This version calls the pure validator
directly (zero writes) and asserts the same expected outcome.
"""
import sys
sys.path.insert(0, ".")
from lib.customer_evidence import validate_and_classify
# Missing message -> expect rejection from validation (proves module chain, writes nothing)
ok, cls, reason, enr = validate_and_classify({"email": "test-event@example.com"})
print("VALIDATE:", ok, reason)
assert not ok and reason == "interest message too short", reason
print("PASS: rejected locally, zero ledger writes")
