from __future__ import annotations

from pathlib import Path

from yaloader.application.services.cookies_file_service import (
    CookiesFileImportError,
    CookiesFileService,
    compact_cookies_file,
    compact_cookies_file_in_place,
    has_usable_cookies,
    validate_cookies_file,
)

VALID_COOKIES_TEXT = "# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t0\tTEST\tVALUE\n"
VALID_INSTAGRAM_COOKIES_TEXT = "# Netscape HTTP Cookie File\n.instagram.com\tTRUE\t/\tTRUE\t0\tSESSIONID\tVALUE\n"
MIXED_COOKIES_TEXT = (
    "# Netscape HTTP Cookie File\n"
    "# comment should be skipped\n"
    "broken line\n"
    ".example.com\tTRUE\t/\tTRUE\t0\tTRACK\tVALUE\n"
    ".youtube.com\tTRUE\t/\tTRUE\t0\tSID\tVALUE\n"
    ".google.com\tTRUE\t/\tTRUE\t0\tHSID\tVALUE\n"
    ".instagram.com\tTRUE\t/\tTRUE\t0\tSESSIONID\tVALUE\n"
)


def test_validate_cookies_file_accepts_netscape_cookies_file(tmp_path: Path) -> None:
    source_file = tmp_path / "cookies.txt"
    source_file.write_text(VALID_COOKIES_TEXT, encoding="utf-8")

    validate_cookies_file(source_file=source_file)


def test_validate_cookies_file_accepts_instagram_only_cookies_file(tmp_path: Path) -> None:
    source_file = tmp_path / "cookies.txt"
    source_file.write_text(VALID_INSTAGRAM_COOKIES_TEXT, encoding="utf-8")

    validate_cookies_file(source_file=source_file)


def test_validate_cookies_file_rejects_missing_file(tmp_path: Path) -> None:
    source_file = tmp_path / "missing-cookies.txt"

    try:
        validate_cookies_file(source_file=source_file)
    except CookiesFileImportError as error:
        assert "файл не найден" in str(error)
    else:
        raise AssertionError("CookiesFileImportError was not raised")


def test_validate_cookies_file_rejects_suspicious_file(tmp_path: Path) -> None:
    source_file = tmp_path / "cookies.txt"
    source_file.write_text("not a cookies file\n", encoding="utf-8")

    try:
        validate_cookies_file(source_file=source_file)
    except CookiesFileImportError as error:
        assert "подозрительный формат" in str(error)
    else:
        raise AssertionError("CookiesFileImportError was not raised")


def test_validate_cookies_file_rejects_file_without_usable_cookies(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "cookies.txt"
    source_file.write_text(
        "# Netscape HTTP Cookie File\n# only comment\nbroken line\n",
        encoding="utf-8",
    )

    try:
        validate_cookies_file(source_file=source_file)
    except CookiesFileImportError as error:
        assert "не содержит подходящих cookies" in str(error)
    else:
        raise AssertionError("CookiesFileImportError was not raised")


def test_compact_cookies_file_keeps_all_usable_cookie_domains(tmp_path: Path) -> None:
    source_file = tmp_path / "source-cookies.txt"
    target_file = tmp_path / "target-cookies.txt"
    source_file.write_text(MIXED_COOKIES_TEXT, encoding="utf-8")

    compact_cookies_file(source_file=source_file, target_file=target_file)

    compacted_text = target_file.read_text(encoding="utf-8")

    assert ".example.com" in compacted_text
    assert ".youtube.com" in compacted_text
    assert ".google.com" in compacted_text
    assert ".instagram.com" in compacted_text
    assert "broken line" not in compacted_text
    assert "comment should be skipped" not in compacted_text


def test_compact_cookies_file_in_place_keeps_all_usable_cookie_domains(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "cookies.txt"
    source_file.write_text(MIXED_COOKIES_TEXT, encoding="utf-8")

    compact_cookies_file_in_place(file_path=source_file)

    compacted_text = source_file.read_text(encoding="utf-8")

    assert ".example.com" in compacted_text
    assert ".youtube.com" in compacted_text
    assert ".google.com" in compacted_text
    assert ".instagram.com" in compacted_text
    assert "broken line" not in compacted_text


def test_has_usable_cookies_detects_instagram_domain(tmp_path: Path) -> None:
    source_file = tmp_path / "cookies.txt"
    source_file.write_text(VALID_INSTAGRAM_COOKIES_TEXT, encoding="utf-8")

    assert has_usable_cookies(source_file=source_file) is True


def test_import_cookies_file_copies_valid_file_to_target(tmp_path: Path) -> None:
    source_file = tmp_path / "exported-cookies.txt"
    target_file = tmp_path / "appdata" / "cookies.txt"
    source_file.write_text(VALID_COOKIES_TEXT, encoding="utf-8")

    imported_file = CookiesFileService(target_file=target_file).import_cookies_file(
        source_file=source_file,
    )

    assert imported_file == target_file
    assert target_file.read_text(encoding="utf-8") == VALID_COOKIES_TEXT


def test_import_cookies_file_keeps_non_youtube_cookie_domains(tmp_path: Path) -> None:
    source_file = tmp_path / "exported-cookies.txt"
    target_file = tmp_path / "appdata" / "cookies.txt"
    source_file.write_text(MIXED_COOKIES_TEXT, encoding="utf-8")

    CookiesFileService(target_file=target_file).import_cookies_file(source_file=source_file)

    compacted_text = target_file.read_text(encoding="utf-8")

    assert ".example.com" in compacted_text
    assert ".youtube.com" in compacted_text
    assert ".google.com" in compacted_text
    assert ".instagram.com" in compacted_text


def test_import_cookies_file_replaces_existing_target(tmp_path: Path) -> None:
    source_file = tmp_path / "exported-cookies.txt"
    target_file = tmp_path / "appdata" / "cookies.txt"
    target_file.parent.mkdir(parents=True)
    target_file.write_text(
        "# Netscape HTTP Cookie File\n.old\tTRUE\t/\tTRUE\t0\tOLD\tVALUE\n",
        encoding="utf-8",
    )
    source_file.write_text(VALID_INSTAGRAM_COOKIES_TEXT, encoding="utf-8")

    CookiesFileService(target_file=target_file).import_cookies_file(source_file=source_file)

    assert target_file.read_text(encoding="utf-8") == VALID_INSTAGRAM_COOKIES_TEXT


def test_import_cookies_file_accepts_existing_target_as_source(tmp_path: Path) -> None:
    target_file = tmp_path / "appdata" / "cookies.txt"
    target_file.parent.mkdir(parents=True)
    target_file.write_text(VALID_INSTAGRAM_COOKIES_TEXT, encoding="utf-8")

    imported_file = CookiesFileService(target_file=target_file).import_cookies_file(
        source_file=target_file,
    )

    assert imported_file == target_file
    assert target_file.read_text(encoding="utf-8") == VALID_INSTAGRAM_COOKIES_TEXT
