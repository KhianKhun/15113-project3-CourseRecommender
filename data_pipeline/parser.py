"""
parser.py — data_pipeline (Segment 1)
Reads data/raw_courses.json, cleans and normalizes every field, and writes
the result to data/courses.json following the schema in SPEC_0.

Run: python data_pipeline/parser.py
"""

import json
import re
import sys

from app.core.config import DATA_DIR

RAW_COURSES_PATH = DATA_DIR / "raw_courses.json"
COURSES_PATH = DATA_DIR / "courses.json"

MIN_DESCRIPTION_LENGTH = 20  # Courses with shorter descriptions are discarded.

# Maps the numeric department_code prefix to the abbreviated department name
# used in the courses.json schema (SPEC_0).
DEPARTMENT_CODE_MAP: dict[str, str] = {
    "10": "ML",
    "36": "STATS",
    "15": "CS",
    "21": "MATH",
}

# Pattern for extracting course ids from prerequisite text.
COURSE_ID_PATTERN = re.compile(r"\d{2}-\d{3}")


def parse_course(raw: dict) -> dict | None:
    """
    Cleans and normalizes a single raw course dict into the SPEC_0 schema.

    Cleaning rules:
    - Strip all leading/trailing whitespace from raw_description and raw_name.
    - Discard the course if the stripped description is fewer than
      MIN_DESCRIPTION_LENGTH characters.
    - Convert raw_units to int; default to 0 and log a warning on failure.
    - Extract prerequisite ids from raw_prerequisites_text using the regex
      \\d{2}-\\d{3}. Boolean logic (and/or) is discarded — the list contains
      all mentioned ids. This is a known simplification.
    - Set source to "official" for all entries.
    - Derive department from department_code via DEPARTMENT_CODE_MAP.

    Args:
        raw: A single dict from raw_courses.json.

    Returns:
        A cleaned course dict conforming to the SPEC_0 schema, or None if
        the course is discarded due to a short description.
    """
    raw_id = str(raw.get("raw_id", "")).strip()
    raw_name = str(raw.get("raw_name", "")).strip()
    raw_description = str(raw.get("raw_description", "")).strip()
    raw_prerequisites_text = str(raw.get("raw_prerequisites_text", ""))
    raw_units = str(raw.get("raw_units", "0")).strip()
    department_code = str(raw.get("department_code", "")).strip()

    # Discard courses with empty or near-empty descriptions
    if len(raw_description) < MIN_DESCRIPTION_LENGTH:
        print(
            f"[parser] DISCARD {raw_id!r}: description too short "
            f"({len(raw_description)} chars)"
        )
        return None

    # Parse units — default to 0 on failure with a warning
    try:
        units = int(raw_units)
    except (ValueError, TypeError):
        print(f"[parser] WARNING: could not parse units for {raw_id!r}, defaulting to 0")
        units = 0

    # Extract all course-id-like strings from the prerequisite text.
    # NOTE: Boolean logic (and/or/parentheses) is intentionally discarded.
    # The list contains every course id mentioned, regardless of conjunctions.
    prerequisites = COURSE_ID_PATTERN.findall(raw_prerequisites_text)

    department = DEPARTMENT_CODE_MAP.get(department_code, department_code)

    return {
        "id": raw_id,
        "name": raw_name,
        "description": raw_description,
        "prerequisites": prerequisites,
        "department": department,
        "units": units,
        "source": "official",
    }


def parse_all(raw_courses: list[dict]) -> tuple[list[dict], int]:
    """
    Parses all raw course dicts into cleaned SPEC_0-conforming course dicts.

    Args:
        raw_courses: The list loaded from data/raw_courses.json.

    Returns:
        A tuple (parsed_courses, discarded_count) where:
            parsed_courses: Successfully parsed course dicts.
            discarded_count: Number of courses discarded during parsing.
    """
    parsed = []
    discarded = 0

    for raw in raw_courses:
        result = parse_course(raw)
        if result is not None:
            parsed.append(result)
        else:
            discarded += 1

    return parsed, discarded


def main() -> None:
    """
    Entry point. Reads raw_courses.json, parses, and writes courses.json.
    Prints a summary of written and discarded courses.
    Exits with code 1 if raw_courses.json does not exist.
    """
    if not RAW_COURSES_PATH.exists():
        print(
            f"[parser] ERROR: {RAW_COURSES_PATH} not found. "
            "Run scraper.py first."
        )
        sys.exit(1)

    with open(RAW_COURSES_PATH, "r", encoding="utf-8") as f:
        raw_courses = json.load(f)

    print(f"[parser] Loaded {len(raw_courses)} raw courses from {RAW_COURSES_PATH}")

    parsed, discarded = parse_all(raw_courses)

    COURSES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(COURSES_PATH, "w", encoding="utf-8") as f:
        json.dump(parsed, f, indent=2, ensure_ascii=False)

    print(
        f"\n[parser] Done. Written: {len(parsed)} courses, "
        f"Discarded: {discarded} courses."
    )
    print(f"[parser] Output: {COURSES_PATH}")


if __name__ == "__main__":
    main()
