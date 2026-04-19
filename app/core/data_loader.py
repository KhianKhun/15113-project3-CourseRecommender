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
