from __future__ import annotations

from typing import cast

from PyQt6.QtCore import QItemSelectionModel, QModelIndex
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QWidget


def get_selected_rows(*, table: QTableWidget) -> tuple[int, ...]:
    selection_model = table.selectionModel()

    if isinstance(selection_model, QItemSelectionModel):
        selected_rows = sorted({index.row() for index in selection_model.selectedRows()})

        if selected_rows:
            return tuple(selected_rows)

    return tuple(sorted({index.row() for index in table.selectedIndexes()}))


def is_row_selected(*, table: QTableWidget, row_index: int) -> bool:
    return row_index in get_selected_rows(table=table)


def clear_current_cell_focus(*, table: QTableWidget) -> None:
    selection_model = table.selectionModel()

    if isinstance(selection_model, QItemSelectionModel):
        selection_model.setCurrentIndex(
            QModelIndex(),
            QItemSelectionModel.SelectionFlag.NoUpdate,
        )

    table.setCurrentIndex(QModelIndex())

    viewport = cast(QWidget, table.viewport())
    viewport.update()


def prepare_right_click_selection(
    *,
    table: QTableWidget,
    clicked_item: QTableWidgetItem,
) -> None:
    row_index = clicked_item.row()

    if not is_row_selected(table=table, row_index=row_index):
        table.clearSelection()
        table.selectRow(row_index)

    table.setFocus()

    viewport = cast(QWidget, table.viewport())
    viewport.update()
