"""Tests for the autonomous 5-gate publisher (Founder authorization 2026-10-17)."""


def test_all_5_gates_required():
    from src.publish.auto_publisher import AutoPublisher
    pub = AutoPublisher()

    # Product missing cover -> gate 3 fails
    product = {
        "id": "test-no-cover-xxx",
        "name": "Test Product",
        "price_usd": 29,
        "price_basis": "MARKET_MINUS_10_PERCENT",
        "demand_evidence": {"type": "REAL"},
        "problem_statement": "A" * 60,
        "target_audience": "B" * 30,
        "measurable_value": "C" * 40,
        "differentiation": "D" * 35,
        "distribution_channels": ["gumroad"],
        "competition_level": "MEDIUM",
        "tags": ["tag1"],
    }
    content = "Real content " * 50

    result = pub.evaluate(product, content)
    assert result["decision"] == "HOLD"
    assert "COVER_EXISTS" in result["failed_gates"]


def test_no_publish_without_price_evidence():
    from src.publish.auto_publisher import AutoPublisher
    pub = AutoPublisher()

    product = {
        "id": "test-no-price-evidence",
        "price_usd": 29,
        "price_basis": "UNKNOWN",
        "demand_evidence": {"type": "MOCK"},
    }
    gate = pub.gate_2_price(product)
    assert gate["passed"] is False


def test_no_publish_with_placeholders():
    from src.publish.auto_publisher import AutoPublisher
    pub = AutoPublisher()

    content = "Real content " * 30 + "[TODO]"
    gate = pub.gate_5_complete({}, content)
    assert gate["passed"] is False
    assert "[TODO]" in gate["found"]


def test_description_under_300_blocked():
    from src.publish.auto_publisher import AutoPublisher
    pub = AutoPublisher()

    content = "Short description only"
    gate = pub.gate_4_description(content)
    assert gate["passed"] is False
    assert gate["word_count"] < 300


def test_publish_log_created():
    from src.publish.auto_publisher import AutoPublisher
    import os
    pub = AutoPublisher()
    pub._log({"test": True, "action": "TEST"})
    assert os.path.exists(pub.log_path)
