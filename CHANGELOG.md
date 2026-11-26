# Changelog

## 1.0.0 - 2026-11-15

Initial release.

* On-page SEO audit over a WordPress pages CSV export: missing
  titles and meta descriptions, duplicate titles, descriptions
  and URLs, missing or repeated H1s, thin content, titles and
  descriptions outside the length search results show, stale
  content, over-long URLs, invalid statuses and dates, and
  focus keywords that never appear in the title.
* Header aliases for Screaming Frog, Yoast SEO, and Rank Math
  exports, plus snake_case headers and UTF-8 BOM handling.
* Summary tables of pages by content type and by index status.
* Findings carry a code, rule name, severity (error or warning),
  and message; errors and warnings are counted in the summary.
* Text and --json output, --out file output, overridable
  thresholds (--max-title, --min-title, --max-description,
  --min-description, --min-words, --max-url, --stale-days,
  --as-of), and a --check CI gate that exits 1 on errors
  (and on warnings with --strict).
* Zero dependencies, Python 3.10 or newer.
