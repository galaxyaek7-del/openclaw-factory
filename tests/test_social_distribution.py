"""Social distribution engine: the 18 offline scenarios of GF-DISTRIBUTION-ENGINE-v1.0
plus regressions for defects found while building it. Synthetic fixtures, a fake
transport, temporary ledgers; no network and no production file is touched."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from content_generation import repurposing_engine as rep  # noqa: E402
from social_distribution import campaigns, content, dashboard, offers, platforms, prioritize, tracking  # noqa: E402

DESC = ("<p>See every week's cash position for the next quarter and spot the tight weeks before they happen.</p>"
        "<p>Monthly reports hide timing. A month can be profitable on paper while payroll lands first.</p>"
        "<ul><li>Weekly view of the next 13 weeks</li><li>No result, outcome or saving is guaranteed</li></ul>")


def registry(state="PUBLIC_LISTING_VERIFIED", price=1900, title="Cash Flow Forecast", iid="P-001"):
    return {"generated_at": "2026-10-23T00:00:00+00:00",
            "products": [{"internal_id": iid, "external_ids": {"gumroad": "g1"}, "title": title, "price_cents": price,
                          "published": state == "PUBLIC_LISTING_VERIFIED", "url": "https://shop.example.com/l/cash",
                          "sales_count": 0, "manifest": "books/batch14/P/manifest.json", "primary_state": state}]}


LIVE = [{"id": "g1", "description": DESC, "tags": ["cash flow", "small business"], "currency": "usd"}]


def product(**kw):
    o = offers.product_offers(registry(**kw), LIVE)[0]
    o["platforms"] = offers.PLATFORMS_BY_TYPE[o["type"]]
    o["language"] = "en"
    return o


def guide(desc="How freelancers stop scope creep before it starts. Free method; not legal advice."):
    return {"offer_id": "SITE-guide-scope", "arm": "education_content", "type": "content_asset", "subtype": "guide",
            "title": "Freelancer scope control", "problem": offers.first_sentence(desc), "url": "https://site.example.com/guide.html",
            "price_cents": None, "description": desc, "tags": [], "primary_state": "PUBLISHED_ON_MAIN",
            "eligibility": {"status": "ELIGIBLE", "reasons": []}, "platforms": ["linkedin", "x"], "rights_status": "OWNED_ORIGINAL",
            "measurement": {"destination": "github_pages"}}


READY = {"name": "T", "state": platforms.CREDENTIALS_PRESENT, "missing_credentials": [], "publish_mode": "API", "why": "test"}


class FakeTransport:
    def __init__(self, fail=None, visible=True):
        self.calls, self.fail, self.visible = [], list(fail or []), visible

    def publish(self, platform, draft):
        self.calls.append(("publish", platform))
        if self.fail:
            raise self.fail.pop(0)
        return {"post_id": f"{platform}-{len(self.calls)}", "url": f"https://{platform}.example/p/{len(self.calls)}"}

    def get(self, platform, post_id):
        self.calls.append(("get", platform))
        return {"visible": self.visible, "public": self.visible, "url": f"https://{platform}.example/{post_id}"}


class Base(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.td, ignore_errors=True)
        p = mock.patch.dict(os.environ, {"FACTORY_LIVE_PUBLISH": "false"})
        p.start()
        self.addCleanup(p.stop)
        self.t = FakeTransport()
        self.jobs = campaigns.Jobs(ledger=self.td / "jobs.jsonl", handoff_dir=self.td / "handoff",
                                   adapters={p: campaigns.Adapter(p, transport=self.t, readiness=dict(READY)) for p in platforms.PLATFORMS})

    def live(self):
        return mock.patch.dict(os.environ, {"FACTORY_LIVE_PUBLISH": "true"})

    def draft(self, offer, platform="linkedin", campaign=None):
        return content.draft(offer, platform, campaign=campaign or tracking.campaign_id(offer["offer_id"]))

    def approved(self, offer, platform="linkedin"):
        j = self.jobs.add_draft(self.draft(offer, platform))
        self.jobs.approve(j, approver="founder", evidence="approved in review 2026-10-23")
        self.jobs.queue(j)
        return j


class TestScenarios(Base):
    def test_01_valid_product_complete_campaign(self):
        o = product()
        j = self.approved(o)
        with self.live():
            self.jobs.publish(j, o)
        r = self.jobs.job(j)
        self.assertEqual(r["state"], "PUBLISHED_VERIFIED")
        self.assertEqual([c[0] for c in self.t.calls], ["publish", "get"])

    def test_02_unpublished_product_is_not_eligible(self):
        o = product(state="UPLOAD_COMPLETED")
        self.assertEqual(o["eligibility"]["status"], "NOT_ELIGIBLE")
        d = self.draft(o)
        self.assertFalse(d["qa"]["passed"])
        self.assertEqual(prioritize.plan([o]), [])

    def test_03_invalid_destination_url(self):
        for bad in (None, "http://insecure.example.com/x", "ftp://x"):
            with self.assertRaises(tracking.TrackingError):
                tracking.build_link(bad, "linkedin", "gf-p-001-202610", "c")
        o = product()
        d = self.draft(o)
        d["link"] = d["link"].replace("shop.example.com", "evil.example.com")
        self.assertTrue(any("points to" in i for i in content.qa(d, o)["issues"]))

    def test_04_missing_or_contradictory_claims(self):
        no_desc = offers.product_offers(registry(), [{"id": "g1", "description": "", "tags": []}])[0]
        self.assertIn("no listing description", " ".join(no_desc["eligibility"]["reasons"]))
        o = product()
        d = self.draft(o)
        d["fields"]["text"] += " Now only $5."
        self.assertTrue(any("does not match the offer price" in i for i in content.qa(d, o)["issues"]))

    def test_05_unsupported_media_format(self):
        o = product()
        self.assertTrue(any("rendered JPEG" in i for i in self.draft(o, "instagram")["qa"]["issues"]))
        self.assertTrue(any("rendered video" in i for i in self.draft(o, "tiktok")["qa"]["issues"]))
        g = guide()
        self.assertTrue(any("not a suitable platform" in i for i in content.draft(g, "instagram", campaign="gf-site-guide-scope-202610")["qa"]["issues"]))

    def test_06_missing_credentials(self):
        o = product()
        self.jobs.adapters["linkedin"] = campaigns.Adapter("linkedin", transport=self.t,
                                                           readiness=dict(READY, missing_credentials=["LINKEDIN_ACCESS_TOKEN"]))
        j = self.approved(o)
        with self.live():
            self.jobs.publish(j, o)
        self.assertEqual(self.jobs.job(j)["state"], "BLOCKED")
        self.assertEqual(self.t.calls, [])

    def test_07_insufficient_permissions_not_retried(self):
        o = product()
        self.t.fail = [campaigns.PermissionDenied("403 missing w_member_social")]
        j = self.approved(o)
        with self.live():
            self.jobs.publish(j, o)
        self.assertEqual(self.jobs.job(j)["state"], "BLOCKED")
        with self.live(), self.assertRaises(campaigns.Refused):
            self.jobs.publish(j, o)
        self.assertEqual(len(self.t.calls), 1)

    def test_08_rate_limited_waits_then_succeeds(self):
        now = [1000.0]
        self.jobs.clock = lambda: now[0]
        o = product()
        self.t.fail = [campaigns.RateLimited(retry_after_s=600)]
        j = self.approved(o)
        with self.live():
            self.jobs.publish(j, o)
            self.assertEqual(self.jobs.job(j)["state"], "RATE_LIMITED")
            with self.assertRaises(campaigns.Refused):
                self.jobs.publish(j, o)
            now[0] += 601
            self.jobs.publish(j, o)
        self.assertEqual(self.jobs.job(j)["state"], "PUBLISHED_VERIFIED")

    def test_09_timeouts_are_bounded(self):
        now = [0.0]
        self.jobs.clock = lambda: now[0]
        o = product()
        self.t.fail = [campaigns.TransientError("timeout")] * 5
        j = self.approved(o)
        with self.live():
            for _ in range(3):
                self.jobs.publish(j, o)
                now[0] += 10_000
        self.assertEqual(self.jobs.job(j)["state"], "FAILED")
        self.assertEqual(self.jobs.job(j)["attempts"], campaigns.MAX_ATTEMPTS)
        with self.live(), self.assertRaises(campaigns.Refused):
            self.jobs.publish(j, o)

    def test_10_duplicate_publishing_prevented(self):
        o = product()
        j = self.approved(o)
        self.assertEqual(self.jobs.add_draft(self.draft(o)), j)
        with self.live():
            self.jobs.publish(j, o)
            r = self.jobs.publish(j, o)
        self.assertTrue(r["duplicate"])
        self.assertEqual(sum(1 for c in self.t.calls if c[0] == "publish"), 1)

    def test_11_partial_multi_platform_failure_is_isolated(self):
        o = product()
        self.jobs.adapters["linkedin"] = campaigns.Adapter("linkedin", transport=FakeTransport(fail=[campaigns.PermissionDenied("no")]),
                                                           readiness=dict(READY))
        jl, jx = self.approved(o, "linkedin"), self.approved(o, "x")
        with self.live():
            self.jobs.publish(jl, o)
            self.jobs.publish(jx, o)
        self.assertEqual(self.jobs.job(jl)["state"], "BLOCKED")
        self.assertEqual(self.jobs.job(jx)["state"], "PUBLISHED_VERIFIED")

    def test_12_missing_tracking_parameters(self):
        probs = tracking.validate_link("https://shop.example.com/l/cash", platform="x", offer_url="https://shop.example.com/l/cash", offer_id="P-001")
        self.assertEqual(sorted(probs), sorted(f"missing {k}" for k in tracking.UTM_KEYS))
        o = product()
        d = self.draft(o, "x")
        d["fields"]["text"] = d["fields"]["text"].replace(d["link"], "https://shop.example.com/l/cash")
        self.assertIn("tracked link missing from the post text", content.qa(d, o)["issues"])

    def test_13_wrong_product_to_campaign_mapping(self):
        o = product()
        d = self.draft(o, "linkedin", campaign=tracking.campaign_id("OTHER-9"))
        self.assertTrue(any("does not belong to offer" in i for i in d["qa"]["issues"]))

    def test_14_unauthorized_publication(self):
        o = product()
        j = self.jobs.add_draft(self.draft(o))
        with self.assertRaises(campaigns.Refused):
            self.jobs.publish(j, o)                                     # not approved
        with self.assertRaises(campaigns.Refused):
            self.jobs.approve(j, approver="founder", evidence="ok")     # weak evidence
        self.jobs.approve(j, approver="founder", evidence="approved in review 2026-10-23")
        self.jobs.queue(j)
        with self.assertRaises(campaigns.Refused):
            self.jobs.publish(j, o)                                     # factory switch off
        self.assertEqual(self.jobs.job(j)["state"], "BLOCKED")
        self.assertEqual(self.t.calls, [])

    def test_15_analytics_must_be_real_and_separate(self):
        real, sim = self.td / "m.jsonl", self.td / "m.simulation.jsonl"
        with self.assertRaises(tracking.TrackingError):
            tracking.record_metric(environment="REAL", campaign="c", platform="x", metric="impressions", value=100,
                                   evidence_class="OBSERVED", source="", evidence=None, method="api", ledger=real)
        with self.assertRaises(tracking.TrackingError):
            tracking.record_metric(environment="REAL", campaign="c", platform="x", metric="impressions", value=5,
                                   evidence_class="UNKNOWN", source="x", evidence=None, method="none", ledger=real)
        with self.assertRaises(tracking.TrackingError):
            tracking.record_metric(environment="SIMULATION", campaign="c", platform="x", metric="purchases", value=1,
                                   evidence_class="OBSERVED", source="sim", evidence="synthetic", method="sim", ledger=real)
        tracking.record_metric(environment="SIMULATION", campaign="c", platform="x", metric="purchases", value=1,
                               evidence_class="OBSERVED", source="sim", evidence="synthetic fixture", method="sim", ledger=sim)
        self.assertFalse(real.exists())
        dash = dashboard.build({"offers": [], "summary": offers.summary([])}, [], {}, tracking.read_metrics(sim))
        self.assertEqual(dash["commercial"]["metrics"], "NO REAL METRICS RECORDED")
        self.assertEqual(dash["commercial"]["verified_revenue_cents"], 0)

    def test_16_price_or_destination_changed_after_approval(self):
        o = product()
        j = self.approved(o)
        changed = dict(o, price_cents=2900)
        with self.live(), self.assertRaises(campaigns.Refused):
            self.jobs.publish(j, changed)
        self.assertEqual(self.jobs.job(j)["state"], "STALE")
        self.assertEqual(self.t.calls, [])

    def test_17_rights_and_policy_review(self):
        o = product()
        d = self.draft(o)
        self.assertTrue(d["qa"]["passed"], d["qa"]["issues"])          # the listing's own disclaimer is fine
        d["fields"]["text"] += " Guaranteed results, trusted by thousands."
        issues = content.qa(d, o)["issues"]
        self.assertTrue(any("guaranteed" in i for i in issues))
        self.assertTrue(any("trusted by" in i for i in issues))
        g = guide("A real guide for UNKNOWN -- not captured at this granularity in the source registry.")
        self.assertTrue(any("data-gap" in i for i in content.draft(g, "x", campaign="gf-site-guide-scope-202610")["qa"]["issues"]))
        v = {"offer_id": "VID-a", "type": "media_asset", "description": "supports P-001", "media_path": "v.mp4", "rights_status": "UNRESOLVED"}
        t = content.draft(o, "tiktok", campaign=tracking.campaign_id("P-001"), offers=[v])
        self.assertIn("video rights UNRESOLVED", t["qa"]["issues"])

    def test_18_interrupted_campaign_recovers_safely(self):
        o = product()
        j = self.approved(o)
        self.jobs._append(j, "PUBLISHING", attempts=1)                 # process died here
        with self.live(), self.assertRaises(campaigns.Refused):
            self.jobs.publish(j, o)
        self.assertEqual(self.jobs.job(j)["state"], "NEEDS_RECONCILIATION")
        self.assertEqual(self.t.calls, [])


class TestSafety(Base):
    def test_default_adapters_never_reach_a_network(self):
        jobs = campaigns.Jobs(ledger=self.td / "j2.jsonl", handoff_dir=self.td / "h2",
                              adapters={"linkedin": campaigns.Adapter("linkedin", readiness=dict(READY))})
        o = product()
        j = jobs.add_draft(self.draft(o))
        jobs.approve(j, approver="founder", evidence="approved in review 2026-10-23")
        r = jobs.queue(j)                                               # no transport: manual hand-off
        self.assertEqual(r["state"], "HANDOFF_READY")
        self.assertIn(self.draft(o)["link"], Path(r["handoff"]).read_text(encoding="utf-8"))
        with self.live(), self.assertRaises(campaigns.Refused):
            jobs.publish(j, o)                                          # hand-off jobs are not API-publishable
        jobs.record_manual_post(j, post_url="https://www.linkedin.com/feed/update/x", posted_by="founder")
        self.assertEqual(jobs.job(j)["state"], "MANUAL_POSTED_UNVERIFIED")

    def test_x_spend_block(self):
        a = campaigns.Adapter("x", transport=self.t, readiness=dict(READY, state=platforms.BLOCKED_SPEND))
        with self.assertRaises(campaigns.SpendRequired):
            a.publish({})
        self.assertEqual(self.t.calls, [])
        r = platforms.readiness(env_names={"X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"}, root=ROOT)
        self.assertEqual(r["x"]["state"], platforms.BLOCKED_SPEND)      # data/x_post_queue.json holds the 402
        self.assertEqual(r["linkedin"]["state"], platforms.NOT_CONNECTED)

    def test_package_has_no_network_client(self):
        for f in (ROOT / "social_distribution").glob("*.py"):
            src = f.read_text(encoding="utf-8")
            for needle in ("import requests", "urllib.request", "http.client", "urlopen("):
                self.assertNotIn(needle, src, f"{f.name} contains {needle}")

    def test_secrets_redacted_in_ledger(self):
        o = product()
        self.t.fail = [campaigns.PermissionDenied("401 Bearer ya29.a0AfH6SMBxxxxxxxxxxxxxxxxxxxxxx")]
        j = self.approved(o)
        with self.live():
            self.jobs.publish(j, o)
        self.assertNotIn("ya29.", self.jobs.ledger.read_text(encoding="utf-8"))


class TestRegressions(unittest.TestCase):
    def test_x_post_never_exceeds_280_with_long_title(self):
        a = rep.Asset(title="T" * 120, description="Sentence one is here. " * 20, price_usd=69,
                      url="https://shop.example.com/l/" + "x" * 80, status="live")
        self.assertLessEqual(rep.x_weighted_length(rep.x_post(a)["text"]), 280)

    def test_live_listing_not_called_a_validation_concept(self):
        a = rep.Asset(title="T", description="A thing.", price_usd=9, url="https://x.example/l", status="live")
        self.assertNotIn("validation concept", rep.linkedin_post(a)["body"])
        self.assertIn("validation concept", rep.linkedin_post(rep.Asset(title="T", description="A thing."))["body"])

    def test_while_is_not_a_pain_marker(self):
        a = rep.Asset(title="T", description="Profitable on paper while payroll lands first.")
        self.assertFalse(rep.short_video_script(a)["hook"].startswith("Stop payroll"))

    def test_html_lists_keep_their_lines(self):
        self.assertIn("\n- Weekly view", offers.plain(DESC))

    def test_product_page_for_unlisted_product_is_not_eligible(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        (root / "customer_site").mkdir()
        page = '<title>{t} | Galaxy Forge</title><meta name="description" content="A useful workbook for a real job.">'
        (root / "customer_site" / "b12-a.html").write_text(page.format(t="Widget Planner — $19 (proposed)"), encoding="utf-8")
        (root / "customer_site" / "b12-b.html").write_text(page.format(t="Cash Flow Forecast — $19 (approved, not yet listed)"), encoding="utf-8")
        got = {o["offer_id"]: o["eligibility"] for o in offers.site_offers(root, {"b12-a.html", "b12-b.html"}, registry())}
        self.assertEqual(got["SITE-b12-a"]["status"], "NOT_ELIGIBLE")
        self.assertEqual(got["SITE-b12-b"]["status"], "NEEDS_REVIEW")    # live product, stale page
        self.assertIn("page is stale", got["SITE-b12-b"]["reasons"][0])

    def test_plan_spreads_across_arms_and_requires_a_usable_draft(self):
        os_ = [dict(product(iid=f"P-{i}"), offer_id=f"P-{i}") for i in range(5)] + [guide()]
        picked = prioritize.plan(os_, n=4, per_arm=2)
        self.assertEqual(sum(1 for p in picked if p["arm"] == "digital_products"), 2)
        self.assertIn("SITE-guide-scope", [p["offer_id"] for p in picked])
        self.assertEqual(prioritize.plan(os_, accept=lambda oid: False), [])
        s = prioritize.score(os_[0])
        self.assertEqual(s["factors"]["demand_evidence"], 0)
        self.assertTrue(any("demand evidence" in u for u in s["uncertainty"]))

    def test_listing_amounts_in_nested_fields_are_not_flagged(self):
        o = product()
        o["description"] = "Attorneys charge $1,000 to file one class. " * 3
        o["problem"] = offers.first_sentence(o["description"])
        v = {"offer_id": "VID-a", "type": "media_asset", "description": "supports P-001", "media_path": "v.mp4", "rights_status": "CLEARED"}
        d = content.draft(o, "tiktok", campaign=tracking.campaign_id("P-001"), offers=[v])
        self.assertFalse([i for i in d["qa"]["issues"] if "amount" in i], d["qa"]["issues"])
        d["fields"]["script"]["hook"] += " Pay $1,000 today."           # an amount a template added is still caught
        self.assertTrue(any("$1,000" in i for i in content.qa(d, o)["issues"]))

    def test_cut_listing_text_after_the_title_is_still_listing_text(self):
        o = product()
        o["description"] = ("Typical settlements run $5K to $20K before legal fees, and most defendants are small "
                            "businesses that " + "never expected a letter, " * 12 + "so this kit organizes the first 30 days.")
        d = content.draft(o, "x", campaign=tracking.campaign_id("P-001"))
        self.assertIn("…", d["fields"]["text"])
        self.assertTrue(d["qa"]["passed"], d["qa"]["issues"])

    def test_product_page_carries_its_live_products_price(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        (root / "customer_site").mkdir()
        (root / "customer_site" / "b12-c.html").write_text(
            '<title>Cash Flow Forecast — $19.00 | Galaxy Forge</title><meta name="description" content="A useful workbook.">',
            encoding="utf-8")
        o = offers.site_offers(root, {"b12-c.html"}, registry())[0]
        self.assertEqual((o["price_cents"], o["linked_product"], o["title"]), (1900, "P-001", "Cash Flow Forecast — $19.00"))
        o["platforms"] = ["linkedin", "x"]
        o["language"] = "en"
        d = content.draft(o, "x", campaign=tracking.campaign_id(o["offer_id"]))
        self.assertTrue(d["qa"]["passed"], d["qa"]["issues"])

    def test_qa_issues_kept_as_a_list(self):
        td = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, td, ignore_errors=True)
        jobs = campaigns.Jobs(ledger=td / "j.jsonl", handoff_dir=td / "h")
        o = product()
        j = jobs.add_draft(content.draft(o, "instagram", campaign=tracking.campaign_id("P-001")))
        dash = dashboard.build({"offers": [], "summary": offers.summary([])}, jobs.jobs(), {})
        self.assertIn("Instagram needs rendered JPEG images; only slide text exists", dash["operational"]["qa_failure_reasons"])
        self.assertEqual(jobs.job(j)["state"], "QA_FAILED")

    def test_purchases_attributed_once_and_never_guessed(self):
        r = tracking.attribute_purchases([
            {"purchase_id": "a", "referrer": "https://x.com/?utm_campaign=gf-p-001-202610"},
            {"purchase_id": "a", "referrer": "https://x.com/?utm_campaign=gf-p-001-202610"},
            {"purchase_id": "b", "referrer": "https://google.com"}])
        self.assertEqual(r["by_campaign"], {"gf-p-001-202610": 1})
        self.assertEqual(r["unattributed"], 1)


if __name__ == "__main__":
    unittest.main()
