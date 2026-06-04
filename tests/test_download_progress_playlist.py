from __future__ import annotations

from uuid import uuid4

from yaloader.infrastructure.ytdlp.downloader import build_downloading_progress


def test_build_downloading_progress_extracts_playlist_data() -> None:
    task_id = uuid4()

    progress = build_downloading_progress(
        task_id=task_id,
        progress_info={
            "status": "downloading",
            "downloaded_bytes": 50,
            "total_bytes": 100,
            "speed": 1024,
            "info_dict": {
                "title": "Current video",
                "playlist_title": "Playlist title",
                "playlist_index": 3,
                "n_entries": 12,
            },
        },
    )

    assert progress.task_id == task_id
    assert progress.playlist_index == 3
    assert progress.playlist_count == 12
    assert progress.current_title == "Current video"
    assert progress.playlist_title == "Playlist title"
