# SPEC_1.2_scraper_parsing_patch.md
# CMU Course Graph — Patch for Segment 1: Scraper Parsing Logic
# This file SUPERSEDES the parse_course_entry() section of SPEC_1.1.
# Read SPEC_0 → SPEC_1 → SPEC_1.1 → this file in order.

---

## What Changed

SPEC_1.1's parsing logic had two bugs confirmed from live HTML:
1. Prerequisites were collected from ALL `?P=` links in `<dd>`,
   including course references in the description body.
2. Description extraction dropped entire lines containing
   "prerequisite", which caused courses like 36-700 (where
   prerequisites are mentioned inline without a separate `<br>`)
   to lose their description entirely.

This patch replaces the `parse_course_entry()` implementation spec
with a corrected version based on confirmed HTML structure.

---

## Confirmed HTML Structure

Each course is a `<dl class="courseblock">` block containing:
- One `<dt class="keepwithnext">` — course id and name
- One `<dd>` — all course metadata, segments separated by `<br />`

The `<dd>` content always follows this segment order:
1. **Semester/units line** (always first): e.g. `"Fall: 12 units"`,
   `"All Semesters: 6 units"`, `"Fall and Spring"` (units optional)
2. **Description body** (one or more segments): free text, may
   contain `?P=` course reference links that are NOT prerequisites
3. **Prerequisites segment** (optional, always last meaningful
   segment): starts with the literal text `"Prerequisites:"`,
   contains `?P=` links for actual prerequisite courses

---

## Corrected parse_course_entry() Spec

```python
def parse_course_entry(dt_tag, dd_tag) -> dict | None:
    """
    Parse one <dt>/<dd> pair into a course dict.
    Returns None if dt does not match XX-NNN pattern.
    """
```

### Step 1: Extract id and name from <dt>

Get the text content of `dt_tag`. Apply regex `^(\d{2}-\d{3})\s+(.+)`.
- Group 1 is `id` (e.g. `"36-700"`)
- Group 2 is `name` (e.g. `"Probability and Mathematical Statistics"`)

If no match, return `None` immediately.

### Step 2: Extract department

`department = id.split("-")[0]`  — the two digits before the hyphen.
Apply the whitelist check here:

```python
if department not in ALLOWED_DEPARTMENTS:
    return None
```

### Step 3: Split <dd> into segments by <br>

Replace every `<br>` / `<br />` tag in `dd_tag` with a sentinel
string (e.g. `"|||"`), then get the full text content, then split
on that sentinel. Strip each segment. Discard empty segments.
This gives an ordered list of text segments.

### Step 4: Extract semester and units from segment[0]

The first segment always contains semester and optionally units.
- **Units**: apply regex `(\d+)\s+units` to segment[0].
  If match found, `units = int(match.group(1))`. Otherwise `units = 0`.
- **Semester**: take segment[0], strip the units portion if present,
  strip trailing punctuation and whitespace.
  Store as a string, e.g. `"Fall"`, `"All Semesters"`, `"Fall and Spring"`.
  This field is not in the SPEC_0 schema — add it as `"semester"` string.
  If parsing fails, default to `"TBD"`.

### Step 5: Identify the prerequisites segment

Scan segments from the END backwards. Find the first segment whose
text (case-insensitive) starts with `"prerequisites"`. This is the
prerequisites segment. All segments before it (excluding segment[0])
form the description body.

If no prerequisites segment exists, description body = all segments
after segment[0], and prerequisites = `[]`.

### Step 6: Extract prerequisites from the prerequisites segment

Take only the prerequisites segment identified in Step 5.
Find all `<a>` tags within that segment's original HTML
(not the stripped text — go back to the BeautifulSoup tag).
Collect link text for each `<a>` whose `href` contains `?P=`.
These are the prerequisite course ids.

**Important:** only search for `<a>` tags within the prerequisites
segment's portion of `dd_tag`. Do NOT search the entire `dd_tag`.

To implement this correctly: before stripping to text, find the
`<br>` tags in `dd_tag` to identify which `<a>` tags fall after
the last `<br>` that precedes the prerequisites text. Alternatively,
check each `<a>` tag in `dd_tag` — if its `.get_text()` matches
`\d{2}-\d{3}` AND it appears after the "Prerequisites:" text node
in document order, include it.

The simplest correct implementation: find the index of the
prerequisites segment in the split list, then collect all `<a>`
tags from `dd_tag` that appear after the `<br>` tag corresponding
to that split index.

### Step 7: Extract description

Join all description body segments (from Step 5) with a single space.
Strip leading/trailing whitespace.
If the result is fewer than 20 characters, return `None` (discard).

### Step 8: Assemble and return

```python
return {
    "id": id,
    "name": name,
    "description": description,
    "prerequisites": prerequisites,   # list of id strings, may be []
    "department": department,         # two-digit string e.g. "36"
    "units": units,                   # int, 0 if not found
    "semester": semester,             # string e.g. "Fall"
    "source": "official"
}
```

Note: `"semester"` is a new field not in SPEC_0. Add it to the schema.
Update SPEC_0's courses.json schema accordingly if needed, but it does
not affect any downstream module since no other module reads this field.

---

## Verification cases

After re-running scraper.py, manually verify these three courses:

**36-498 Corporate Capstone II**
- prerequisites: `[]` (the 36-497 links are in description, not prereqs)
- description: contains "continue work on projects begun as part of..."
- units: 0 (no units mentioned)

**36-700 Probability and Mathematical Statistics**
- prerequisites: `[]` (prereq text is plain text, no course links)
- description: contains "one-semester course covering the basics..."
- units: 12

**36-712 Introduction to mean field statistics**
- prerequisites: `["10-601"]` (only the linked course; 36-705 and
  36-725 appear as plain text without links, so they are excluded)
- description: contains "ideas and techniques...statistical physics..."
- units: 6