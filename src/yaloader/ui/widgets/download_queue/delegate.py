from __future__ import annotations

from typing import override

from PyQt6.QtCore import QModelIndex, QRect, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter
from PyQt6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

from yaloader.ui.widgets.download_queue.columns import QUEUE_ROW_HEIGHT, URL_COLUMN_INDEX

URL_TITLE_ROLE = int(Qt.ItemDataRole.UserRole)
URL_TITLE_STATE_ROLE = URL_TITLE_ROLE + 1
URL_COPY_FEEDBACK_ROLE = URL_TITLE_ROLE + 2

URL_TITLE_STATE_DEFAULT = "default"
URL_TITLE_STATE_ERROR = "error"

URL_CELL_VERTICAL_PADDING = 4
URL_TITLE_VERTICAL_SPACING = 0

CELL_TEXT_HORIZONTAL_PADDING = 8

SELECTED_ROW_BACKGROUND = QColor("#182D46")
SELECTED_ROW_HOVER_BACKGROUND = QColor("#203A59")
SELECTED_ROW_TEXT = QColor("#F0F3F6")
SELECTED_ROW_SECONDARY_TEXT = QColor("#C9D1D9")

CELL_ROW_BACKGROUND = QColor("#0D1117")
CELL_ROW_ALTERNATE_BACKGROUND = QColor("#111722")
CELL_ROW_HOVER_BACKGROUND = QColor("#161B22")

URL_TEXT = QColor("#F0F3F6")
URL_TITLE_TEXT = QColor("#8B949E")
URL_ERROR_TEXT = QColor("#FCA5A5")
URL_COPY_FEEDBACK_TEXT = QColor("#A7F3D0")


class DownloadQueueItemDelegate(QStyledItemDelegate):
    @override
    def paint(
        self,
        painter: QPainter | None,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        if painter is None:
            return

        fixed_option = QStyleOptionViewItem(option)
        fixed_option.state = fixed_option.state & ~QStyle.StateFlag.State_HasFocus

        if index.column() == URL_COLUMN_INDEX:
            self._paint_url_cell(
                painter=painter,
                option=fixed_option,
                index=index,
            )
            return

        self._paint_plain_cell(
            painter=painter,
            option=fixed_option,
            index=index,
        )

    @override
    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        base_size = super().sizeHint(option, index)

        return QSize(
            base_size.width(),
            max(base_size.height(), QUEUE_ROW_HEIGHT),
        )

    def _paint_plain_cell(
        self,
        *,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        display_text = self._get_text_data(
            index=index,
            role=Qt.ItemDataRole.DisplayRole,
        )
        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)
        lines = display_text.splitlines() or [""]
        primary_text = lines[0]
        secondary_text = lines[1] if len(lines) > 1 else ""
        has_secondary_text = bool(secondary_text.strip())
        secondary_font = self._build_title_font(base_font=option.font)
        secondary_font_metrics = QFontMetrics(secondary_font)
        primary_height = option.fontMetrics.height()
        secondary_height = secondary_font_metrics.height() if has_secondary_text else 0
        total_text_height = primary_height

        if has_secondary_text:
            total_text_height += URL_TITLE_VERTICAL_SPACING + secondary_height

        content_rect = option.rect.adjusted(
            CELL_TEXT_HORIZONTAL_PADDING,
            0,
            -CELL_TEXT_HORIZONTAL_PADDING,
            0,
        )
        top_position = option.rect.top() + max(
            URL_CELL_VERTICAL_PADDING,
            (option.rect.height() - total_text_height) // 2,
        )
        primary_rect = QRect(content_rect)
        primary_rect.setTop(top_position)
        primary_rect.setHeight(primary_height)

        painter.save()
        painter.setClipRect(option.rect)
        painter.fillRect(
            option.rect,
            self._resolve_cell_background(option=option),
        )
        painter.setFont(option.font)
        painter.setPen(SELECTED_ROW_TEXT if is_selected else URL_TEXT)
        painter.drawText(
            primary_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            option.fontMetrics.elidedText(
                primary_text,
                Qt.TextElideMode.ElideRight,
                primary_rect.width(),
            ),
        )

        if has_secondary_text:
            secondary_rect = QRect(content_rect)
            secondary_rect.setTop(primary_rect.top() + primary_height + URL_TITLE_VERTICAL_SPACING)
            secondary_rect.setHeight(secondary_height)
            painter.setFont(secondary_font)
            painter.setPen(SELECTED_ROW_SECONDARY_TEXT if is_selected else URL_TITLE_TEXT)
            painter.drawText(
                secondary_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                secondary_font_metrics.elidedText(
                    secondary_text,
                    Qt.TextElideMode.ElideRight,
                    secondary_rect.width(),
                ),
            )

        painter.restore()

    def _paint_url_cell(
        self,
        *,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        url_text = self._get_text_data(index=index, role=Qt.ItemDataRole.DisplayRole)
        title_text = self._get_text_data(index=index, role=URL_TITLE_ROLE)
        copy_feedback_text = self._get_text_data(index=index, role=URL_COPY_FEEDBACK_ROLE)

        displayed_url_text = copy_feedback_text if copy_feedback_text else url_text
        has_secondary_text = bool(title_text.strip())
        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)

        title_font = self._build_title_font(base_font=option.font)
        title_font_metrics = QFontMetrics(title_font)

        url_height = option.fontMetrics.height()
        title_height = title_font_metrics.height() if has_secondary_text else 0
        total_text_height = url_height

        if has_secondary_text:
            total_text_height += URL_TITLE_VERTICAL_SPACING + title_height

        top_position = option.rect.top() + max(
            URL_CELL_VERTICAL_PADDING,
            (option.rect.height() - total_text_height) // 2,
        )

        content_rect = option.rect.adjusted(
            CELL_TEXT_HORIZONTAL_PADDING,
            0,
            -CELL_TEXT_HORIZONTAL_PADDING,
            0,
        )

        url_rect = QRect(content_rect)
        url_rect.setTop(top_position)
        url_rect.setHeight(url_height)

        painter.save()
        painter.setClipRect(option.rect)
        painter.fillRect(
            option.rect,
            self._resolve_cell_background(option=option),
        )

        painter.setFont(option.font)
        painter.setPen(
            self._resolve_url_text_color(
                is_selected=is_selected,
                has_copy_feedback=bool(copy_feedback_text),
            )
        )
        painter.drawText(
            url_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            option.fontMetrics.elidedText(
                displayed_url_text,
                Qt.TextElideMode.ElideRight,
                url_rect.width(),
            ),
        )

        if has_secondary_text:
            title_rect = QRect(content_rect)
            title_rect.setTop(url_rect.top() + url_height + URL_TITLE_VERTICAL_SPACING)
            title_rect.setHeight(title_height)

            painter.setFont(title_font)
            painter.setPen(self._resolve_title_text_color(index=index, is_selected=is_selected))
            painter.drawText(
                title_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                title_font_metrics.elidedText(
                    title_text,
                    Qt.TextElideMode.ElideRight,
                    title_rect.width(),
                ),
            )

        painter.restore()

    def _resolve_cell_background(self, *, option: QStyleOptionViewItem) -> QColor:
        if option.state & QStyle.StateFlag.State_Selected:
            if option.state & QStyle.StateFlag.State_MouseOver:
                return SELECTED_ROW_HOVER_BACKGROUND

            return SELECTED_ROW_BACKGROUND

        if option.state & QStyle.StateFlag.State_MouseOver:
            return CELL_ROW_HOVER_BACKGROUND

        if option.features & QStyleOptionViewItem.ViewItemFeature.Alternate:
            return CELL_ROW_ALTERNATE_BACKGROUND

        return CELL_ROW_BACKGROUND

    def _resolve_url_text_color(
        self,
        *,
        is_selected: bool,
        has_copy_feedback: bool,
    ) -> QColor:
        if has_copy_feedback:
            return URL_COPY_FEEDBACK_TEXT

        if is_selected:
            return SELECTED_ROW_TEXT

        return URL_TEXT

    def _resolve_title_text_color(self, *, index: QModelIndex, is_selected: bool) -> QColor:
        title_state = self._get_text_data(index=index, role=URL_TITLE_STATE_ROLE)

        if title_state == URL_TITLE_STATE_ERROR:
            return URL_ERROR_TEXT

        if is_selected:
            return SELECTED_ROW_SECONDARY_TEXT

        return URL_TITLE_TEXT

    def _get_text_data(self, *, index: QModelIndex, role: int | Qt.ItemDataRole) -> str:
        value = index.data(role)

        if not isinstance(value, str):
            return ""

        return value

    def _build_title_font(self, *, base_font: QFont) -> QFont:
        title_font = QFont(base_font)
        point_size = title_font.pointSize()

        if point_size > 2:
            title_font.setPointSize(point_size - 2)

        title_font.setWeight(QFont.Weight.Normal)

        return title_font
