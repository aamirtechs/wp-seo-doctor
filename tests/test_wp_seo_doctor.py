"""Tests for wp_seo_doctor."""

import json
import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

import wp_seo_doctor as wsd

AS_OF = date(2026, 11, 15)


def options(**overrides):
    """Audit options, with clean defaults."""
    base = {
        "max_title": 60,
        "min_title": 30,
        "max_description": 160,
        "min_description": 50,
        "min_words": 150,
        "max_url": 115,
        "stale_days": 365,
        "as_of": AS_OF,
        "has_keyword_column": True,
    }
    base.update(overrides)
    return base


def row(**overrides):
    """One page row, with clean defaults."""
    base = {"url": "/about-us/",
            "title": "About Our Company and Our Story",
            "meta_description": "Learn who we are, how Example "
                                "Store started, and why customers "
                                "trust us.",
            "h1": "About Example Store",
            "h1_count": "1",
            "word_count": "380",
            "status": "index",
            "canonical": "https://example.com/about-us/",
            "focus_keyword": "about our company",
            "content_type": "page",
            "last_modified": "2026-09-15"}
    base.update(overrides)
    return base


def codes(findings, rule=None):
    """Finding rules, optionally filtered to one rule."""
    return [f.rule for f in findings
            if rule is None or f.rule == rule]


def run(rows, **overrides):
    """Audit rows and return (findings, report, summary)."""
    findings, report = wsd.audit(rows, options(**overrides))
    return findings, report, wsd.summarize(findings, report)


class TestParseHelpers(unittest.TestCase):
    def test_parse_int_strips_commas(self):
        self.assertEqual(wsd.parse_int("1,200", "x", "words"), 1200)

    def test_parse_int_blank_is_none(self):
        self.assertIsNone(wsd.parse_int("", "x", "words"))
        self.assertIsNone(wsd.parse_int(None, "x", "words"))

    def test_parse_int_rejects_text(self):
        with self.assertRaises(ValueError):
            wsd.parse_int("many", "x", "words")

    def test_parse_date_valid(self):
        self.assertEqual(wsd.parse_date("2026-09-15", "x", "date"),
                         date(2026, 9, 15))

    def test_parse_date_blank_is_none(self):
        self.assertIsNone(wsd.parse_date("", "x", "date"))

    def test_parse_date_rejects_other_formats(self):
        with self.assertRaises(ValueError):
            wsd.parse_date("15/09/2026", "x", "date")

    def test_normalise_url_strips_trailing_slash(self):
        self.assertEqual(wsd.normalise_url("/About/"), "/about")
        self.assertEqual(wsd.normalise_url("/"), "/")

    def test_normalise_header(self):
        self.assertEqual(wsd.normalise_header("Meta Description 1"),
                         "metadescription1")
        self.assertEqual(wsd.normalise_header("Word Count"),
                         "wordcount")


class TestCleanRow(unittest.TestCase):
    def test_clean_row_has_no_findings(self):
        findings, report, summary = run([row()])
        self.assertEqual(findings, [])
        self.assertEqual(summary["pages"], 1)
        self.assertEqual(summary["errors"], 0)
        self.assertEqual(summary["warnings"], 0)

    def test_blank_status_defaults_to_index(self):
        findings, _, _ = run([row(status="")])
        self.assertEqual(findings, [])

    def test_noindex_without_canonical_is_clean(self):
        findings, _, _ = run([row(status="noindex", canonical="")])
        self.assertEqual(findings, [])

    def test_title_at_exact_limits_is_clean(self):
        findings, _, _ = run([row(title="x" * 60)])
        self.assertNotIn("long-title", codes(findings))
        findings, _, _ = run([row(title="x" * 30,
                                  focus_keyword="")])
        self.assertNotIn("short-title", codes(findings))

    def test_description_at_exact_limits_is_clean(self):
        findings, _, _ = run([row(meta_description="x" * 160)])
        self.assertNotIn("long-meta-description", codes(findings))
        findings, _, _ = run([row(meta_description="x" * 50)])
        self.assertNotIn("short-meta-description",
                         codes(findings))

    def test_word_count_at_minimum_is_clean(self):
        findings, _, _ = run([row(word_count="150")])
        self.assertNotIn("thin-content", codes(findings))


class TestErrors(unittest.TestCase):
    def test_missing_url(self):
        findings, _, summary = run([row(url="")])
        self.assertIn("missing-url", codes(findings))
        self.assertEqual(summary["errors"], 1)

    def test_invalid_url(self):
        findings, _, _ = run([row(url="about-us")])
        self.assertIn("invalid-url", codes(findings))
        findings, _, _ = run([row(url="https://example.com/x")])
        self.assertNotIn("invalid-url", codes(findings))

    def test_duplicate_url_case_and_slash_insensitive(self):
        rows = [row(), row(url="/ABOUT-US")]
        findings, _, _ = run(rows)
        self.assertIn("duplicate-url", codes(findings))

    def test_missing_title(self):
        findings, _, _ = run([row(title="")])
        self.assertIn("missing-title", codes(findings))

    def test_missing_meta_description(self):
        findings, _, _ = run([row(meta_description="")])
        self.assertIn("missing-meta-description", codes(findings))

    def test_duplicate_title_case_insensitive(self):
        rows = [row(), row(url="/other/",
                           title="ABOUT OUR COMPANY AND OUR STORY")]
        findings, _, _ = run(rows)
        self.assertIn("duplicate-title", codes(findings))

    def test_duplicate_meta_description(self):
        rows = [row(), row(url="/other/")]
        findings, _, _ = run(rows)
        self.assertIn("duplicate-meta-description", codes(findings))

    def test_missing_h1(self):
        findings, _, _ = run([row(h1="")])
        self.assertIn("missing-h1", codes(findings))

    def test_multiple_h1(self):
        findings, _, _ = run([row(h1_count="3")])
        self.assertIn("multiple-h1", codes(findings))

    def test_invalid_h1_count(self):
        findings, _, _ = run([row(h1_count="two")])
        self.assertIn("invalid-h1-count", codes(findings))

    def test_invalid_word_count(self):
        findings, _, _ = run([row(word_count="many")])
        self.assertIn("invalid-word-count", codes(findings))

    def test_negative_word_count(self):
        findings, _, _ = run([row(word_count="-5")])
        self.assertIn("invalid-word-count", codes(findings))

    def test_invalid_status(self):
        findings, _, _ = run([row(status="maybe")])
        self.assertIn("invalid-status", codes(findings))

    def test_invalid_date(self):
        findings, _, _ = run([row(last_modified="15 Sep 2026")])
        self.assertIn("invalid-date", codes(findings))

    def test_future_date(self):
        findings, _, _ = run([row(last_modified="2027-01-01")])
        self.assertIn("future-date", codes(findings))


class TestWarnings(unittest.TestCase):
    def test_long_title(self):
        findings, _, _ = run([row(title="x" * 61)])
        self.assertIn("long-title", codes(findings))

    def test_short_title(self):
        findings, _, _ = run([row(title="About Us",
                                  focus_keyword="about")])
        self.assertIn("short-title", codes(findings))

    def test_long_meta_description(self):
        findings, _, _ = run([row(meta_description="x" * 161)])
        self.assertIn("long-meta-description", codes(findings))

    def test_short_meta_description(self):
        findings, _, _ = run([row(meta_description="Too short.")])
        self.assertIn("short-meta-description", codes(findings))

    def test_thin_content(self):
        findings, _, _ = run([row(word_count="149")])
        self.assertIn("thin-content", codes(findings))

    def test_h1_same_as_title(self):
        findings, _, _ = run([row(h1="About Our Company and "
                                   "Our Story")])
        self.assertIn("h1-same-as-title", codes(findings))

    def test_missing_canonical(self):
        findings, _, _ = run([row(canonical="")])
        self.assertIn("missing-canonical", codes(findings))

    def test_missing_focus_keyword(self):
        findings, _, _ = run([row(focus_keyword="")])
        self.assertIn("missing-focus-keyword", codes(findings))

    def test_keyword_not_in_title(self):
        findings, _, _ = run([row(focus_keyword="pricing")])
        self.assertIn("keyword-not-in-title", codes(findings))

    def test_keyword_check_skipped_without_column(self):
        findings, _, _ = run([row(focus_keyword="pricing")],
                             has_keyword_column=False)
        self.assertNotIn("keyword-not-in-title", codes(findings))
        self.assertNotIn("missing-focus-keyword", codes(findings))

    def test_long_url(self):
        findings, _, _ = run([row(url="/" + "a" * 120)])
        self.assertIn("long-url", codes(findings))

    def test_url_at_max_length_is_clean(self):
        findings, _, _ = run([row(url="/" + "a" * 114)])
        self.assertNotIn("long-url", codes(findings))

    def test_stale_content(self):
        findings, _, _ = run([row(last_modified="2025-11-14")])
        self.assertIn("stale-content", codes(findings))

    def test_recent_content_not_stale(self):
        findings, _, _ = run([row(last_modified="2025-11-15")])
        self.assertNotIn("stale-content", codes(findings))

    def test_thresholds_are_overridable(self):
        findings, _, _ = run([row(title="x" * 61)], max_title=100)
        self.assertNotIn("long-title", codes(findings))
        findings, _, _ = run([row(word_count="100")], min_words=50)
        self.assertNotIn("thin-content", codes(findings))


class TestReport(unittest.TestCase):
    def test_by_type_and_status_tables(self):
        rows = [row(), row(url="/blog/one/",
                           title="Blog Post One With a Long Title",
                           focus_keyword="blog post one",
                           content_type="post",
                           status="noindex")]
        findings, report, summary = run(rows)
        types = {e["type"]: e["count"] for e in report["by_type"]}
        self.assertEqual(types, {"page": 1, "post": 1})
        statuses = {e["status"]: e["count"]
                    for e in report["by_status"]}
        self.assertEqual(statuses, {"index": 1, "noindex": 1})
        self.assertEqual(summary["pages"], 2)

    def test_summary_counts(self):
        rows = [row(title=""), row(url="/other/",
                     meta_description="")]
        _, _, summary = run(rows)
        self.assertEqual(summary["findings"], 2)
        self.assertEqual(summary["errors"], 2)
        self.assertEqual(summary["warnings"], 0)

    def test_text_format(self):
        findings, report, summary = run([row(title="")])
        text = wsd.format_text(findings, report, summary)
        self.assertIn("ERROR [missing-title] /about-us/:", text)
        self.assertIn("Pages: 1, findings: 1, errors: 1, "
                      "warnings: 0", text)

    def test_text_format_clean(self):
        findings, report, summary = run([row()])
        text = wsd.format_text(findings, report, summary)
        self.assertIn("All pages clean.", text)

    def test_json_format(self):
        findings, report, summary = run([row(title="")])
        payload = json.loads(wsd.format_json(findings, report,
                                             summary))
        self.assertEqual(payload["summary"]["errors"], 1)
        self.assertEqual(payload["findings"][0]["rule"],
                         "missing-title")
        self.assertEqual(payload["findings"][0]["severity"],
                         "error")


class TestFileHandling(unittest.TestCase):
    def write_csv(self, text):
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".csv", delete=False, encoding="utf-8")
        handle.write(text)
        handle.close()
        return handle.name

    def test_read_csv_header_aliases(self):
        path = self.write_csv(
            "Address,Title 1,Meta Description 1,H1-1,Word Count\n"
            "/x,About Our Company and Our Story,"
            "Learn who we are and how we started.,About Us,300\n")
        try:
            rows = wsd.read_csv(path)
            self.assertEqual(rows[0]["url"], "/x")
            self.assertEqual(rows[0]["title"],
                             "About Our Company and Our Story")
            self.assertEqual(rows[0]["word_count"], "300")
        finally:
            os.unlink(path)

    def test_read_csv_handles_bom(self):
        path = self.write_csv(
            "url,title,meta_description,h1,h1_count,word_count,"
            "status,canonical,focus_keyword,content_type,"
            "last_modified\n"
            "/x,About Our Company and Our Story,"
            "Learn who we are and how we started.,About Us,1,300,"
            "index,https://example.com/x,about,page,2026-09-15\n")
        try:
            with open(path, "rb") as handle:
                raw = handle.read()
            with open(path, "wb") as handle:
                handle.write(b"\xef\xbb\xbf" + raw)
            rows = wsd.read_csv(path)
            self.assertEqual(rows[0]["url"], "/x")
        finally:
            os.unlink(path)

    def test_main_missing_file_exits_2(self):
        self.assertEqual(wsd.main(["/no/such/file.csv"]), 2)

    def test_main_missing_url_column_exits_2(self):
        path = self.write_csv("title,word_count\nHello,100\n")
        try:
            self.assertEqual(wsd.main([path]), 2)
        finally:
            os.unlink(path)

    def test_main_check_exits_1_on_error(self):
        path = self.write_csv(
            "url,title,meta_description,h1,h1_count,word_count,"
            "status,canonical,focus_keyword,content_type,"
            "last_modified\n"
            "/x,,A fine description of the page.,About Us,1,300,"
            "index,https://example.com/x,about,page,2026-09-15\n")
        try:
            self.assertEqual(
                wsd.main([path, "--check", "--as-of",
                          "2026-11-15"]), 1)
        finally:
            os.unlink(path)

    def test_main_check_passes_on_warnings_only(self):
        path = self.write_csv(
            "url,title,meta_description,h1,h1_count,word_count,"
            "status,canonical,focus_keyword,content_type,"
            "last_modified\n"
            "/x,About Our Company and Our Story,"
            "Learn who we are and how we started.,About Us,1,100,"
            "index,https://example.com/x,about,page,2026-09-15\n")
        try:
            self.assertEqual(
                wsd.main([path, "--check", "--as-of",
                          "2026-11-15"]), 0)
            self.assertEqual(
                wsd.main([path, "--check", "--strict", "--as-of",
                          "2026-11-15"]), 1)
        finally:
            os.unlink(path)

    def test_main_json_output(self):
        path = self.write_csv(
            "url,title,meta_description,h1,h1_count,word_count,"
            "status,canonical,focus_keyword,content_type,"
            "last_modified\n"
            "/x,,A fine description of the page.,About Us,1,300,"
            "index,https://example.com/x,about,page,2026-09-15\n")
        try:
            with tempfile.NamedTemporaryFile(
                    "w", suffix=".json", delete=False) as out:
                out_path = out.name
            code = wsd.main([path, "--json", "--out", out_path,
                             "--as-of", "2026-11-15"])
            self.assertEqual(code, 0)
            with open(out_path, encoding="utf-8") as handle:
                payload = json.load(handle)
            self.assertEqual(payload["summary"]["errors"], 1)
        finally:
            os.unlink(path)
            os.unlink(out_path)


class TestSampleFiles(unittest.TestCase):
    def sample_path(self, name):
        return os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "examples", name)

    def test_sample_counts(self):
        rows = wsd.read_csv(self.sample_path("pages.csv"))
        findings, report, summary = run(rows)
        self.assertEqual(summary["pages"], 14)
        self.assertEqual(summary["findings"], 35)
        self.assertEqual(summary["errors"], 11)
        self.assertEqual(summary["warnings"], 24)

    def test_clean_sample_is_clean(self):
        rows = wsd.read_csv(self.sample_path("clean.csv"))
        findings, _, summary = run(rows)
        self.assertEqual(summary["findings"], 0)

    def test_warnings_sample_has_no_errors(self):
        rows = wsd.read_csv(self.sample_path("warnings.csv"))
        findings, _, summary = run(rows)
        self.assertEqual(summary["errors"], 0)
        self.assertEqual(summary["warnings"], 8)


if __name__ == "__main__":
    unittest.main()
