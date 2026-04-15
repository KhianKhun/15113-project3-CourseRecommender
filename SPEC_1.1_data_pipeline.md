# SPEC_1.1_data_pipeline_patch.md
# CMU Course Graph — Patch for Segment 1: Data Pipeline
# This file SUPERSEDES the corresponding sections of SPEC_1_data_pipeline.md.
# Read SPEC_0_convention.md first, then apply this patch on top of SPEC_1.

---

## What Changed

SPEC_1 assumed a two-step pipeline (scraper → parser) with unknown HTML
structure. Now that the actual site structure is confirmed, the pipeline
is simplified to a single script. The raw staging file `raw_courses.json`
is no longer needed. `scraper.py` and `parser.py` are merged into one
file: `scraper.py`. `parser.py` is removed. `validator.py` is unchanged.

---

## Confirmed Site Structure

Base URL: `http://coursecatalog.web.cmu.edu/coursedescriptions/`

This index page lists all department course pages as `<a>` tags. Each
department course page URL ends in `/courses/`. The scraper must:

1. Fetch the index page and collect all `/courses/` links.
2. Fetch each department page and parse courses from it.
3. Write the merged result to `data/courses.json`.

### Department page HTML structure (confirmed from live site)

Each course on a department page is rendered as a `<dl>` definition list.
Each course occupies exactly one `<dt>` + one `<dd>` pair:

```html
<dt>36-200 Reasoning with Data</dt>
<dd>
  All Semesters: 9 units
  <br/>
  This course is an introduction to...
  <br/>
  Prerequisites: <a href="...">36-218</a> or <a href="...">36-225</a>
</dd>
```

Key parsing rules derived from this structure:

- **Course id and name**: the `<dt>` text has the format
  `"XX-NNN Course Name"`. Split on the first space after the id pattern
  `\d{2}-\d{3}` to separate id from name.

- **Department code**: extracted from the course id itself — the two
  digits before the hyphen (e.g., `"36"` from `"36-200"`). Do NOT use
  a hardcoded mapping dict. The department field in `courses.json` is
  set to this two-digit string (e.g., `"36"`, `"15"`, `"10"`, `"21"`).

- **Units**: the first line of `<dd>` text contains a pattern like
  `"9 units"` or `"12 units"`. Extract with regex `(\d+)\s+units`.
  If not found, default to 0.

- **Description**: the body of the `<dd>` text after stripping the
  first line (semester/units line) and after stripping the
  prerequisites line. Strip all HTML tags and normalize whitespace.

- **Prerequisites**: find all `<a>` tags inside the `<dd>` whose
  `href` contains `?P=` (these are course cross-reference links).
  Extract the course id from the link text (not the href). Return as
  a flat list of id strings. Boolean logic (and/or) is intentionally
  discarded — collect all mentioned ids only.

---

## Revised scraper.py

### Single-script pipeline

`scraper.py` now does everything: fetch, parse, and write. It replaces
both the old `scraper.py` and `parser.py`. The output is written
directly to `data/courses.json` with no intermediate staging file.

### Entry point

```python
if __name__ == "__main__":
    courses = scrape_all_departments()
    write_courses(courses)
    print(f"Done. {len(courses)} courses written to data/courses.json.")
```

### Key functions to implement

```python
def get_department_urls(index_url: str) -> list[str]:
    """
    Fetch the index page and return all unique URLs ending in /courses/.
    Filter out duplicates. Return as a list of absolute URLs.
    """

def scrape_department_page(url: str) -> list[dict]:
    """
    Fetch one department course page and return a list of course dicts
    conforming to the SPEC_0 schema. Uses the confirmed HTML structure
    described above. Returns empty list on fetch failure (log warning).
    """

def parse_course_entry(dt_tag, dd_tag) -> dict | None:
    """
    Parse one <dt>/<dd> pair into a course dict.
    Returns None if the dt text does not match the XX-NNN pattern
    (i.e., it is a section header or non-course entry — skip it).
    """

def scrape_all_departments() -> list[dict]:
    """
    Orchestrates the full scrape: get department URLs, scrape each,
    merge results, deduplicate by id (keep first occurrence),
    sort by id, return final list.
    Add time.sleep(1) between department page requests.
    """

def write_courses(courses: list[dict]) -> None:
    """
    Write courses list to COURSES_PATH as formatted JSON.
    Creates data/ directory if it does not exist.
    """
```

### Deduplication note

Some courses appear on multiple department pages (cross-listed courses,
e.g., a course listed under both SCS and ML). Deduplicate by `id`,
keeping the first occurrence encountered. Log how many duplicates
were dropped.

### Discard rules

Discard any parsed entry where:
- `id` does not match `^\d{2}-\d{3}$`
- `description` is empty or fewer than 20 characters after stripping
- `name` is empty

---

## parser.py

This file is no longer needed. Do not create it.
If it already exists in the repository, it can be left as-is but
will not be called by anything.

---

## validator.py

Unchanged from SPEC_1. Run it after scraper.py to verify the output.

---

## Updated run sequence

```bash
python data_pipeline/scraper.py    # fetches + parses + writes courses.json
python data_pipeline/validator.py  # validates the output
```

---

## Updated dependencies

No change from SPEC_1. Only `requests` and `beautifulsoup4` are needed.