from __future__ import annotations

from typing import Final

MODE_COLUMN_INDEX: Final = 0
URL_COLUMN_INDEX: Final = 1
QUALITY_COLUMN_INDEX: Final = 2
FORMAT_COLUMN_INDEX: Final = 3
STATUS_COLUMN_INDEX: Final = 4
PROGRESS_COLUMN_INDEX: Final = 5
FOLDER_COLUMN_INDEX: Final = 6

QUEUE_COLUMN_COUNT: Final = 7
QUEUE_ROW_HEIGHT: Final = 48
TABLE_RIGHT_OVERDRAW_WIDTH: Final = 2

MIN_COLUMN_WIDTHS: Final[dict[int, int]] = {
    MODE_COLUMN_INDEX: 64,
    URL_COLUMN_INDEX: 260,
    QUALITY_COLUMN_INDEX: 84,
    FORMAT_COLUMN_INDEX: 68,
    STATUS_COLUMN_INDEX: 92,
    PROGRESS_COLUMN_INDEX: 120,
    FOLDER_COLUMN_INDEX: 190,
}

COLUMN_STRETCH_WEIGHTS: Final[dict[int, float]] = {
    MODE_COLUMN_INDEX: 0.2,
    URL_COLUMN_INDEX: 6.0,
    QUALITY_COLUMN_INDEX: 0.25,
    FORMAT_COLUMN_INDEX: 0.25,
    STATUS_COLUMN_INDEX: 0.35,
    PROGRESS_COLUMN_INDEX: 1.1,
    FOLDER_COLUMN_INDEX: 2.8,
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
        width
        for column_index, width in calculated_widths.items()
        if column_index != FOLDER_COLUMN_INDEX
    )
    calculated_widths[FOLDER_COLUMN_INDEX] = max(1, last_column_width)

    return calculated_widths
