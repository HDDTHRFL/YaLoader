from __future__ import annotations

import shutil
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile, ZipInfo

MAX_ARCHIVE_MEMBER_SIZE_BYTES = 2 * 1024 * 1024 * 1024


class ArchiveExtractionError(RuntimeError):
    pass


class UnsafeArchiveMemberError(ArchiveExtractionError):
    pass


def safe_extract_zip_archive(*, archive_file: Path, destination_dir: Path) -> None:
    try:
        with ZipFile(archive_file) as archive:
            for member in archive.infolist():
                extract_zip_member(member=member, archive=archive, destination_dir=destination_dir)
    except BadZipFile as error:
        raise ArchiveExtractionError(f"zip archive is invalid: {archive_file}") from error


def extract_zip_member(
    *,
    member: ZipInfo,
    archive: ZipFile,
    destination_dir: Path,
) -> None:
    relative_path = build_safe_relative_member_path(member=member)

    if relative_path is None:
        return

    if member.file_size > MAX_ARCHIVE_MEMBER_SIZE_BYTES:
        raise ArchiveExtractionError(
            f"archive member is too large: {member.filename}",
        )

    destination_path = destination_dir / relative_path

    if member.is_dir():
        destination_path.mkdir(parents=True, exist_ok=True)
        return

    destination_path.parent.mkdir(parents=True, exist_ok=True)

    with archive.open(member) as source_file, destination_path.open("wb") as destination_file:
        shutil.copyfileobj(source_file, destination_file)


def build_safe_relative_member_path(*, member: ZipInfo) -> Path | None:
    normalized_name = member.filename.replace("\\", "/").strip()

    if not normalized_name:
        return None

    pure_path = PurePosixPath(normalized_name)

    if pure_path.is_absolute():
        raise UnsafeArchiveMemberError(f"absolute archive path is not allowed: {member.filename}")

    safe_parts: list[str] = []

    for part in pure_path.parts:
        if part in {"", "."}:
            continue

        if part == "..":
            raise UnsafeArchiveMemberError(
                f"path traversal archive member is not allowed: {member.filename}",
            )

        if ":" in part:
            raise UnsafeArchiveMemberError(
                f"drive-qualified archive member is not allowed: {member.filename}",
            )

        safe_parts.append(part)

    if not safe_parts:
        return None

    return Path(*safe_parts)
