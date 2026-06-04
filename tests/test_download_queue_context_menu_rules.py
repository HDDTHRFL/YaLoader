from __future__ import annotations

from pathlib import Path

from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadMode, DownloadStatus, OutputFormat, VideoQuality
from yaloader.domain.value_objects.media_url import MediaUrl
from yaloader.ui.widgets.download_queue.context_menu import (
    can_show_remove_action,
    collect_cancelable_task_ids,
    collect_downloadable_task_ids,
)


def test_pending_prepared_task_is_cancelable_and_not_downloadable(tmp_path: Path) -> None:
    task = create_task(
        target_dir=tmp_path,
        url_suffix="prepared001",
        status=DownloadStatus.PENDING,
    )

    assert collect_cancelable_task_ids(
        selected_tasks=(task,),
        prepared_task_ids=(task.task_id,),
    ) == (task.task_id,)
    assert (
        collect_downloadable_task_ids(
            selected_tasks=(task,),
            prepared_task_ids=(task.task_id,),
        )
        == ()
    )
    assert not can_show_remove_action(
        selected_tasks=(task,),
        prepared_task_ids=(task.task_id,),
    )


def test_pending_unprepared_task_is_downloadable_and_removable(tmp_path: Path) -> None:
    task = create_task(
        target_dir=tmp_path,
        url_suffix="pending001",
        status=DownloadStatus.PENDING,
    )

    assert (
        collect_cancelable_task_ids(
            selected_tasks=(task,),
            prepared_task_ids=(),
        )
        == ()
    )
    assert collect_downloadable_task_ids(
        selected_tasks=(task,),
        prepared_task_ids=(),
    ) == (task.task_id,)
    assert can_show_remove_action(
        selected_tasks=(task,),
        prepared_task_ids=(),
    )


def test_running_task_is_cancelable_and_not_removable(tmp_path: Path) -> None:
    task = create_task(
        target_dir=tmp_path,
        url_suffix="running001",
        status=DownloadStatus.RUNNING,
    )

    assert collect_cancelable_task_ids(
        selected_tasks=(task,),
        prepared_task_ids=(),
    ) == (task.task_id,)
    assert (
        collect_downloadable_task_ids(
            selected_tasks=(task,),
            prepared_task_ids=(),
        )
        == ()
    )
    assert not can_show_remove_action(
        selected_tasks=(task,),
        prepared_task_ids=(),
    )


def test_mixed_selection_splits_downloadable_and_cancelable_tasks(tmp_path: Path) -> None:
    prepared_task = create_task(
        target_dir=tmp_path,
        url_suffix="prepared001",
        status=DownloadStatus.PENDING,
    )
    pending_task = create_task(
        target_dir=tmp_path,
        url_suffix="pending002",
        status=DownloadStatus.PENDING,
    )
    running_task = create_task(
        target_dir=tmp_path,
        url_suffix="running003",
        status=DownloadStatus.RUNNING,
    )

    assert collect_cancelable_task_ids(
        selected_tasks=(prepared_task, pending_task, running_task),
        prepared_task_ids=(prepared_task.task_id,),
    ) == (prepared_task.task_id, running_task.task_id)
    assert collect_downloadable_task_ids(
        selected_tasks=(prepared_task, pending_task, running_task),
        prepared_task_ids=(prepared_task.task_id,),
    ) == (pending_task.task_id,)
    assert not can_show_remove_action(
        selected_tasks=(prepared_task, pending_task, running_task),
        prepared_task_ids=(prepared_task.task_id,),
    )


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
