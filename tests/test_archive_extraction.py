from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from yaloader.infrastructure.tools.archive_extraction import (
    UnsafeArchiveMemberError,
    safe_extract_zip_archive,
)


def test_safe_extract_zip_archive_extracts_safe_members(tmp_path: Path) -> None:
    archive_file = tmp_path / "archive.zip"
    destination_dir = tmp_path / "extracted"

    with ZipFile(archive_file, mode="w") as archive:
        archive.writestr("root/bin/ffmpeg.exe", "fake ffmpeg")

    safe_extract_zip_archive(
        archive_file=archive_file,
        destination_dir=destination_dir,
    )

    assert (destination_dir / "root" / "bin" / "ffmpeg.exe").read_text(
        encoding="utf-8",
    ) == "fake ffmpeg"


def test_safe_extract_zip_archive_rejects_path_traversal(tmp_path: Path) -> None:
    archive_file = tmp_path / "archive.zip"
    destination_dir = tmp_path / "extracted"

    with ZipFile(archive_file, mode="w") as archive:
        archive.writestr("../evil.txt", "evil")

    try:
        safe_extract_zip_archive(
            archive_file=archive_file,
            destination_dir=destination_dir,
        )
    except UnsafeArchiveMemberError as error:
        assert "path traversal" in str(error)
    else:
        raise AssertionError("UnsafeArchiveMemberError was not raised")

    assert not (tmp_path / "evil.txt").exists()


def test_safe_extract_zip_archive_rejects_drive_qualified_member(tmp_path: Path) -> None:
    archive_file = tmp_path / "archive.zip"
    destination_dir = tmp_path / "extracted"

    with ZipFile(archive_file, mode="w") as archive:
        archive.writestr("C:/evil.txt", "evil")

    try:
        safe_extract_zip_archive(
            archive_file=archive_file,
            destination_dir=destination_dir,
        )
    except UnsafeArchiveMemberError as error:
        assert "drive-qualified" in str(error)
    else:
        raise AssertionError("UnsafeArchiveMemberError was not raised")
