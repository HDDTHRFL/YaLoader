from __future__ import annotations

import hashlib
import string
from pathlib import Path

SHA256_HEX_LENGTH = 64
FILE_READ_CHUNK_SIZE_BYTES = 1024 * 1024
HEX_DIGITS = frozenset(string.hexdigits.casefold())


class ChecksumError(ValueError):
    pass


def calculate_file_sha256(*, file_path: Path) -> str:
    digest = hashlib.sha256()

    with file_path.open("rb") as file:
        while chunk := file.read(FILE_READ_CHUNK_SIZE_BYTES):
            digest.update(chunk)

    return digest.hexdigest()


def parse_sha256_text(*, text: str) -> str:
    for line in text.splitlines():
        stripped_line = line.strip()

        if not stripped_line:
            continue

        candidate = stripped_line.split()[0].strip().casefold()
        validate_sha256_hex(value=candidate)

        return candidate

    raise ChecksumError("sha256 text is empty")


def validate_sha256_hex(*, value: str) -> None:
    if len(value) != SHA256_HEX_LENGTH:
        raise ChecksumError(f"invalid sha256 length: {len(value)}")

    if any(character not in HEX_DIGITS for character in value):
        raise ChecksumError("sha256 contains non-hex characters")


def verify_file_sha256(*, file_path: Path, expected_sha256: str) -> None:
    normalized_expected_sha256 = expected_sha256.strip().casefold()
    validate_sha256_hex(value=normalized_expected_sha256)

    actual_sha256 = calculate_file_sha256(file_path=file_path)

    if actual_sha256 != normalized_expected_sha256:
        raise ChecksumError(
            f"sha256 mismatch for {file_path}: expected {normalized_expected_sha256}, "
            f"actual {actual_sha256}",
        )
