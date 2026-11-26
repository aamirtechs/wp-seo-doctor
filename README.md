# wp-seo-doctor

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/aamirtechs/wp-seo-doctor/blob/main/LICENSE) [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/aamirtechs/wp-seo-doctor/issues)

A zero-dependency Python CLI that audits a WordPress pages and
posts CSV export for the on-page SEO mistakes that cost clicks
and rankings: missing titles and meta descriptions, duplicate
titles and descriptions, missing or repeated H1s, thin content,
titles and descriptions outside the length search results show,
stale content, URLs that are too long, and focus keywords that
never appear in the title.

An audit of 270 sites in 2026 found 64 percent of WordPress
sites with no meta description on some pages, 37 percent with
thin content, and 28 percent with the same title on different
pages. Yoast SEO and Rank Math check one page at a time inside
the dashboard, and Screaming Frog's free version caps at 500
URLs. This tool is the offline audit: it reads the exported
CSV, flags every problem with a rule name and a severity, and
never touches your site.

## Install

Requires Python 3.10 or newer. No dependencies beyond the standard
library.

```bash
pip install wp-seo-doctor
```

Or run it straight from the source checkout:

```bash
python3 wp_seo_doctor.py examples/pages.csv
```

## Input format

A CSV export with a header row. Columns used: `url`, `title`,
`meta_description`, `h1`, `h1_count`, `word_count`, `status`,
`canonical`, `focus_keyword`, `content_type`, `last_modified`.
Screaming Frog aliases work too (`Address`, `Title 1`,
`Meta Description 1`, `H1-1`, `Word Count`), as do Yoast and
Rank Math names (`SEO Title`, `Focus Keyword`), and snake_case
headers. Extra columns are ignored, so a full export works
as-is. A UTF-8 BOM header is handled. A blank status defaults
to `index`.

```csv
url,title,meta_description,h1,h1_count,word_count,status,canonical,focus_keyword,content_type,last_modified
/shop/blue-widget/,Buy the Blue Widget With Free Shipping,The blue widget is our best seller. Durable, lightweight, and built to last for years of daily use.,Blue Widget,1,320,index,https://example.com/shop/blue-widget/,blue widget,product,2026-09-20
/blog/how-to-choose-a-widget/,How to Choose the Right Widget for You,Learn how to pick a widget that fits your space, your budget, and your daily routine.,How to Choose a Widget,1,1200,index,https://example.com/blog/how-to-choose-a-widget/,choose the right widget,post,2026-11-01
```

## What it checks

Errors, the ones that leave a page broken for search:

* `missing-title`: no title, so search results show the URL
  instead.
* `missing-meta-description`: no meta description, so search
  results show an auto-generated snippet.
* `duplicate-title`, `duplicate-meta-description`: the same
  title or description on more than one page.
* `duplicate-url`: the same URL listed more than once.
* `invalid-url`: a URL that does not start with `/` or
  `http(s)://`.
* `missing-h1`: no H1, so search engines get no main heading.
* `multiple-h1`: more than one H1 on a page.
* `invalid-status`: a status that is not `index` or `noindex`.
* `invalid-word-count`, `invalid-h1-count`, `invalid-date`:
  values that do not parse.
* `future-date`: a last modified date in the future.

Warnings, patterns worth fixing:

* `long-title`, `short-title`: titles above 60 or below 30
  characters (overridable with `--max-title` and `--min-title`).
* `long-meta-description`, `short-meta-description`:
  descriptions above 160 or below 50 characters (overridable
  with `--max-description` and `--min-description`).
* `thin-content`: word count below 150 (overridable with
  `--min-words`).
* `h1-same-as-title`: the H1 repeats the title word for word.
* `missing-canonical`: an indexable page with no canonical URL.
* `missing-focus-keyword`: no focus keyword set (only checked
  when the export has a focus keyword column).
* `keyword-not-in-title`: the focus keyword does not appear in
  the title.
* `long-url`: a URL above 115 characters (overridable with
  `--max-url`).
* `stale-content`: not modified for more than 365 days
  (overridable with `--stale-days` and `--as-of`).

The report also prints two tables after the findings: pages by
content type and pages by index status.

## Usage

```bash
python3 wp_seo_doctor.py examples/pages.csv --as-of 2026-11-15
```

Captured output:

```
WARNING [short-title] /: title is 24 characters, below the 30 minimum, so it says too little in search results
WARNING [h1-same-as-title] /: H1 repeats the title word for word, so it adds nothing for readers or search engines
WARNING [keyword-not-in-title] /: focus keyword 'widgets' does not appear in the title
WARNING [short-title] /about/: title is 8 characters, below the 30 minimum, so it says too little in search results
ERROR [missing-meta-description] /about/: page has no meta description, so search results show an auto-generated snippet
WARNING [missing-canonical] /about/: indexable page has no canonical URL, so search engines may index a duplicate version
WARNING [stale-content] /about/: page was last modified 2024-01-10, more than 365 days ago
WARNING [long-title] /shop/blue-widget/: title is 84 characters, above the 60 limit, so it will be cut off in search results
WARNING [long-title] /shop/red-widget/: title is 84 characters, above the 60 limit, so it will be cut off in search results
ERROR [duplicate-title] /shop/red-widget/: title 'Buy the Blue Widget Online Today With Free Shipping Included and a Two Year Warranty' is used on more than one page
ERROR [duplicate-meta-description] /shop/red-widget/: meta description 'The blue widget is our best seller. Durable, lightweight, and built to last for years of daily use.' is used on more than one page
ERROR [missing-h1] /shop/red-widget/: page has no H1, so search engines get no main heading
WARNING [thin-content] /shop/red-widget/: page has 90 words, below the 150 minimum, so it is thin content
WARNING [missing-canonical] /shop/red-widget/: indexable page has no canonical URL, so search engines may index a duplicate version
WARNING [missing-focus-keyword] /shop/red-widget/: page has no focus keyword set, so nobody checked what it should rank for
ERROR [multiple-h1] /blog/how-to-choose-a-widget/: page has 2 H1 headings, but a page should have exactly one
WARNING [keyword-not-in-title] /blog/how-to-choose-a-widget/: focus keyword 'choose a widget' does not appear in the title
WARNING [long-meta-description] /blog/widget-care-guide/: meta description is 214 characters, above the 160 limit, so it will be cut off in search results
WARNING [short-title] /contact/: title is 7 characters, below the 30 minimum, so it says too little in search results
WARNING [short-meta-description] /contact/: meta description is 47 characters, below the 50 minimum, so it says too little in search results
WARNING [thin-content] /contact/: page has 60 words, below the 150 minimum, so it is thin content
WARNING [stale-content] /contact/: page was last modified 2025-06-01, more than 365 days ago
ERROR [invalid-status] /shop/green-widget/: status 'maybe' is not index or noindex
WARNING [short-title] /old-page: title is 27 characters, below the 30 minimum, so it says too little in search results
WARNING [missing-focus-keyword] /old-page: page has no focus keyword set, so nobody checked what it should rank for
ERROR [future-date] /old-page: last modified date 2027-01-01 is in the future
ERROR [duplicate-url] /shop/blue-widget/: URL /shop/blue-widget/ is listed more than once
WARNING [short-title] /shop/blue-widget/: title is 26 characters, below the 30 minimum, so it says too little in search results
ERROR [invalid-url] bad-url: URL bad-url does not start with / or http(s)://
ERROR [missing-title] bad-url: page has no title, so search results show the URL instead
WARNING [short-title] /blog/widget-history/: title is 29 characters, below the 30 minimum, so it says too little in search results
ERROR [invalid-word-count] /blog/widget-history/: word count is not a whole number: 'many'
WARNING [keyword-not-in-title] /blog/widget-history/: focus keyword 'widget history' does not appear in the title
WARNING [keyword-not-in-title] /services/widget-repair/: focus keyword 'widget installation' does not appear in the title
WARNING [long-url] /very/long/url/that/keeps/going/and/going/with/many/segments/added/just/to/push/it/past/the/limit/set/for/urls/extra-segment-added-to-push-it-past-the-limit: URL is 156 characters, above the 115 limit, so it may be truncated in search results

Pages by type:
  page               7 pages
  post               3 pages
  product            4 pages

Pages by status:
  index              12 pages
  maybe              1 pages
  noindex            1 pages

Pages: 14, findings: 35, errors: 11, warnings: 24
```

The sample has 14 pages and 35 findings. The story it tells:
the red widget copies the blue widget's title and description
and has no H1, the home page title repeats as its H1, the
about page has no meta description and has not been touched
since 2024, one post has two H1s, one page carries a future
modified date, and one URL runs to 156 characters.

Use it as a CI gate: `--check` exits 1 when any error is found,
and 0 otherwise. On the sample above it exits 1:

```bash
python3 wp_seo_doctor.py examples/pages.csv --as-of 2026-11-15 --check
```

On `examples/clean.csv`, five clean pages, it exits 0:

```

Pages by type:
  page               3 pages
  post               1 pages
  product            1 pages

Pages by status:
  index              5 pages

Pages: 5, findings: 0, errors: 0, warnings: 0
All pages clean.
```

With `--strict`, `--check` also fails on warnings: a file with
warnings only (short titles, thin content, stale pages, a
missing canonical, and a keyword that never appears in its
title) exits 0 under `--check` and 1 under `--check --strict`.
`--json` emits the summary, the type and status tables, and
findings as JSON, and `--out` writes the report to a file.

Tune the thresholds to your house style: `--max-title 90
--min-words 300` on the sample drops the long-title warnings
on the two widget pages and flags five pages as thin, including
the 200-word bad-url page.

## Options

| Flag | Meaning |
| --- | --- |
| `--max-title` | Flag titles above this length (default: 60) |
| `--min-title` | Flag titles below this length (default: 30) |
| `--max-description` | Flag meta descriptions above this length (default: 160) |
| `--min-description` | Flag meta descriptions below this length (default: 50) |
| `--min-words` | Flag pages below this word count (default: 150) |
| `--max-url` | Flag URLs above this length (default: 115) |
| `--stale-days` | Flag pages not modified for this many days (default: 365) |
| `--as-of` | Reference date YYYY-MM-DD for stale and future checks (default: today) |
| `--json` | Emit JSON instead of text |
| `--check` | Exit 1 if any error is found |
| `--strict` | With --check, also exit 1 on warnings |
| `--out` | Write the report to a file |

## Edge cases

* A title at exactly `--max-title` or `--min-title` is not
  flagged; it must be strictly outside the range. The same
  applies to descriptions, word count, and URL length.
* Duplicate detection is case-insensitive, and URLs ignore a
  trailing slash, so `/About/` and `/about` count as the same
  URL.
* A blank status means `index`. A `noindex` page is not
  flagged for a missing canonical, since it should not be
  indexed at all.
* The focus keyword checks only run when the export has a
  focus keyword column. An export without one skips them
  silently.
* A stale check compares against `--as-of`, which defaults to
  today, so the same file can be re-audited later and pages
  will turn stale as they age.
* Rows with an unparseable word count or date are flagged as
  errors but still count in the page totals.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

59 tests, all passing: every rule, error and warning severities,
header aliases and BOM handling, duplicate detection, threshold
boundaries and overrides, summary counts, JSON output shape,
`--check` and `--strict` exit codes, and the three sample files
with their exact finding counts.

## License

MIT. See [LICENSE](LICENSE).
