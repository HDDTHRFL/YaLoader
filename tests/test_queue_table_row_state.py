from __future__ import annotations

from pathlib import Path

from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadMode, OutputFormat, VideoQuality
from yaloader.domain.value_objects.media_url import MediaUrl
from yaloader.ui.widgets.download_queue.row_state import QueueTableRowState


def test_create_builds_default_row_state(tmp_path: Path) -> None:
    task = create_task(target_dir=tmp_path)

    row_state = QueueTableRowState.create(task=task)

    assert row_state.task == task
    assert row_state.is_quality_resolution_pending is False
    assert row_state.is_metadata_resolution_failed is False
    assert row_state.copy_feedback_generation is None


def test_with_task_preserves_ui_state(tmp_path: Path) -> None:
    task = create_task(target_dir=tmp_path)
    updated_task = task.with_metadata(
        title="Resolved title",
        video_quality=VideoQuality.P1080,
    )
    row_state = (
        QueueTableRowState.create(task=task)
        .with_quality_resolution_pending(is_pending=True)
        .with_metadata_resolution_failed(is_failed=True)
        .with_copy_feedback_generation(generation=7)
    )

    updated_row_state = row_state.with_task(task=updated_task)

    assert updated_row_state.task == updated_task
    assert updated_row_state.is_quality_resolution_pending is True
    assert updated_row_state.is_metadata_resolution_failed is True
    assert updated_row_state.copy_feedback_generation == 7


def test_with_quality_resolution_pending_is_immutable(tmp_path: Path) -> None:
    task = create_task(target_dir=tmp_path)
    row_state = QueueTableRowState.create(task=task)

    updated_row_state = row_state.with_quality_resolution_pending(is_pending=True)

    assert row_state.is_quality_resolution_pending is False
    assert updated_row_state.is_quality_resolution_pending is True


def test_with_metadata_resolution_failed_is_immutable(tmp_path: Path) -> None:
    task = create_task(target_dir=tmp_path)
    row_state = QueueTableRowState.create(task=task)

    updated_row_state = row_state.with_metadata_resolution_failed(is_failed=True)

    assert row_state.is_metadata_resolution_failed is False
    assert updated_row_state.is_metadata_resolution_failed is True


def test_with_copy_feedback_generation_is_immutable(tmp_path: Path) -> None:
    task = create_task(target_dir=tmp_path)
    row_state = QueueTableRowState.create(task=task)

    updated_row_state = row_state.with_copy_feedback_generation(generation=3)

    assert row_state.copy_feedback_generation is None
    assert updated_row_state.copy_feedback_generation == 3


def create_task(*, target_dir: Path) -> DownloadTask:
    return DownloadTask.create(
        url=MediaUrl("https://www.youtube.com/watch?v=test"),
        target_dir=target_dir,
        mode=DownloadMode.VIDEO,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
        include_playlist=False,
    )


def test_with_platform_icon_path_is_immutable(tmp_path: Path) -> None:
    task = create_task(target_dir=tmp_path)
    row_state = QueueTableRowState.create(task=task)
    icon_path = tmp_path / "instagram.png"

    updated_row_state = row_state.with_platform_icon_path(icon_path=icon_path)

    assert row_state.platform_icon_path is None
    assert updated_row_state.platform_icon_path == icon_path
