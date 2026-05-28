from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from loguru import logger
from pydantic import ValidationError

from yaloader.application.dto.download_history_record import DownloadHistoryRecord

DEFAULT_MAX_HISTORY_RECORDS = 500


@dataclass(frozen=True, slots=True)
class DownloadHistoryService:
    history_file: Path
    max_records: int = DEFAULT_MAX_HISTORY_RECORDS

    def load(self) -> tuple[DownloadHistoryRecord, ...]:
        if not self.history_file.is_file():
            return ()

        try:
            raw_data = json.loads(self.history_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            logger.warning(
                "Failed to load download history. path={} error={}",
                self.history_file,
                error,
            )
            return ()

        if not isinstance(raw_data, list):
            logger.warning("Download history has invalid root type. path={}", self.history_file)
            return ()

        records: list[DownloadHistoryRecord] = []

        for item in raw_data:
            try:
                records.append(DownloadHistoryRecord.model_validate(item))
            except ValidationError as error:
                logger.warning(
                    "Invalid download history record skipped. path={} error={}",
                    self.history_file,
                    error,
                )

        return tuple(records)

    def append(self, *, record: DownloadHistoryRecord) -> None:
        records = (record, *self.load())
        limited_records = records[: self.max_records]
        self._save(records=limited_records)

    def remove_by_task_id(self, *, task_id: UUID) -> int:
        records = self.load()
        filtered_records = tuple(record for record in records if record.task_id != task_id)
        removed_count = len(records) - len(filtered_records)

        if removed_count == 0:
            return 0

        if filtered_records:
            self._save(records=filtered_records)
            return removed_count

        if self.history_file.is_file():
            self.history_file.unlink()

        return removed_count

    def clear(self) -> int:
        records_count = len(self.load())

        if self.history_file.is_file():
            self.history_file.unlink()

        return records_count

    def _save(self, *, records: tuple[DownloadHistoryRecord, ...]) -> None:
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        raw_data = [record.model_dump(mode="json") for record in records]
        self.history_file.write_text(
            json.dumps(raw_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
            newline="\n",
        )
