from __future__ import annotations

from pathlib import Path

from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadMode, DownloadStatus, OutputFormat, VideoQuality
from yaloader.domain.value_objects.media_url import MediaUrl
from yaloader.ui.widgets.download_queue.context_menu import (
    can_show_remove_action,
    collect_downloadable_task_ids,
    collect_running_task_ids,
)


def test_context_menu_collects_only_running_tasks_for_cancel(tmp_path: Path) -> None:
    running_task = create_task(
        target_dir=tmp_path,
        url_suffix="running001",
        status=DownloadStatus.RUNNING,
    )
    pending_task = create_task(
        target_dir=tmp_path,
        url_suffix="pending002",
        status=DownloadStatus.PENDING,
    )

    assert collect_running_task_ids(selected_tasks=(running_task, pending_task)) == (
        running_task.task_id,
    )


def test_context_menu_keeps_pending_tasks_downloadable_when_running_task_is_selected(
    tmp_path: Path,
) -> None:
    running_task = create_task(
        target_dir=tmp_path,
        url_suffix="running001",
        status=DownloadStatus.RUNNING,
    )
    pending_task = create_task(
        target_dir=tmp_path,
        url_suffix="pending002",
        status=DownloadStatus.PENDING,
    )

    assert collect_downloadable_task_ids(selected_tasks=(running_task, pending_task)) == (
        pending_task.task_id,
    )


def test_context_menu_hides_remove_action_when_running_task_is_selected(tmp_path: Path) -> None:
    running_task = create_task(
        target_dir=tmp_path,
        url_suffix="running001",
        status=DownloadStatus.RUNNING,
    )
    pending_task = create_task(
        target_dir=tmp_path,
        url_suffix="pending002",
        status=DownloadStatus.PENDING,
    )

    assert not can_show_remove_action(selected_tasks=(running_task,))
    assert not can_show_remove_action(selected_tasks=(running_task, pending_task))
    assert can_show_remove_action(selected_tasks=(pending_task,))


def create_task(
    *,
    target_dir: Path,
    url_suffix: str,
    status: DownloadStatus,
) -> DownloadTask:
    task = DownloadTask.create(
        url=MediaUrl(value=f"https://www.youtube.com/watch?v={url_suffix}"),
        target_dir=target_dir,
        mode=DownloadMode.VIDEO,
        output_format=OutputFormat.MP4,
        video_quality=VideoQuality.BEST,
        include_playlist=False,
    )

    return task.with_status(status=status)
