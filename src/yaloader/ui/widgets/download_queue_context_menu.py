from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QWidget

from yaloader.domain.entities.download_task import DownloadTask
from yaloader.domain.enums import DownloadStatus
from yaloader.ui.widgets.context_menu_actions import (
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

    copy_action = QAction(
        "Копировать ссылки" if len(selected_tasks) > 1 else "Копировать ссылку",
        context_menu,
    )
    context_menu.addAction(copy_action)

    download_action: QAction | None = None
    cancel_action: QAction | None = None
    downloadable_task_ids: tuple[UUID, ...] = ()

    if len(selected_tasks) == 1 and selected_tasks[0].status is DownloadStatus.RUNNING:
        cancel_action = add_menu_button_action(
            menu=context_menu,
            text="Отменить загрузку",
            object_name="MenuDangerButton",
        )
    else:
        downloadable_task_ids = tuple(
            task.task_id for task in selected_tasks if task.status in DOWNLOADABLE_STATUSES
        )

        if downloadable_task_ids:
            download_action = QAction(
                "Скачать файлы" if len(downloadable_task_ids) > 1 else "Скачать файл",
                context_menu,
            )
            context_menu.addAction(download_action)

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

    if cancel_action is not None and selected_action == cancel_action:
        return DownloadQueueContextMenuResult(
            action=DownloadQueueContextAction.CANCEL,
            task_ids=(selected_tasks[0].task_id,),
        )

    if download_action is not None and selected_action == download_action:
        return DownloadQueueContextMenuResult(
            action=DownloadQueueContextAction.DOWNLOAD,
            task_ids=downloadable_task_ids,
        )

    if selected_action == remove_action:
        return DownloadQueueContextMenuResult(
            action=DownloadQueueContextAction.REMOVE,
            task_ids=selected_task_ids,
        )

    return None
