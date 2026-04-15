"""
scraper.py — data_pipeline (Segment 1)
Single-script pipeline: fetches, parses, and writes data/courses.json.
Supersedes the original two-step scraper.py + parser.py from SPEC_1.

Confirmed HTML structure (SPEC_1.1):
  Index page: http://coursecatalog.web.cmu.edu/coursedescriptions/
  Each department page lists courses as <dl> with <dt>/<dd> pairs:
    <dt>36-200 Reasoning with Data</dt>
    <dd>
      All Semesters: 9 units<br/>
      Description text...<br/>
      Prerequisites: <a href="...?P=36-218">36-218</a> or ...
    </dd>

Run: python data_pipeline/scraper.py
"""

import json
import re
import time

import requests
from bs4 import BeautifulSoup

from app.core.config import COURSES_PATH, DATA_DIR

INDEX_URL = "http://coursecatalog.web.cmu.edu/coursedescriptions/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; CMUCourseGraphScraper/1.0; "
        "educational research tool)"
    )
}

COURSE_ID_PATTERN = re.compile(r"^\d{2}-\d{3}$")
UNITS_PATTERN = re.compile(r"(\d+)\s+units", re.IGNORECASE)
MIN_DESCRIPTION_LENGTH = 20


def get_department_urls(index_url: str) -> list[str]:
    """
    Fetch the index page and return all unique department course page URLs.

    Looks for <a> tags whose href ends with /courses/ and returns them
    as a deduplicated list of absolute URLs.

    Args:
        index_url: The base index URL listing all departments.

    Returns:
        A list of absolute department page URLs, deduplicated.
    """
    try:
        response = requests.get(index_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[scraper] ERROR: failed to fetch index page: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    base = "http://coursecatalog.web.cmu.edu"

    seen: set[str] = set()
    urls: list[str] = []

    for a in soup.find_all("a", href=True):
        href: str = a["href"]
        if href.endswith("/courses/"):
            abs_url = href if href.startswith("http") else base + href
            if abs_url not in seen:
                seen.add(abs_url)
                urls.append(abs_url)

    print(f"[scraper] Found {len(urls)} department pages on index.")
    return urls


def parse_course_entry(dt_tag, dd_tag) -> dict | None:
    """
    Parse one <dt>/<dd> pair into a course dict conforming to SPEC_0 schema.

    Returns None if:
    - The <dt> text does not begin with a valid XX-NNN course id pattern
      (i.e., it is a section header or non-course entry).
    - The name is empty.
    - The description is empty or fewer than MIN_DESCRIPTION_LENGTH chars.

    Args:
        dt_tag: A BeautifulSoup <dt> element.
        dd_tag: The immediately following <dd> element.

    Returns:
        A course dict with keys: id, name, description, prerequisites,
        department, units, source. Or None if the entry should be skipped.
    """
    dt_text = dt_tag.get_text(separator=" ", strip=True)

    # Course id is the first token in <dt> — must match XX-NNN
    id_match = re.match(r"^(\d{2}-\d{3})\s+(.*)", dt_text)
    if not id_match:
        return None

    course_id = id_match.group(1)
    name = id_match.group(2).strip()

    if not name:
        return None

    # Department is the two-digit prefix before the hyphen (SPEC_1.1)
    department = course_id.split("-")[0]

    # --- Parse <dd> ---
    # Extract prerequisites: <a> tags with href containing ?P=
    prerequisites: list[str] = []
    for a in dd_tag.find_all("a", href=True):
        if "?P=" in a["href"]:
            prereq_id = a.get_text(strip=True)
            if COURSE_ID_PATTERN.match(prereq_id):
                prerequisites.append(prereq_id)

    # Get full dd text with line breaks represented as newlines
    # Replace <br> tags with newlines before extracting text
    for br in dd_tag.find_all("br"):
        br.replace_with("\n")
    dd_text = dd_tag.get_text(separator="\n")

    lines = [line.strip() for line in dd_text.splitlines()]
    lines = [line for line in lines if line]  # remove empty lines

    # Units: scan all lines for "N units" pattern
    units = 0
    units_line_idx = -1
    for i, line in enumerate(lines):
        units_match = UNITS_PATTERN.search(line)
        if units_match:
            units = int(units_match.group(1))
            units_line_idx = i
            break

    # Description: all lines except the units line and the prerequisites line.
    # The prerequisites line typically starts with "Prerequisites:" or
    # contains course id links. We remove it by detecting the pattern.
    prereq_line_pattern = re.compile(r"prerequisite", re.IGNORECASE)
    description_lines = []
    for i, line in enumerate(lines):
        if i == units_line_idx:
            continue
        if prereq_line_pattern.search(line):
            continue
        description_lines.append(line)

    description = " ".join(description_lines).strip()
    # Normalize multiple whitespace characters
    description = re.sub(r"\s+", " ", description)

    if len(description) < MIN_DESCRIPTION_LENGTH:
        return None

    return {
        "id": course_id,
        "name": name,
        "description": description,
        "prerequisites": prerequisites,
        "department": department,
        "units": units,
        "source": "official",
    }


def scrape_department_page(url: str) -> list[dict]:
    """
    Fetch one department course page and return a list of course dicts.

    Parses the confirmed <dl>/<dt>/<dd> structure (SPEC_1.1). Each
    consecutive <dt>/<dd> pair is passed to parse_course_entry(). Returns
    an empty list on fetch failure (logs a warning).

    Args:
        url: Absolute URL of a department course page.

    Returns:
        A list of parsed course dicts. May be empty on error or if the
        page contains no valid courses.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[scraper] WARNING: failed to fetch {url}: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    courses: list[dict] = []

    # Find all <dl> blocks; each contains <dt>/<dd> course pairs
    for dl in soup.find_all("dl"):
        children = [tag for tag in dl.children if tag.name in ("dt", "dd")]

        i = 0
        while i < len(children) - 1:
            dt = children[i]
            dd = children[i + 1]
            if dt.name == "dt" and dd.name == "dd":
                result = parse_course_entry(dt, dd)
                if result is not None:
                    courses.append(result)
                i += 2
            else:
                i += 1

    return courses


def scrape_all_departments() -> list[dict]:
    """
    Orchestrate the full scrape: fetch index, scrape all departments,
    merge, deduplicate by id (first occurrence wins), sort by id.

    Adds a 1-second polite delay between department page requests.

    Returns:
        Final deduplicated and sorted list of course dicts.
    """
    dept_urls = get_department_urls(INDEX_URL)
    if not dept_urls:
        print("[scraper] ERROR: no department URLs found. Aborting.")
        return []

    all_courses: list[dict] = []
    seen_ids: set[str] = set()
    duplicate_count = 0

    for url in dept_urls:
        print(f"[scraper] Scraping: {url}")
        time.sleep(1)
        dept_courses = scrape_department_page(url)
        print(f"[scraper]   → {len(dept_courses)} courses parsed")

        for course in dept_courses:
            cid = course["id"]
            if cid in seen_ids:
                duplicate_count += 1
            else:
                seen_ids.add(cid)
                all_courses.append(course)

    all_courses.sort(key=lambda c: c["id"])

    print(
        f"\n[scraper] Scrape complete. "
        f"Total: {len(all_courses)} unique courses, "
        f"{duplicate_count} duplicates dropped."
    )
    return all_courses


def write_courses(courses: list[dict]) -> None:
    """
    Write the courses list to COURSES_PATH as formatted JSON.
    Creates the data/ directory if it does not exist.

    Args:
        courses: The list returned by scrape_all_departments().
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(COURSES_PATH, "w", encoding="utf-8") as f:
        json.dump(courses, f, indent=2, ensure_ascii=False)
    print(f"[scraper] Saved to {COURSES_PATH}")


if __name__ == "__main__":
    courses = scrape_all_departments()
    write_courses(courses)
    print(f"Done. {len(courses)} courses written to data/courses.json.")
