# Good first issues

Seeded issues for new contributors. File each one on GitHub with the
`good first issue` and `help wanted` labels.

## 1. Flag pages whose title and H1 target different keywords

Title: Warn when the H1 keyword and the title keyword disagree

Description: The tool checks whether the focus keyword appears in
the title, but it never compares the title with the H1. Add a
warning when the focus keyword appears in the H1 but not in the
title, and another when it appears in the title but not in the
H1, so a page that splits its keyword targeting across the two
is easy to spot.

Difficulty: Easy

Acceptance criteria: a sample page with the keyword in the H1
only gets the new warning; a page with the keyword in both stays
clean; a page with no focus keyword column stays clean; a test
covers both cases; README documents the rule.

## 2. Add a per-type findings breakdown

Title: Show error and warning counts per content type

Description: The report prints pages by type, but not how many
findings each type carries. Add an errors and warnings count to
each row of the pages-by-type table (and to the JSON by_type
entries), so a store owner can see at a glance whether products
or posts carry the most SEO debt.

Difficulty: Easy

Acceptance criteria: the type table in text output shows
findings counts; JSON by_type rows gain errors and warnings
fields; a test checks both values for the sample file (product
rows carry the most errors); README documents the columns.

## 3. Support a known-good titles reference file

Title: Let sites check titles against an approved list

Description: Add an optional --reference flag that takes a CSV
of approved titles (url, title). Flag any audited page whose
title differs from the approved title for the same URL, so a
site can catch a title that drifted from the copy the SEO team
signed off.

Difficulty: Medium

Acceptance criteria: a reference file flags the sample home page
as differing; matching titles stay clean; a missing reference
file exits 2 with a clear error; a test covers both cases;
README documents the flag.

## 4. Add a word-count distribution to the summary

Title: Show a word-count histogram in the report

Description: The report flags thin pages one by one but never
shows the shape of the site. Add a small word-count histogram
to the text report (buckets: under 150, 150 to 499, 500 to 999,
1000 plus) with a count per bucket, and the same buckets in the
JSON output, so a site owner can see how much of the site is
thin at a glance.

Difficulty: Medium

Acceptance criteria: the sample file shows 3 pages under 150
words and the rest in the higher buckets; the clean file shows
all pages in the 150 plus buckets; a test checks the bucket
counts for both files; README documents the histogram.
