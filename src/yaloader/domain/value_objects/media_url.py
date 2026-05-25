from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class MediaUrl:
    value: str

    def __post_init__(self) -> None:
        normalized_value = self.value.strip()

        if not normalized_value:
            msg = "Media URL cannot be empty."
            raise ValueError(msg)

        parsed_url = urlparse(normalized_value)

        if parsed_url.scheme not in {"http", "https"}:
            msg = "Media URL must use http or https scheme."
            raise ValueError(msg)

        if not parsed_url.netloc:
            msg = "Media URL must contain host."
            raise ValueError(msg)

        object.__setattr__(self, "value", normalized_value)
