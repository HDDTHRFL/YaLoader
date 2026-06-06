from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

COOKIES_HEADER_PREFIXES = (
    "# Netscape HTTP Cookie File",
    "# HTTP Cookie File",
)

TEMPORARY_COOKIES_FILE_SUFFIX = ".tmp"


class CookiesFileImportError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CookiesFileService:
    target_file: Path

    def import_cookies_file(self, *, source_file: Path) -> Path:
        validate_cookies_file(source_file=source_file)

        if is_same_filesystem_file(left_path=source_file, right_path=self.target_file):
            return self.target_file

        self.target_file.parent.mkdir(parents=True, exist_ok=True)
        temporary_file = self.target_file.with_name(
            f"{self.target_file.name}{TEMPORARY_COOKIES_FILE_SUFFIX}",
        )

        try:
            shutil.copy2(source_file, temporary_file)
            temporary_file.replace(self.target_file)
        except OSError as error:
            raise CookiesFileImportError(
                f"не удалось импортировать cookies.txt: {error}"
            ) from error

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


def read_first_line(*, source_file: Path) -> str:
    with source_file.open(mode="r", encoding="utf-8", errors="replace") as file:
        return file.readline().strip()


def is_same_filesystem_file(*, left_path: Path, right_path: Path) -> bool:
    try:
        return left_path.samefile(right_path)
    except OSError:
        return left_path.resolve() == right_path.resolve()
