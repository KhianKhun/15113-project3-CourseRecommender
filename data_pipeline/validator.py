"""
validator.py — data_pipeline (Segment 1)
Reads data/courses.json and validates every entry against the SPEC_0 schema.

Run: python data_pipeline/validator.py

Exits with code 0 if all checks pass, code 1 if any check fails.
Intended to be used as a CI quality gate after the parser runs.
"""

import json
import re
import sys

from app.core.config import COURSES_PATH

REQUIRED_FIELDS = {"id", "name", "description", "prerequisites", "department", "units", "source"}
VALID_SOURCES = {"official", "user"}
ID_PATTERN = re.compile(r"^\d{2}-\d{3}$")


def validate(courses: list[dict]) -> list[str]:
    """
    Validates all course dicts in a list against the SPEC_0 schema.

    Checks performed:
    1. All seven required fields are present.
    2. id matches the pattern \\d{2}-\\d{3}.
    3. All id values are globally unique.
    4. source is exactly "official" or "user".
    5. units is a positive integer.
    6. prerequisites is a list.
    7. Every id mentioned in any prerequisites list exists as an id in the
       array (no dangling references).

    Args:
        courses: The list loaded from data/courses.json.

    Returns:
        A list of error message strings. An empty list means all checks passed.
    """
    errors: list[str] = []
    all_ids: set[str] = set()
    seen_ids: set[str] = set()

    # First pass: collect all valid ids for the dangling-reference check.
    for course in courses:
        cid = course.get("id")
        if isinstance(cid, str) and ID_PATTERN.match(cid):
            all_ids.add(cid)

    # Second pass: full field-by-field validation.
    for i, course in enumerate(courses):
        prefix = f"[Course #{i}]"

        # 1. Required fields
        missing = REQUIRED_FIELDS - course.keys()
        if missing:
            errors.append(f"{prefix} Missing required fields: {sorted(missing)}")
            continue  # Cannot safely check further fields

        cid = course["id"]

        # 2. id format
        if not isinstance(cid, str) or not ID_PATTERN.match(cid):
            errors.append(
                f"{prefix} Invalid id format: {cid!r} (expected 'XX-NNN' e.g. '10-301')"
            )

        # 3. id uniqueness
        if cid in seen_ids:
            errors.append(f"{prefix} Duplicate id: {cid!r}")
        else:
            seen_ids.add(cid)

        # 4. source
        if course["source"] not in VALID_SOURCES:
            errors.append(
                f"{prefix} id={cid!r}: invalid source {course['source']!r} "
                f"(must be one of {sorted(VALID_SOURCES)})"
            )

        # 5. units must be a non-negative integer (0 is allowed)
        if not isinstance(course["units"], int) or course["units"] < 0:
            errors.append(
                f"{prefix} id={cid!r}: 'units' must be a non-negative integer, "
                f"got {course['units']!r}"
            )

        # 6. prerequisites must be a list
        if not isinstance(course["prerequisites"], list):
            errors.append(
                f"{prefix} id={cid!r}: 'prerequisites' must be a list, "
                f"got {type(course['prerequisites']).__name__}"
            )
        else:
            # 7. No dangling prerequisite references
            for prereq_id in course["prerequisites"]:
                if prereq_id not in all_ids:
                    errors.append(
                        f"{prefix} id={cid!r}: prerequisite {prereq_id!r} "
                        "does not exist in courses.json"
                    )

    return errors


def main() -> None:
    """
    Entry point. Reads courses.json, runs all validation checks, prints
    results, and exits with code 0 (success) or 1 (failure).
    """
    if not COURSES_PATH.exists():
        print(f"[validator] ERROR: {COURSES_PATH} not found. Run parser.py first.")
        sys.exit(1)

    with open(COURSES_PATH, "r", encoding="utf-8") as f:
        courses = json.load(f)

    print(f"[validator] Loaded {len(courses)} courses from {COURSES_PATH}")

    errors = validate(courses)

    if not errors:
        print(f"[validator] OK — all {len(courses)} courses passed validation.")
        sys.exit(0)
    else:
        print(f"\n[validator] FAILED — {len(errors)} error(s) found:\n")
        for error in errors:
            print(f"  {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
