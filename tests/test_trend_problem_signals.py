"""Customer-problem signals from Stack Exchange (backlog B32, 2026-10-29).

The network is replaced by a fake fetch; every write goes to a temp directory.
"""
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import trend_problem_signals as tps  # noqa: E402
from trend_to_product import records, scoring  # noqa: E402

NOW = datetime(2026, 10, 29, tzinfo=timezone.utc)


def item(qid, title, views=100, answers=1):
    return {"question_id": qid, "title": title, "view_count": views, "answer_count": answers,
            "link": f"https://crafts.stackexchange.com/q/{qid}", "creation_date": 1760000000}


class FakeFetch:
    def __init__(self, by_site, extra=None):
        self.by_site, self.extra, self.urls = by_site, extra or {}, []

    def __call__(self, url):
        self.urls.append(url)
        site = url.split("site=")[1].split("&")[0]
        d = {"items": self.by_site.get(site, []), "quota_remaining": 250}
        d.update(self.extra)
        return d


class ProblemSignals(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def run_(self, fetch, **kw):
        return tps.run(now=NOW, fetch=fetch, sleep=lambda s: None, base_dir=self.d, **kw)

    def test_records_sources_and_one_signal_per_topic(self):
        f = FakeFetch({"crafts": [item(1, "How do I read this crochet pattern chart?", 900),
                                  item(2, "What does this pattern mean in crochet &amp; how to follow it", 50),
                                  item(3, "Best glue for wood", 10)]})
        r = self.run_(f)
        self.assertEqual("ran", r["action"])
        srcs = records.read_jsonl("sources.jsonl", self.d)
        self.assertTrue(all(s["access_method"] == "PUBLIC_API_KEYLESS" for s in srcs))
        self.assertTrue(all(s["source_type"] == "ANECDOTAL" and s["permitted_use"] == "SIGNAL_ONLY" for s in srcs))
        sig = records.signals_for(topic="crochet_patterns", base_dir=self.d)[0]
        self.assertEqual("CUSTOMER_PROBLEM", sig["signal_type"])
        self.assertEqual(2, sig["value"]["question_count"])          # the glue question does not match
        self.assertEqual("What does this pattern mean in crochet & how to follow it",
                         sig["value"]["sample"][1]["title"])
        self.assertFalse(sig["counts_as_sales_evidence"])

    def test_topic_without_questions_gets_no_signal(self):
        r = self.run_(FakeFetch({}))
        self.assertTrue(all(v == 0 for v in r["topics"].values()))
        self.assertEqual([], records.read_jsonl("signals.jsonl", self.d))

    def test_backoff_stops_further_calls(self):
        f = FakeFetch({"crafts": [item(1, "crochet pattern row")]}, extra={"backoff": 10})
        r = self.run_(f)
        self.assertEqual(1, len(f.urls))
        self.assertIn("backoff", r["stopped"])

    def test_low_quota_stops(self):
        f = FakeFetch({}, extra={"quota_remaining": 10})
        r = self.run_(f)
        self.assertEqual(1, len(f.urls))
        self.assertIn("quota", r["stopped"])

    def test_fetch_error_is_recorded_not_raised(self):
        def boom(url):
            raise OSError("down")
        r = self.run_(boom)
        self.assertEqual("ran", r["action"])
        self.assertEqual([], records.read_jsonl("sources.jsonl", self.d))

    def test_if_due_guard(self):
        self.run_(FakeFetch({}))
        r = self.run_(FakeFetch({}), if_due=True)
        self.assertEqual("none", r["action"])

    def test_rescore_adds_signal_and_scores_severity(self):
        f = FakeFetch({"crafts": [item(i, f"crochet pattern row {i}") for i in range(12)]})
        scoring.record_opportunity("Patterns", "crochet_patterns", "craft_pattern", [], base_dir=self.d)
        r = self.run_(f)
        self.assertEqual(1, len(r["rescored"]))
        o = [o for o in scoring.latest_opportunities(self.d) if o["name"] == "Patterns"][0]
        self.assertEqual(3, o["dimensions"]["problem_severity"]["score"])   # 12 questions -> band 10-29
        self.assertEqual(1, len(o["signal_ids"]))
        # A second run supersedes, not stacks, the topic's problem signal.
        f2 = FakeFetch({"crafts": [item(i, f"crochet pattern row {i}") for i in range(40)]})
        tps.run(now=datetime(2026, 11, 9, tzinfo=timezone.utc), fetch=f2, sleep=lambda s: None, base_dir=self.d)
        o = [o for o in scoring.latest_opportunities(self.d) if o["name"] == "Patterns"][0]
        self.assertEqual(1, len(o["signal_ids"]))
        self.assertEqual(4, o["dimensions"]["problem_severity"]["score"])

    def test_loose_matches_from_first_live_run_are_rejected(self):
        # Real titles the first (substring) version counted on 2026-10-29.
        noise = {"maker_pricing": "(Drawing on iPad) Do they sell artist gloves that cover all 5 fingers?",
                 "reading_journals": 'Meaning of "with no why to how it keeps its mystery"',
                 "printable_miniatures": "How do you paint a plastic miniature to look like polished mahogany?",
                 "craft_planners": "Tips for working with yarn that splits easily?"}
        for topic, title in noise.items():
            for site, q, groups in tps.QUERIES[topic]:
                self.assertFalse(tps._matches(title, groups), (topic, title))
        self.assertTrue(tps._matches("What does this pattern mean in crochet?",
                                     tps.QUERIES["crochet_patterns"][0][2]))

    def test_zero_questions_removes_previous_problem_signal(self):
        f = FakeFetch({"crafts": [item(i, f"crochet pattern row {i}") for i in range(5)]})
        scoring.record_opportunity("Patterns", "crochet_patterns", "craft_pattern", [], base_dir=self.d)
        self.run_(f)
        tps.run(now=datetime(2026, 11, 9, tzinfo=timezone.utc), fetch=FakeFetch({}), sleep=lambda s: None,
                base_dir=self.d)
        o = [o for o in scoring.latest_opportunities(self.d) if o["name"] == "Patterns"][0]
        self.assertEqual([], o["signal_ids"])
        self.assertIsNone(o["dimensions"]["problem_severity"]["score"])

    def test_failed_query_keeps_previous_signals(self):
        f = FakeFetch({"crafts": [item(i, f"crochet pattern row {i}") for i in range(5)]})
        scoring.record_opportunity("Patterns", "crochet_patterns", "craft_pattern", [], base_dir=self.d)
        self.run_(f)

        def boom(url):
            raise OSError("down")
        tps.run(now=datetime(2026, 11, 9, tzinfo=timezone.utc), fetch=boom, sleep=lambda s: None,
                base_dir=self.d)
        o = [o for o in scoring.latest_opportunities(self.d) if o["name"] == "Patterns"][0]
        self.assertEqual(1, len(o["signal_ids"]))

    def test_live_paths_untouched(self):
        self.run_(FakeFetch({}))
        self.assertTrue(os.path.exists(os.path.join(self.d, "problem_signals_run.json")))


if __name__ == "__main__":
    unittest.main()
