from __future__ import annotations

from uuid import uuid4

from yaloader.application.dto.prepared_download import PreparedDownload
from yaloader.application.services.prepared_download_cache import PreparedDownloadCache


def test_cache_saves_and_returns_prepared_download() -> None:
    cache = PreparedDownloadCache()
    prepared_download = PreparedDownload(
        task_id=uuid4(),
        url="https://www.youtube.com/watch?v=test001",
        title="Test video",
        raw_info={"title": "Test video"},
    )

    cache.save(prepared_download=prepared_download)

    assert cache.get(task_id=prepared_download.task_id) == prepared_download
    assert cache.contains(task_id=prepared_download.task_id)
    assert cache.count() == 1


def test_cache_removes_prepared_download() -> None:
    cache = PreparedDownloadCache()
    prepared_download = PreparedDownload(
        task_id=uuid4(),
        url="https://www.youtube.com/watch?v=test001",
    )
    cache.save(prepared_download=prepared_download)

    removed_download = cache.remove(task_id=prepared_download.task_id)

    assert removed_download == prepared_download
    assert cache.get(task_id=prepared_download.task_id) is None
    assert not cache.contains(task_id=prepared_download.task_id)
    assert cache.count() == 0


def test_cache_clear_returns_removed_count() -> None:
    cache = PreparedDownloadCache()
    first_download = PreparedDownload(
        task_id=uuid4(),
        url="https://www.youtube.com/watch?v=test001",
    )
    second_download = PreparedDownload(
        task_id=uuid4(),
        url="https://www.youtube.com/watch?v=test002",
    )
    cache.save(prepared_download=first_download)
    cache.save(prepared_download=second_download)

    removed_count = cache.clear()

    assert removed_count == 2
    assert cache.count() == 0
