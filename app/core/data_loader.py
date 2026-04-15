"""
data_loader.py — app/core
Loads and merges course data from courses.json and user_courses.json.
"""

import json

from app.core.config import COURSES_PATH, USER_COURSES_PATH


def load_courses() -> list[dict]:
    """
    Load and merge courses.json and user_courses.json.

    Returns a list of course dicts with a fixed ordering:
    official courses first (sorted by id), then user courses (sorted by id).
    If user_courses.json does not exist, it is created as an empty array.

    Returns:
        A merged, sorted list of course dicts.
    """
    # Load official courses
    with open(COURSES_PATH, "r", encoding="utf-8") as f:
        official = json.load(f)
    official_sorted = sorted(official, key=lambda c: c["id"])

    # Load or initialize user courses
    if not USER_COURSES_PATH.exists():
        USER_COURSES_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(USER_COURSES_PATH, "w", encoding="utf-8") as f:
            json.dump([], f)
        user = []
    else:
        with open(USER_COURSES_PATH, "r", encoding="utf-8") as f:
            user = json.load(f)
    user_sorted = sorted(user, key=lambda c: c["id"])

    return official_sorted + user_sorted


def save_user_course(course: dict) -> None:
    """
    Append a new course to user_courses.json.

    Validates schema before writing. Raises ValueError if schema is invalid.

    Args:
        course: A course dict conforming to the SPEC_0 schema.
            'source' will be forced to "user".

    Raises:
        ValueError: If any required field is missing or malformed.
    """
    _validate_schema(course)

    course = {**course, "source": "user"}

    if USER_COURSES_PATH.exists():
        with open(USER_COURSES_PATH, "r", encoding="utf-8") as f:
            existing = json.load(f)
    else:
        existing = []

    # Check for duplicate id
    existing_ids = {c["id"] for c in existing}
    if course["id"] in existing_ids:
        raise ValueError(f"Course id '{course['id']}' already exists in user_courses.json")

    existing.append(course)

    USER_COURSES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(USER_COURSES_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)


def _validate_schema(course: dict) -> None:
    """
    Validates that a course dict matches the SPEC_0 schema.

    Args:
        course: The course dict to check.

    Raises:
        ValueError: If any required field is missing or has wrong type.
    """
    import re
    required = {"id", "name", "description", "prerequisites", "department", "units"}
    missing = required - course.keys()
    if missing:
        raise ValueError(f"Missing required fields: {sorted(missing)}")

    if not re.fullmatch(r"\d{2}-\d{3}", str(course.get("id", ""))):
        raise ValueError(f"Invalid id format: '{course['id']}' (expected 'XX-NNN')")

    if not isinstance(course["name"], str) or not course["name"].strip():
        raise ValueError("Field 'name' must be a non-empty string")

    if not isinstance(course["description"], str) or not course["description"].strip():
        raise ValueError("Field 'description' must be a non-empty string")

    if not isinstance(course["prerequisites"], list):
        raise ValueError("Field 'prerequisites' must be a list")

    if not isinstance(course["units"], int) or course["units"] < 0:
        raise ValueError("Field 'units' must be a non-negative integer")


def get_course_by_id(course_id: str, courses: list[dict]) -> dict | None:
    """
    Returns the course dict for a given id, or None if not found.

    Args:
        course_id: The course id string to look up.
        courses: The merged course list from load_courses().

    Returns:
        The matching course dict, or None if course_id is not present.
    """
    for course in courses:
        if course["id"] == course_id:
            return course
    return None
