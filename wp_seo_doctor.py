"""WordPress SEO audit CLI.

Reads a CSV export of WordPress pages and posts (URL, title, meta
description, H1, word count, index status, canonical URL, focus
keyword, content type, last modified date) and audits every page
for the on-page SEO mistakes that cost clicks and rankings:
missing titles and meta descriptions, duplicate titles and
descriptions, missing or repeated H1s, thin content, titles and
descriptions outside the length that search results show, stale
content, and focus keywords that never appear in the title.

The export format matches what Screaming Frog, Yoast SEO, and
Rank Math produce when they export a site crawl or a post list:
one row per URL with a header row. Snake_case headers work too,
and extra columns are ignored.

Each problem is a finding with a code, a rule name, a severity
(error or warning), and a message. Errors are the ones that leave
a page with no title, no description, no H1, or a duplicate of
another page; warnings are patterns worth fixing. --check exits
1 when any error is found, and --strict also fails on warnings.

Zero dependencies, Python 3.10 or newer, standard library only.

Usage:
    python3 wp_seo_doctor.py examples/pages.csv
    python3 wp_seo_doctor.py pages.csv --json --check --strict
"""

import argparse
import csv
import json
import sys
from datetime import date, datetime

__version__ = "1.0.0"

DEFAULT_MAX_TITLE = 60
DEFAULT_MIN_TITLE = 30
DEFAULT_MAX_DESCRIPTION = 160
DEFAULT_MIN_DESCRIPTION = 50
DEFAULT_MIN_WORDS = 150
DEFAULT_MAX_URL = 115
DEFAULT_STALE_DAYS = 365

VALID_STATUSES = ("index", "noindex")

# Header names, normalised by lowercasing and stripping every
# character that is not a letter or digit, mapped to the field
# this tool uses. Screaming Frog exports "Address", "Title 1",
# "Meta Description 1", "H1-1" and "Word Count"; Yoast and Rank
# Math exports use "URL", "SEO Title", "Meta Description" and
# "Focus Keyword". A hand-built CSV may use the snake_case names
# instead. All of them work.
HEADER_ALIASES = {
    "url": "url",
    "address": "url",
    "title": "title",
    "title1": "title",
    "seotitle": "title",
    "metadescription": "meta_description",
    "metadescription1": "meta_description",
    "description": "meta_description",
    "h1": "h1",
    "h11": "h1",
    "h1count": "h1_count",
    "h1s": "h1_count",
    "wordcount": "word_count",
    "words": "word_count",
    "wordcounttotal": "word_count",
    "status": "status",
    "robots": "status",
    "indexstatus": "status",
    "indexability": "status",
    "canonical": "canonical",
    "canonicallink": "canonical",
    "focuskeyword": "focus_keyword",
    "keyword": "focus_keyword",
    "focuskeyphrase": "focus_keyword",
    "contenttype": "content_type",
    "type": "content_type",
    "posttype": "content_type",
    "lastmodified": "last_modified",
    "modified": "last_modified",
    "date": "last_modified",
    "datemodified": "last_modified",
}


class Finding:
    """One audit finding for one page, URL, or pattern."""

    def __init__(self, code, rule, severity, message):
        self.code = code
        self.rule = rule
        self.severity = severity
        self.message = message

    def as_dict(self):
        """Return the finding as a plain dict."""
        return {"code": self.code, "rule": self.rule,
                "severity": self.severity, "message": self.message}

    def __str__(self):
        return "%s [%s] %s: %s" % (self.severity.upper(), self.rule,
                                   self.code, self.message)


def normalise_header(name):
    """Lowercase a header and strip every non-alphanumeric char."""
    return "".join(ch for ch in str(name).strip().lower()
                   if ch.isalnum())


def normalise_url(url):
    """Normalise a URL for duplicate detection."""
    text = str(url).strip().lower()
    if len(text) > 1 and text.endswith("/"):
        text = text.rstrip("/")
    return text


def parse_int(value, code, field):
    """Parse an integer, or return None when blank.

    Raises ValueError on anything else.
    """
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        raise ValueError("%s is not a whole number: %r" % (field, value))


def parse_date(value, code, field):
    """Parse a YYYY-MM-DD date, or return None when blank.

    Raises ValueError on anything else.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("%s is not a YYYY-MM-DD date: %r"
                         % (field, value))


def audit_row(row, seen_urls, seen_titles, seen_descriptions,
              options):
    """Audit one page row and return its findings."""
    findings = []
    code = row.get("url", "").strip()
    label = code or "(no url)"

    def add(rule, severity, message):
        findings.append(Finding(label, rule, severity, message))

    if not code:
        add("missing-url", "error",
            "row has no URL, so the page cannot be identified")
        return findings

    url_key = normalise_url(code)
    if url_key in seen_urls:
        add("duplicate-url", "error",
            "URL %s is listed more than once" % code)
    else:
        seen_urls.add(url_key)

    if not (code.startswith("/") or code.startswith("http://")
            or code.startswith("https://")):
        add("invalid-url", "error",
            "URL %s does not start with / or http(s)://" % code)

    if len(code) > options["max_url"]:
        add("long-url", "warning",
            "URL is %d characters, above the %d limit, so it may "
            "be truncated in search results" % (len(code),
                                                options["max_url"]))

    title = row.get("title", "").strip()
    if not title:
        add("missing-title", "error",
            "page has no title, so search results show the URL "
            "instead")
    else:
        if len(title) > options["max_title"]:
            add("long-title", "warning",
                "title is %d characters, above the %d limit, so "
                "it will be cut off in search results"
                % (len(title), options["max_title"]))
        elif len(title) < options["min_title"]:
            add("short-title", "warning",
                "title is %d characters, below the %d minimum, so "
                "it says too little in search results"
                % (len(title), options["min_title"]))
        title_key = title.casefold()
        if title_key in seen_titles:
            add("duplicate-title", "error",
                "title %r is used on more than one page" % title)
        else:
            seen_titles.add(title_key)

    description = row.get("meta_description", "").strip()
    if not description:
        add("missing-meta-description", "error",
            "page has no meta description, so search results show "
            "an auto-generated snippet")
    else:
        if len(description) > options["max_description"]:
            add("long-meta-description", "warning",
                "meta description is %d characters, above the %d "
                "limit, so it will be cut off in search results"
                % (len(description), options["max_description"]))
        elif len(description) < options["min_description"]:
            add("short-meta-description", "warning",
                "meta description is %d characters, below the %d "
                "minimum, so it says too little in search results"
                % (len(description), options["min_description"]))
        desc_key = description.casefold()
        if desc_key in seen_descriptions:
            add("duplicate-meta-description", "error",
                "meta description %r is used on more than one "
                "page" % description)
        else:
            seen_descriptions.add(desc_key)

    h1 = row.get("h1", "").strip()
    if not h1:
        add("missing-h1", "error",
            "page has no H1, so search engines get no main "
            "heading")
    elif title and h1.casefold() == title.casefold():
        add("h1-same-as-title", "warning",
            "H1 repeats the title word for word, so it adds "
            "nothing for readers or search engines")

    h1_count = None
    try:
        h1_count = parse_int(row.get("h1_count"), code, "H1 count")
    except ValueError as exc:
        add("invalid-h1-count", "error", str(exc))
    if h1_count is not None and h1_count > 1:
        add("multiple-h1", "error",
            "page has %d H1 headings, but a page should have "
            "exactly one" % h1_count)

    word_count = None
    try:
        word_count = parse_int(row.get("word_count"), code,
                               "word count")
    except ValueError as exc:
        add("invalid-word-count", "error", str(exc))
    if word_count is not None:
        if word_count < 0:
            add("invalid-word-count", "error",
                "word count %d is below zero" % word_count)
        elif word_count < options["min_words"]:
            add("thin-content", "warning",
                "page has %d words, below the %d minimum, so it "
                "is thin content" % (word_count,
                                     options["min_words"]))

    status = row.get("status", "").strip().lower()
    if not status:
        status = "index"
    if status not in VALID_STATUSES:
        add("invalid-status", "error",
            "status %r is not index or noindex"
            % row.get("status", "").strip())

    canonical = row.get("canonical", "").strip()
    if not canonical and status == "index":
        add("missing-canonical", "warning",
            "indexable page has no canonical URL, so search "
            "engines may index a duplicate version")

    keyword = row.get("focus_keyword", "").strip()
    if options["has_keyword_column"]:
        if not keyword:
            add("missing-focus-keyword", "warning",
                "page has no focus keyword set, so nobody checked "
                "what it should rank for")
        elif title and keyword.casefold() not in title.casefold():
            add("keyword-not-in-title", "warning",
                "focus keyword %r does not appear in the title"
                % keyword)

    modified = None
    try:
        modified = parse_date(row.get("last_modified"), code,
                              "last modified date")
    except ValueError as exc:
        add("invalid-date", "error", str(exc))
    if modified is not None:
        if modified > options["as_of"]:
            add("future-date", "error",
                "last modified date %s is in the future"
                % modified.isoformat())
        elif (options["as_of"] - modified).days \
                > options["stale_days"]:
            add("stale-content", "warning",
                "page was last modified %s, more than %d days ago"
                % (modified.isoformat(), options["stale_days"]))

    return findings


def audit(rows, options):
    """Audit all page rows and return (findings, report)."""
    findings = []
    seen_urls = set()
    seen_titles = set()
    seen_descriptions = set()
    by_type = {}
    by_status = {}
    for row in rows:
        findings.extend(audit_row(row, seen_urls, seen_titles,
                                  seen_descriptions, options))
        content_type = row.get("content_type", "").strip() or "(blank)"
        entry = by_type.setdefault(content_type, {"count": 0})
        entry["count"] += 1
        status = row.get("status", "").strip().lower() or "index"
        by_status[status] = by_status.get(status, 0) + 1
    report = {
        "pages": len(rows),
        "by_type": [{"type": key, "count": value["count"]}
                    for key, value in sorted(by_type.items())],
        "by_status": [{"status": key, "count": value}
                      for key, value in sorted(by_status.items())],
    }
    return findings, report


def summarize(findings, report):
    """Build the summary dict from findings and the report."""
    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")
    summary = {
        "pages": report["pages"],
        "findings": len(findings),
        "errors": errors,
        "warnings": warnings,
    }
    return summary


def format_text(findings, report, summary):
    """Render the audit as human-readable text."""
    lines = []
    for finding in findings:
        lines.append(str(finding))
    if report["by_type"]:
        lines.append("")
        lines.append("Pages by type:")
        for entry in report["by_type"]:
            lines.append("  %-18s %d pages" % (entry["type"],
                                               entry["count"]))
    if report["by_status"]:
        lines.append("")
        lines.append("Pages by status:")
        for entry in report["by_status"]:
            lines.append("  %-18s %d pages" % (entry["status"],
                                               entry["count"]))
    lines.append("")
    lines.append("Pages: %d, findings: %d, errors: %d, warnings: %d"
                 % (summary["pages"], summary["findings"],
                    summary["errors"], summary["warnings"]))
    if summary["errors"] == 0 and summary["warnings"] == 0:
        lines.append("All pages clean.")
    return "\n".join(lines) + "\n"


def format_json(findings, report, summary):
    """Render the audit as JSON."""
    payload = {
        "summary": summary,
        "by_type": report["by_type"],
        "by_status": report["by_status"],
        "findings": [f.as_dict() for f in findings],
    }
    return json.dumps(payload, indent=2) + "\n"


def read_csv(path, aliases=None):
    """Read a CSV file, normalising headers via the alias map."""
    aliases = aliases or HEADER_ALIASES
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return []
        mapped = {}
        for name in reader.fieldnames:
            if name is None:
                continue
            mapped[name] = aliases.get(normalise_header(name),
                                       normalise_header(name))
        rows = []
        for raw in reader:
            row = {}
            for name, value in raw.items():
                if name is None:
                    continue
                row[mapped[name]] = "" if value is None else value
            rows.append(row)
        return rows


def parse_args(argv):
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Audit a WordPress pages CSV export for "
                    "on-page SEO problems.")
    parser.add_argument("file", help="CSV file of pages to audit")
    parser.add_argument("--max-title", type=int,
                        default=DEFAULT_MAX_TITLE,
                        help="flag titles above this length "
                             "(default: 60)")
    parser.add_argument("--min-title", type=int,
                        default=DEFAULT_MIN_TITLE,
                        help="flag titles below this length "
                             "(default: 30)")
    parser.add_argument("--max-description", type=int,
                        default=DEFAULT_MAX_DESCRIPTION,
                        help="flag meta descriptions above this "
                             "length (default: 160)")
    parser.add_argument("--min-description", type=int,
                        default=DEFAULT_MIN_DESCRIPTION,
                        help="flag meta descriptions below this "
                             "length (default: 50)")
    parser.add_argument("--min-words", type=int,
                        default=DEFAULT_MIN_WORDS,
                        help="flag pages below this word count "
                             "(default: 150)")
    parser.add_argument("--max-url", type=int,
                        default=DEFAULT_MAX_URL,
                        help="flag URLs above this length "
                             "(default: 115)")
    parser.add_argument("--stale-days", type=int,
                        default=DEFAULT_STALE_DAYS,
                        help="flag pages not modified for this "
                             "many days (default: 365)")
    parser.add_argument("--as-of", default=None,
                        help="reference date YYYY-MM-DD for stale "
                             "and future checks (default: today)")
    parser.add_argument("--json", action="store_true",
                        help="emit JSON instead of text")
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if any error is found")
    parser.add_argument("--strict", action="store_true",
                        help="with --check, also exit 1 on "
                             "warnings")
    parser.add_argument("--out", default=None,
                        help="write the report to a file")
    return parser.parse_args(argv)


def main(argv=None):
    """Run the audit and return the process exit code."""
    args = parse_args(argv)
    try:
        as_of = date.today()
        if args.as_of:
            as_of = datetime.strptime(args.as_of,
                                      "%Y-%m-%d").date()
    except ValueError:
        print("error: --as-of must be a YYYY-MM-DD date",
              file=sys.stderr)
        return 2
    try:
        rows = read_csv(args.file)
    except FileNotFoundError:
        print("error: file not found: %s" % args.file,
              file=sys.stderr)
        return 2
    except OSError as exc:
        print("error: cannot read %s: %s" % (args.file, exc),
              file=sys.stderr)
        return 2
    if not rows:
        print("error: no data rows in %s" % args.file,
              file=sys.stderr)
        return 2
    if "url" not in rows[0]:
        print("error: no URL column found in %s" % args.file,
              file=sys.stderr)
        return 2
    options = {
        "max_title": args.max_title,
        "min_title": args.min_title,
        "max_description": args.max_description,
        "min_description": args.min_description,
        "min_words": args.min_words,
        "max_url": args.max_url,
        "stale_days": args.stale_days,
        "as_of": as_of,
        "has_keyword_column": "focus_keyword" in rows[0],
    }
    findings, report = audit(rows, options)
    summary = summarize(findings, report)
    if args.json:
        output = format_json(findings, report, summary)
    else:
        output = format_text(findings, report, summary)
    if args.out:
        try:
            with open(args.out, "w", encoding="utf-8") as handle:
                handle.write(output)
        except OSError as exc:
            print("error: cannot write %s: %s" % (args.out, exc),
                  file=sys.stderr)
            return 2
    else:
        sys.stdout.write(output)
    if args.check:
        if summary["errors"] > 0:
            return 1
        if args.strict and summary["warnings"] > 0:
            return 1
    return 0


def main_entry():
    """Console script entry point."""
    sys.exit(main())


if __name__ == "__main__":
    main_entry()
