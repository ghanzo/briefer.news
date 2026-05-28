#!/usr/bin/env python3
"""Regression tests for scripts/brief_parser.py against frozen renders of both
editions. Stdlib unittest only — runs on the host with no venv:

    python3 -m unittest tests.test_brief_parser -v
    python3 tests/test_brief_parser.py

The fixtures are real 2026-05-28 renders (post the 2026-05-27 dek-removal /
progressive-disclosure change). They pin the CURRENT contract so the next
structural change to the brief breaks here loudly instead of silently in the
~12 downstream consumers.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from brief_parser import parse_file  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures"
USA = FIX / "brief_usa_2026-05-28.html"
CHINA = FIX / "brief_china_2026-05-28.html"


class BriefParserContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.usa = parse_file(USA)
        cls.china = parse_file(CHINA)

    def test_event_tiers(self):
        for d in (self.usa, self.china):
            self.assertEqual(d["events_visible_count"], 5)
            self.assertEqual(d["events_more_count"], 4)
            self.assertEqual(sum(e["tier"] == "week" for e in d["events"]), 5)

    def test_allied_is_usa_only(self):
        self.assertEqual(sum(e["tier"] == "allied" for e in self.usa["events"]), 3)
        self.assertEqual(sum(e["tier"] == "allied" for e in self.china["events"]), 0)
        self.assertTrue(self.usa["has_allied"])
        self.assertFalse(self.china["has_allied"])

    def test_voices(self):
        for d in (self.usa, self.china):
            self.assertEqual(len(d["voices"]), 6)
            for v in d["voices"]:
                self.assertTrue(v["quote"])
                self.assertTrue(v["speaker"])

    def test_meta_description_survived_dek_removal(self):
        # The 2026-05-27 change removed the on-page dek, NOT the SEO meta desc.
        for d in (self.usa, self.china):
            self.assertTrue(d["meta_description"])
            self.assertIsNone(d["dek"])

    def test_citations_resolve(self):
        # Regression guard for the cite-marker bug: every visible event and
        # every voice must carry a citation marker + url.
        for d in (self.usa, self.china):
            for e in (x for x in d["events"] if x["tier"] in ("visible", "more")):
                self.assertTrue(e["cite_marker"], f"missing cite_marker: {e['lead'][:40]}")
                self.assertTrue(e["cite_url"], f"missing cite_url: {e['lead'][:40]}")
            for v in d["voices"]:
                self.assertTrue(v["cite_marker"])

    def test_sources(self):
        for d in (self.usa, self.china):
            self.assertTrue(d["sources"])
            for s in d["sources"]:
                self.assertTrue(s["publisher"])
                self.assertTrue(s["url"])
        # USA carries the lettered allied sublist; China does not.
        self.assertIn("a", [s["marker"] for s in self.usa["sources"]])
        self.assertNotIn("a", [s["marker"] for s in self.china["sources"]])

    def test_head_fields(self):
        self.assertEqual(self.usa["canonical"], "https://briefer.news/usa/")
        self.assertEqual(self.china["canonical"], "https://briefer.news/china/")
        for d in (self.usa, self.china):
            self.assertTrue(d["date"])
            self.assertTrue(d["headline"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
