"""S3-AFFILIATE-01: revalidate_all() must persist fresh probes (the stale-list
never shrank because probes were never stamped). Isolated: tmp portfolio +
monkeypatched network + monkeypatched intelligence rows built from the tmp
records (no real registry, no network)."""
import json
import os


from affiliate import healthcheck as H
from affiliate import intelligence as I
from commission_engine import save_opportunity_portfolio


def _opp(oid, urls):
    return {
        "opportunity_id": oid,
        "last_verified": None,
        "evidence_url": urls,
        "verification_status": "VERIFIED",
        "commission_value": "5%",
        "source": "test",
    }


def test_persist_stamps_probed_only(tmp_path, monkeypatch):
    path = str(tmp_path / "opp.jsonl")
    save_opportunity_portfolio(
        [
            _opp("A", ["https://example.com/a"]),
            _opp("B", []),  # no evidence URL -> must NOT be stamped
        ],
        path,
    )
    monkeypatch.setattr(
        H, "url_health", lambda urls, timeout=8: [{"url": urls[0], "ok": True, "status": 200}]
    )

    import commission_engine as ce

    orig_intel = I.portfolio_intelligence

    def fake_intel(portfolio=None, now=None):
        return orig_intel(
            portfolio=ce.load_opportunity_portfolio(path)
        )

    monkeypatch.setattr(I, "portfolio_intelligence", fake_intel)
    # local_scan reads the real registry; bypass it: all rows count as stale
    # so the stamp path is exercised for every probed program.
    monkeypatch.setattr(H, "local_scan", lambda: {"stale_verification": ["A", "B"]})

    out = H.revalidate_all(portfolio_path=path)
    assert out["restamped"] == 1

    recs = {
        r["opportunity_id"]: r for r in ce.load_opportunity_portfolio(path)
    }
    assert recs["A"]["last_verified"] is not None
    assert "last_verified_evidence" in recs["A"]
    assert recs["B"]["last_verified"] is None
    assert "last_verified_evidence" not in recs["B"]


def test_persist_false_writes_nothing(tmp_path, monkeypatch):
    path = str(tmp_path / "opp.jsonl")
    save_opportunity_portfolio([_opp("A", ["https://example.com/a"])], path)
    before = open(path, encoding="utf-8").read()
    monkeypatch.setattr(
        H, "url_health", lambda urls, timeout=8: [{"url": urls[0], "ok": True, "status": 200}]
    )
    monkeypatch.setattr(H, "local_scan", lambda: {"stale_verification": []})
    H.revalidate_all(persist=False, portfolio_path=path)
    assert open(path, encoding="utf-8").read() == before
