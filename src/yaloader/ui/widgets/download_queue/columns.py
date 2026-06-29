from __future__ import annotations

from typing import Final

MODE_COLUMN_INDEX: Final = 0
URL_COLUMN_INDEX: Final = 1
QUALITY_COLUMN_INDEX: Final = 2
STATUS_PROGRESS_COLUMN_INDEX: Final = 3
FOLDER_COLUMN_INDEX: Final = 4

STATUS_COLUMN_INDEX: Final = STATUS_PROGRESS_COLUMN_INDEX
PROGRESS_COLUMN_INDEX: Final = STATUS_PROGRESS_COLUMN_INDEX

QUEUE_COLUMN_COUNT: Final = 5
QUEUE_ROW_HEIGHT: Final = 54
TABLE_RIGHT_OVERDRAW_WIDTH: Final = 1

MIN_COLUMN_WIDTHS: Final[dict[int, int]] = {
    MODE_COLUMN_INDEX: 106,
    URL_COLUMN_INDEX: 340,
    QUALITY_COLUMN_INDEX: 136,
    STATUS_PROGRESS_COLUMN_INDEX: 170,
    FOLDER_COLUMN_INDEX: 210,
}

COLUMN_STRETCH_WEIGHTS: Final[dict[int, float]] = {
    MODE_COLUMN_INDEX: 0.42,
    URL_COLUMN_INDEX: 7.0,
    QUALITY_COLUMN_INDEX: 0.62,
    STATUS_PROGRESS_COLUMN_INDEX: 1.35,
    FOLDER_COLUMN_INDEX: 2.9,
}


def calculate_queue_column_widths(*, available_width: int) -> dict[int, int]:
    if available_width <= 0:
        return {}

    minimum_total_width = sum(MIN_COLUMN_WIDTHS.values())
    total_weight = sum(COLUMN_STRETCH_WEIGHTS.values())
    calculated_widths: dict[int, int] = {}

    if available_width <= minimum_total_width:
        scale = available_width / minimum_total_width

        for column_index, minimum_width in MIN_COLUMN_WIDTHS.items():
            calculated_widths[column_index] = max(1, int(minimum_width * scale))

        return calculated_widths

    extra_width = available_width - minimum_total_width

    for column_index, minimum_width in MIN_COLUMN_WIDTHS.items():
        weighted_extra = int(extra_width * COLUMN_STRETCH_WEIGHTS[column_index] / total_weight)
        calculated_widths[column_index] = minimum_width + weighted_extra

    last_column_width = available_width - sum(
        width for column_index, width in calculated_widths.items() if column_index != FOLDER_COLUMN_INDEX
    )
    calculated_widths[FOLDER_COLUMN_INDEX] = max(1, last_column_width)

    return calculated_widths
