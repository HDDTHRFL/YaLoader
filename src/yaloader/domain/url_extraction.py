from __future__ import annotations

import re
from collections.abc import Iterable
from re import Pattern
from typing import Final

HTTP_URL_PATTERN: Final[Pattern[str]] = re.compile(
    r"https?://[^\s<>'\"]+",
    flags=re.IGNORECASE,
)

TRAILING_URL_PUNCTUATION: Final = ".,;:!?)]}»"


def extract_first_http_url(*, text: str) -> str | None:
    for match in HTTP_URL_PATTERN.finditer(text):
        normalized_url = normalize_url_candidate(candidate=match.group(0))

        if normalized_url:
            return normalized_url

    return None


def extract_first_http_url_from_candidates(*, candidates: Iterable[str]) -> str | None:
    for candidate in candidates:
        normalized_candidate = normalize_url_candidate(candidate=candidate)

        if is_http_url(text=normalized_candidate):
            return normalized_candidate

        extracted_url = extract_first_http_url(text=normalized_candidate)

        if extracted_url is not None:
            return extracted_url

    return None


def normalize_url_candidate(*, candidate: str) -> str:
    return candidate.strip().rstrip(TRAILING_URL_PUNCTUATION)


def is_http_url(*, text: str) -> bool:
    normalized_text = text.casefold()
    return normalized_text.startswith(("http://", "https://"))
