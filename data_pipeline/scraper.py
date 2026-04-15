"""
scraper.py — data_pipeline (Segment 1)
Fetches raw HTML from the CMU course catalog and writes data/raw_courses.json.

Run: python data_pipeline/scraper.py

This script performs all network I/O. It does not parse or clean data —
that is parser.py's responsibility. Separating fetching from parsing means
the parser can be re-run without hitting the network again.
"""

import json
import sys
import time

import requests
from bs4 import BeautifulSoup

from app.core.config import DATA_DIR

RAW_COURSES_PATH = DATA_DIR / "raw_courses.json"

# Add new departments here without modifying any other code.
DEPARTMENT_CONFIGS = [
    {
        "department_code": "10",
        "catalog_url": "https://coursecatalogue.andrew.cmu.edu/schools/school-computer-science/departments/machine-learning/",
    },
    {
        "department_code": "36",
        "catalog_url": "https://coursecatalogue.andrew.cmu.edu/schools/dietrich-college-humanities-social-sciences/departments/statistics-data-science/",
    },
    {
        "department_code": "15",
        "catalog_url": "https://coursecatalogue.andrew.cmu.edu/schools/school-computer-science/departments/computer-science/",
    },
    {
        "department_code": "21",
        "catalog_url": "https://coursecatalogue.andrew.cmu.edu/schools/mellon-college-science/departments/mathematical-sciences/",
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; CMUCourseGraphScraper/1.0; "
        "educational research tool)"
    )
}


def scrape_department(department_code: str, catalog_url: str) -> list[dict]:
    """
    Scrapes all courses listed on a single department catalog page.

    Fetches the department index page to collect individual course URLs,
    then fetches each course detail page to extract raw fields.

    Args:
        department_code: The numeric prefix string (e.g. "10", "15").
        catalog_url: The URL of the department's catalog page.

    Returns:
        A list of raw course dicts with keys:
            raw_id, raw_name, raw_description, raw_prerequisites_text,
            raw_units, department_code.
        Failed individual course fetches are skipped with a warning printed.
    """
    raw_courses = []

    try:
        response = requests.get(catalog_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[scraper] ERROR: failed to fetch department {department_code}: {e}")
        return raw_courses

    soup = BeautifulSoup(response.text, "html.parser")

    # Collect links to individual course pages.
    # The catalog uses <a> tags whose href contains the course number pattern.
    course_links = _extract_course_links(soup, catalog_url)

    print(f"[scraper] Department {department_code}: found {len(course_links)} course links")

    for url in course_links:
        time.sleep(1)  # Polite delay to avoid overloading CMU's servers
        raw = _scrape_course_page(url, department_code)
        if raw is not None:
            raw_courses.append(raw)

    return raw_courses


def _extract_course_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    """
    Extracts all individual course page URLs from a department index page.

    Looks for anchor tags whose href contains a course-number-like pattern.
    Returns absolute URLs.

    Args:
        soup: Parsed HTML of the department index page.
        base_url: The department index URL, used to resolve relative links.

    Returns:
        A deduplicated list of absolute course page URL strings.
    """
    import re
    from urllib.parse import urljoin, urlparse

    base = "https://coursecatalogue.andrew.cmu.edu"
    seen: set[str] = set()
    links: list[str] = []

    for a in soup.find_all("a", href=True):
        href: str = a["href"]
        # Course pages typically contain a numeric course id in the path
        if re.search(r"\d{2}-\d{3}", href):
            abs_url = urljoin(base, href)
            if abs_url not in seen:
                seen.add(abs_url)
                links.append(abs_url)

    return links


def _scrape_course_page(url: str, department_code: str) -> dict | None:
    """
    Fetches and extracts raw fields from a single course detail page.

    Args:
        url: The absolute URL of the course detail page.
        department_code: The department prefix (e.g. "10").

    Returns:
        A raw course dict, or None if the fetch or extraction fails.
    """
    import re

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[scraper] WARNING: failed to fetch {url}: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    # Extract course id from the page title or heading (e.g. "10-301")
    raw_id = _extract_text(soup, ["h1", "h2", ".course-number", ".course-id"])
    id_match = re.search(r"\d{2}-\d{3}", raw_id or url)
    raw_id = id_match.group(0) if id_match else ""

    # Extract course name
    raw_name = _extract_text(soup, [".course-title", "h1", "h2"])

    # Extract description — typically in a <p> or .course-description block
    raw_description = _extract_text(soup, [
        ".course-description", ".description", "article p", "main p",
    ])

    # Extract prerequisites text as-is (raw string, not parsed)
    raw_prerequisites_text = _extract_prerequisites_text(soup)

    # Extract units
    raw_units = _extract_text(soup, [".course-units", ".units", ".credits"])
    raw_units = re.sub(r"[^\d]", "", raw_units or "")

    if not raw_id:
        print(f"[scraper] WARNING: could not extract course id from {url}, skipping")
        return None

    return {
        "raw_id": raw_id,
        "raw_name": raw_name or "",
        "raw_description": raw_description or "",
        "raw_prerequisites_text": raw_prerequisites_text or "",
        "raw_units": raw_units or "0",
        "department_code": department_code,
    }


def _extract_text(soup: BeautifulSoup, selectors: list[str]) -> str:
    """
    Tries each CSS selector in order and returns the text of the first match.

    Args:
        soup: The parsed BeautifulSoup tree.
        selectors: A list of CSS selector strings to try in priority order.

    Returns:
        The stripped text content of the first matching element, or "".
    """
    for selector in selectors:
        el = soup.select_one(selector)
        if el and el.get_text(strip=True):
            return el.get_text(separator=" ", strip=True)
    return ""


def _extract_prerequisites_text(soup: BeautifulSoup) -> str:
    """
    Extracts the raw prerequisite text block from a course page.

    Looks for a heading or label containing "prerequisite" (case-insensitive)
    and returns the following sibling's text content.

    Args:
        soup: The parsed BeautifulSoup tree.

    Returns:
        The raw prerequisite string exactly as it appears on the page, or "".
    """
    import re

    for tag in soup.find_all(["h2", "h3", "h4", "strong", "b", "dt", "th"]):
        if re.search(r"prerequisite", tag.get_text(), re.IGNORECASE):
            sibling = tag.find_next_sibling()
            if sibling:
                return sibling.get_text(separator=" ", strip=True)
            parent = tag.parent
            if parent:
                return parent.get_text(separator=" ", strip=True)

    # Fallback: look for a paragraph or div containing prerequisite ids
    for el in soup.find_all(["p", "div", "dd"]):
        text = el.get_text()
        if re.search(r"prerequisite", text, re.IGNORECASE) and re.search(r"\d{2}-\d{3}", text):
            return text.strip()

    return ""


def scrape_all() -> list[dict]:
    """
    Runs the full scrape across all departments in DEPARTMENT_CONFIGS.

    Returns:
        The combined list of all raw course dicts.
        Prints a per-department and overall summary to stdout.
    """
    all_raw: list[dict] = []
    failed = 0

    for config in DEPARTMENT_CONFIGS:
        dept_code = config["department_code"]
        url = config["catalog_url"]
        print(f"[scraper] Scraping department {dept_code} from {url}")
        raw = scrape_department(dept_code, url)
        all_raw.extend(raw)
        print(f"[scraper] Department {dept_code}: collected {len(raw)} courses")

    success = len(all_raw)
    print(f"\n[scraper] Done. Total: {success} courses fetched, {failed} departments failed.")
    return all_raw


def save_raw(raw_courses: list[dict]) -> None:
    """
    Writes the raw course list to data/raw_courses.json.

    Args:
        raw_courses: The list returned by scrape_all().

    Returns:
        None. Writes to RAW_COURSES_PATH.
    """
    RAW_COURSES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_COURSES_PATH, "w", encoding="utf-8") as f:
        json.dump(raw_courses, f, indent=2, ensure_ascii=False)
    print(f"[scraper] Saved {len(raw_courses)} raw courses to {RAW_COURSES_PATH}")


if __name__ == "__main__":
    raw = scrape_all()
    save_raw(raw)
