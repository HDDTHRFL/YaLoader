from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

COOKIES_HEADER_PREFIXES: Final[tuple[str, ...]] = (
    "# Netscape HTTP Cookie File",
    "# HTTP Cookie File",
)
PRIMARY_COOKIES_HEADER: Final = "# Netscape HTTP Cookie File"
TEMPORARY_COOKIES_FILE_SUFFIX: Final = ".tmp"
COMPACT_TEMPORARY_COOKIES_FILE_SUFFIX: Final = ".compact.tmp"
COOKIES_FILE_ENCODING: Final = "utf-8"

BYTES_PER_KIB: Final = 1024
BYTES_PER_MIB: Final = BYTES_PER_KIB * BYTES_PER_KIB
MAX_RECOMMENDED_COOKIES_FILE_SIZE_BYTES: Final = 50 * BYTES_PER_MIB

NETSCAPE_COOKIE_FIELDS_COUNT: Final = 7


class CookiesFileImportError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CookiesFileService:
    target_file: Path

    def import_cookies_file(self, *, source_file: Path) -> Path:
        validate_cookies_file(source_file=source_file)

        if is_same_filesystem_file(left_path=source_file, right_path=self.target_file):
            compact_cookies_file_in_place(file_path=self.target_file)
            validate_cookies_file(source_file=self.target_file)
            return self.target_file

        self.target_file.parent.mkdir(parents=True, exist_ok=True)
        temporary_file = self.target_file.with_name(
            f"{self.target_file.name}{TEMPORARY_COOKIES_FILE_SUFFIX}",
        )

        try:
            compact_cookies_file(
                source_file=source_file,
                target_file=temporary_file,
            )
            validate_cookies_file(source_file=temporary_file)
            temporary_file.replace(self.target_file)
        except OSError as error:
            raise CookiesFileImportError(
                f"не удалось импортировать cookies.txt: {error}"
            ) from error
        finally:
            remove_file_if_exists(file_path=temporary_file)

        return self.target_file


def validate_cookies_file(*, source_file: Path) -> None:
    if not source_file.is_file():
        raise CookiesFileImportError(f"файл не найден: {source_file}")

    try:
        first_line = read_first_line(source_file=source_file)
    except OSError as error:
        raise CookiesFileImportError(f"файл недоступен: {error}") from error

    if not first_line:
        raise CookiesFileImportError("файл пустой или недоступен")

    if not first_line.startswith(COOKIES_HEADER_PREFIXES):
        raise CookiesFileImportError("подозрительный формат cookies.txt")

    try:
        has_relevant_cookies = has_usable_cookies(source_file=source_file)
    except OSError as error:
        raise CookiesFileImportError(f"файл недоступен: {error}") from error

    if not has_relevant_cookies:
        raise CookiesFileImportError("файл не содержит подходящих cookies")


def compact_cookies_file_in_place(*, file_path: Path) -> None:
    temporary_file = file_path.with_name(f"{file_path.name}{COMPACT_TEMPORARY_COOKIES_FILE_SUFFIX}")

    try:
        compact_cookies_file(
            source_file=file_path,
            target_file=temporary_file,
        )
        temporary_file.replace(file_path)
    finally:
        remove_file_if_exists(file_path=temporary_file)


def compact_cookies_file(*, source_file: Path, target_file: Path) -> None:
    target_file.parent.mkdir(parents=True, exist_ok=True)

    kept_cookie_lines = 0

    with (
        source_file.open(mode="r", encoding=COOKIES_FILE_ENCODING, errors="replace") as source,
        target_file.open(mode="w", encoding=COOKIES_FILE_ENCODING, newline="\n") as target,
    ):
        target.write(f"{PRIMARY_COOKIES_HEADER}\n")

        for raw_line in source:
            normalized_line = raw_line.rstrip("\r\n")

            if not is_usable_cookie_line(line=normalized_line):
                continue

            target.write(f"{normalized_line}\n")
            kept_cookie_lines += 1

    if kept_cookie_lines == 0:
        remove_file_if_exists(file_path=target_file)
        raise CookiesFileImportError("файл не содержит подходящих cookies")


def has_usable_cookies(*, source_file: Path) -> bool:
    with source_file.open(mode="r", encoding=COOKIES_FILE_ENCODING, errors="replace") as file:
        return any(is_usable_cookie_line(line=line) for line in file)


def is_usable_cookie_line(*, line: str) -> bool:
    return parse_netscape_cookie_domain(line=line) is not None


def parse_netscape_cookie_domain(*, line: str) -> str | None:
    normalized_line = line.strip()

    if not normalized_line or normalized_line.startswith("#"):
        return None

    fields = normalized_line.split("\t")

    if len(fields) < NETSCAPE_COOKIE_FIELDS_COUNT:
        fields = normalized_line.split(maxsplit=NETSCAPE_COOKIE_FIELDS_COUNT - 1)

    if len(fields) < NETSCAPE_COOKIE_FIELDS_COUNT:
        return None

    domain = fields[0].strip().lstrip(".").casefold()

    if not domain:
        return None

    return domain


def is_large_cookies_file(*, source_file: Path) -> bool:
    return source_file.stat().st_size > MAX_RECOMMENDED_COOKIES_FILE_SIZE_BYTES


def format_cookies_file_size(*, size_bytes: int) -> str:
    if size_bytes >= BYTES_PER_MIB:
        return f"{size_bytes / BYTES_PER_MIB:.1f} МБ"

    if size_bytes >= BYTES_PER_KIB:
        return f"{size_bytes / BYTES_PER_KIB:.1f} КБ"

    return f"{size_bytes} байт"


def read_first_line(*, source_file: Path) -> str:
    with source_file.open(mode="r", encoding=COOKIES_FILE_ENCODING, errors="replace") as file:
        return file.readline().strip()


def is_same_filesystem_file(*, left_path: Path, right_path: Path) -> bool:
    try:
        return left_path.samefile(right_path)
    except OSError:
        return left_path.resolve() == right_path.resolve()


def remove_file_if_exists(*, file_path: Path) -> None:
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        return
