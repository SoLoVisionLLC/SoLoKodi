import re

from .constants import KIDS_KEYWORDS


def normalize_title(value):
    if not value:
        return ""
    text = value.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def looks_like_kids_content(title, extra=""):
    haystack = normalize_title("{0} {1}".format(title or "", extra or ""))
    if not haystack:
        return False
    return any(keyword in haystack for keyword in KIDS_KEYWORDS)


def titles_match(left, right):
    left_norm = normalize_title(left)
    right_norm = normalize_title(right)
    if not left_norm or not right_norm:
        return False
    if left_norm == right_norm:
        return True
    if left_norm in right_norm or right_norm in left_norm:
        return True
    left_words = set(left_norm.split())
    right_words = set(right_norm.split())
    if len(left_words) < 2 or len(right_words) < 2:
        return False
    overlap = left_words & right_words
    return len(overlap) >= min(2, len(left_words), len(right_words))
