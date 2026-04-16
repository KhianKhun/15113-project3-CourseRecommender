"""
scraper.py — data_pipeline (Segment 1)
Single-script pipeline: fetches, parses, and writes data/courses.json.
Supersedes the original two-step scraper.py + parser.py from SPEC_1.

Confirmed HTML structure (SPEC_1.2):
  Index page: http://coursecatalog.web.cmu.edu/coursedescriptions/
  Each course is a <dl class="courseblock"> with:
    <dt class="keepwithnext">XX-NNN Course Name</dt>
    <dd>
      Semester: N units<br/>
      Description body...<br/>
      Prerequisites: <a href="...?P=XX-NNN">XX-NNN</a> or ...
    </dd>
  Segments within <dd> are separated by <br> tags.
  The prerequisites segment (if present) is always the last segment
  and starts with the literal text "Prerequisites:".

Run: python -m data_pipeline.scraper
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
    Parse one <dt>/<dd> pair into a course dict (SPEC_1.2).

    Steps:
      1. Extract id and name from <dt> text.
      2. Extract department; skip if not in ALLOWED_DEPARTMENTS.
      3. Split <dd> into ordered segments by iterating contents at <br>
         boundaries, preserving <a> tags per segment.
      4. Extract semester and units from segment[0].
      5. Scan segments from end to find the prerequisites segment
         (starts with "Prerequisites:").
      6. Extract prerequisite ids from <a ?P=> links in that segment only.
      7. Build description from body segments between segment[0] and prereq.
      8. Assemble and return dict; return None if description too short.

    Args:
        dt_tag: A BeautifulSoup <dt> element.
        dd_tag: The immediately following <dd> element.

    Returns:
        A course dict or None if the entry should be skipped.
    """
    # Step 1: id and name from <dt>
    dt_text = dt_tag.get_text(separator=" ", strip=True)
    id_match = re.match(r"^(\d{2}-\d{3})\s+(.+)", dt_text)
    if not id_match:
        return None

    course_id = id_match.group(1)
    name = id_match.group(2).strip()
    if not name:
        return None

    # Step 2: extract department from course id
    department = course_id.split("-")[0]

    # Step 3: split <dd> into segments by <br>, preserving <a> tags per segment.
    # We iterate dd_tag.contents WITHOUT modifying the tag so <a> references
    # remain valid.
    segments: list[dict] = []   # each entry: {"text": str, "a_tags": list}
    current_parts: list[str] = []
    current_a_tags: list = []

    for child in dd_tag.contents:
        if getattr(child, "name", None) == "br":
            seg_text = re.sub(r"\s+", " ", " ".join(current_parts)).strip()
            segments.append({"text": seg_text, "a_tags": current_a_tags})
            current_parts = []
            current_a_tags = []
        else:
            if hasattr(child, "get_text"):
                current_parts.append(child.get_text(separator=" "))
                if child.name == "a":
                    current_a_tags.append(child)
                elif hasattr(child, "find_all"):
                    current_a_tags.extend(child.find_all("a"))
            else:
                current_parts.append(str(child))

    # Capture the final segment (no trailing <br>)
    if current_parts or current_a_tags:
        seg_text = re.sub(r"\s+", " ", " ".join(current_parts)).strip()
        segments.append({"text": seg_text, "a_tags": current_a_tags})

    segments = [s for s in segments if s["text"]]
    if not segments:
        return None

    # Step 4: semester and units from segment[0]
    seg0_text = segments[0]["text"]
    units_match = UNITS_PATTERN.search(seg0_text)
    units = int(units_match.group(1)) if units_match else 0

    semester_text = seg0_text[: units_match.start()] if units_match else seg0_text
    semester = re.sub(r"[\s:,]+$", "", semester_text).strip() or "TBD"

    # Step 5: find prerequisites segment by scanning from the end.
    # It is the last segment whose text starts with "Prerequisites:" (case-insensitive).
    prereq_idx: int | None = None
    for i in range(len(segments) - 1, 0, -1):
        if re.match(r"prerequisites?\s*:", segments[i]["text"], re.IGNORECASE):
            prereq_idx = i
            break

    # Step 6: extract prerequisites from the prereq segment's <a> tags only.
    prerequisites: list[str] = []
    if prereq_idx is not None:
        for a in segments[prereq_idx]["a_tags"]:
            if a.get("href") and "?P=" in a["href"]:
                prereq_id = a.get_text(strip=True)
                if COURSE_ID_PATTERN.match(prereq_id):
                    prerequisites.append(prereq_id)

    # Step 7: description from body segments (between segment[0] and prereq).
    body_end = prereq_idx if prereq_idx is not None else len(segments)
    body_segments = segments[1:body_end]
    description = re.sub(r"\s+", " ", " ".join(s["text"] for s in body_segments)).strip()

    if len(description) < MIN_DESCRIPTION_LENGTH:
        return None

    # Step 8: assemble result
    return {
        "id": course_id,
        "name": name,
        "description": description,
        "prerequisites": prerequisites,
        "department": department,
        "units": units,
        "semester": semester,
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
