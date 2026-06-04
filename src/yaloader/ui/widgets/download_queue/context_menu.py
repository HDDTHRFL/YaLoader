from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QWidget, QWidgetAction

from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadStatus
from yaloader.ui.widgets.common.context_menu_actions import (
    add_menu_action,
    add_menu_button_action,
    create_context_menu,
)

DOWNLOADABLE_STATUSES = frozenset(
    {
        DownloadStatus.PENDING,
        DownloadStatus.FAILED,
        DownloadStatus.CANCELED,
    }
)


class DownloadQueueContextAction(StrEnum):
    COPY = "copy"
    DOWNLOAD = "download"
    CANCEL = "cancel"
    REMOVE = "remove"


@dataclass(frozen=True, slots=True)
class DownloadQueueContextMenuResult:
    action: DownloadQueueContextAction
    task_ids: tuple[UUID, ...]


def show_download_queue_context_menu(
    *,
    parent: QWidget,
    global_position: QPoint,
    selected_tasks: Sequence[DownloadTask],
    selected_task_ids: tuple[UUID, ...],
) -> DownloadQueueContextMenuResult | None:
    if not selected_tasks:
        return None

    context_menu = create_context_menu(parent=parent)

    copy_action = add_menu_action(
        menu=context_menu,
        text="Копировать ссылки" if len(selected_tasks) > 1 else "Копировать ссылку",
    )

    downloadable_task_ids = collect_downloadable_task_ids(selected_tasks=selected_tasks)
    running_task_ids = collect_running_task_ids(selected_tasks=selected_tasks)

    download_action: QWidgetAction | None = None
    cancel_action: QWidgetAction | None = None
    remove_action: QWidgetAction | None = None

    if downloadable_task_ids:
        download_action = add_menu_action(
            menu=context_menu,
            text="Скачать файлы" if len(downloadable_task_ids) > 1 else "Скачать файл",
        )

    if running_task_ids:
        cancel_action = add_menu_button_action(
            menu=context_menu,
            text="Отменить загрузки" if len(running_task_ids) > 1 else "Отменить загрузку",
            object_name="MenuDangerButton",
        )

    if can_show_remove_action(selected_tasks=selected_tasks):
        remove_action = add_menu_button_action(
            menu=context_menu,
            text="Удалить выбранные" if len(selected_task_ids) > 1 else "Удалить из очереди",
            object_name="MenuDangerButton",
        )

    selected_action = context_menu.exec(global_position)

    if selected_action is None:
        return None

    if selected_action == copy_action:
        return DownloadQueueContextMenuResult(
            action=DownloadQueueContextAction.COPY,
            task_ids=selected_task_ids,
        )

    if download_action is not None and selected_action == download_action:
        return DownloadQueueContextMenuResult(
            action=DownloadQueueContextAction.DOWNLOAD,
            task_ids=downloadable_task_ids,
        )

    if cancel_action is not None and selected_action == cancel_action:
        return DownloadQueueContextMenuResult(
            action=DownloadQueueContextAction.CANCEL,
            task_ids=running_task_ids,
        )

    if remove_action is not None and selected_action == remove_action:
        return DownloadQueueContextMenuResult(
            action=DownloadQueueContextAction.REMOVE,
            task_ids=selected_task_ids,
        )

    return None


def collect_downloadable_task_ids(*, selected_tasks: Sequence[DownloadTask]) -> tuple[UUID, ...]:
    return tuple(task.task_id for task in selected_tasks if task.status in DOWNLOADABLE_STATUSES)


def collect_running_task_ids(*, selected_tasks: Sequence[DownloadTask]) -> tuple[UUID, ...]:
    return tuple(task.task_id for task in selected_tasks if task.status is DownloadStatus.RUNNING)


def can_show_remove_action(*, selected_tasks: Sequence[DownloadTask]) -> bool:
    return not any(task.status is DownloadStatus.RUNNING for task in selected_tasks)
