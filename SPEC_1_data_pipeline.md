# SPEC_1_data_pipeline.md
# CMU Course Graph — Segment 1: Data Pipeline
# Before starting, read SPEC_0_convention.md in full.
# This session is responsible for all files under `data_pipeline/`.
# Do not create or modify any files outside of `data_pipeline/`.

---

## Overview

The data pipeline is a one-time tool. It is run once by the developer to
produce `data/courses.json`, after which it is not needed for normal app
operation. The pipeline has three stages: scraping, parsing, and validation.
Each stage is a separate script. They are meant to be run in sequence from
the terminal:

```bash
python data_pipeline/scraper.py
python data_pipeline/parser.py
python data_pipeline/validator.py
```

The final output of the pipeline is `data/courses.json`, which must conform
exactly to the schema defined in SPEC_0.

---

## Data Source

CMU's course catalog is publicly available at:
https://coursecatalogue.andrew.cmu.edu/

The catalog lists courses by department. Each course has a detail page
containing the course number, title, description, units, and prerequisites.
The site is static HTML and does not require JavaScript rendering, so
`requests` + `BeautifulSoup` is sufficient. Do not use Playwright.

Target departments for the initial scrape (these cover the core SML/CS/Stats
curriculum):
- Machine Learning (10-XXX)
- Statistics (36-XXX)
- Computer Science (15-XXX)
- Mathematics (21-XXX)

The scraper should be easy to extend to additional departments by adding
entries to a configuration list, without modifying core scraping logic.

---

## scraper.py

### Responsibility

Fetch raw HTML from the CMU course catalog and save it locally. This script
performs all network requests and writes raw data to a staging file
`data/raw_courses.json`. It does not parse or clean anything — that is
parser.py's job. Separating fetching from parsing means you can re-run
the parser without hitting the network again.

### Output format for data/raw_courses.json

A JSON array where each element contains the minimally-extracted raw fields
directly from the HTML, before any cleaning:

```json
[
  {
    "raw_id": "10-301",
    "raw_name": "Introduction to Machine Learning",
    "raw_description": "  This course provides...  ",
    "raw_prerequisites_text": "21-241 and (36-218 or 36-219)",
    "raw_units": "12",
    "department_code": "10"
  }
]
```

Note that `raw_prerequisites_text` is the unparsed string exactly as it
appears on the page. Parsing this into a clean list of ids is parser.py's
responsibility.

### Key implementation details

Define a `DEPARTMENT_CONFIGS` list at the top of the file. Each entry is a
dict with keys `department_code` (string) and `catalog_url` (string). The
main scraping loop iterates over this list, so adding a new department
requires only adding a new entry here.

Add a polite delay of 1 second between requests using `time.sleep(1)` to
avoid overloading CMU's servers.

If a network request fails, log the error and continue to the next course
rather than crashing. At the end, print a summary of how many courses were
successfully fetched and how many failed.

---

## parser.py

### Responsibility

Read `data/raw_courses.json`, clean and normalize every field, parse the
prerequisite text into a list of course id strings, and write the result to
`data/courses.json`. This script must produce output that exactly matches
the schema in SPEC_0.

### Prerequisite parsing logic

The prerequisite text on CMU's catalog uses natural language like "21-241
and (36-218 or 36-219)". The parser should extract all course id patterns
matching the regex `\d{2}-\d{3}` from this string and return them as a flat
list. Boolean logic (and/or) is intentionally discarded for now — the list
simply contains all mentioned course ids. This is a known simplification and
should be noted in a comment.

### Cleaning rules

Strip all leading and trailing whitespace from `raw_description` and
`raw_name`. Convert `raw_units` to an integer; if conversion fails, default
to 0 and log a warning. Set `source` to `"official"` for all entries.
Derive `department` from `department_code` using a hardcoded mapping dict
at the top of the file, for example `{"10": "ML", "36": "STATS",
"15": "CS", "21": "MATH"}`.

Discard any course where `raw_description` is empty or fewer than 20
characters after stripping, since an embedding computed on a near-empty
description would be meaningless.

### Output

Write the cleaned array to `data/courses.json` following the schema in
SPEC_0 exactly. Print a summary of how many courses were written and how
many were discarded.

---

## validator.py

### Responsibility

Read `data/courses.json` and verify that every entry conforms to the schema
in SPEC_0. This script is the quality gate before the rest of the app uses
the data. It should be fast and exit with a non-zero status code if any
validation error is found, so it can be used as a simple CI check.

### Validation rules to enforce

Every entry must have all seven required fields: `id`, `name`, `description`,
`prerequisites`, `department`, `units`, `source`. The `id` field must match
the pattern `\d{2}-\d{3}`. All `id` values must be globally unique across
the array. The `source` field must be exactly `"official"` or `"user"`.
The `units` field must be a positive integer. The `prerequisites` field must
be a list (possibly empty). Every course id mentioned in any `prerequisites`
list must itself exist as an `id` in the array — no dangling references.

### Output

If all checks pass, print a success message and exit with code 0. If any
check fails, print a clear error message identifying the offending entry
and field, then exit with code 1.

---

## Dependencies

This segment requires only the following packages, all of which should be
added to `requirements.txt`:

```
requests
beautifulsoup4
```

No other third-party packages are needed for the data pipeline.

---

## What this segment does NOT do

This segment does not compute embeddings. It does not build any graph
structures. It does not touch anything under `app/`. Its sole output is
`data/courses.json` and the intermediate `data/raw_courses.json`.
`raw_courses.json` may be added to `.gitignore` as it is a large
intermediate artifact.