from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from yaloader.application.dto.app_settings import AppSettings


@dataclass(frozen=True, slots=True)
class SettingsService:
    settings_file: Path
    default_downloads_dir: Path

    def load(self) -> AppSettings:
        if not self.settings_file.is_file():
            return self._build_default_settings()

        try:
            raw_data = json.loads(self.settings_file.read_text(encoding="utf-8"))
            return AppSettings.model_validate(raw_data)
        except (OSError, json.JSONDecodeError, ValidationError):
            return self._build_default_settings()

    def save(self, settings: AppSettings) -> None:
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        raw_settings = settings.model_dump(mode="json")
        self.settings_file.write_text(
            json.dumps(raw_settings, ensure_ascii=False, indent=2),
            encoding="utf-8",
            newline="\n",
        )

    def update_downloads_dir(self, downloads_dir: Path) -> AppSettings:
        return self._update_settings({"downloads_dir": downloads_dir})

    def update_download_speed_limit(
        self,
        *,
        bytes_per_second: int | None,
    ) -> AppSettings:
        return self._update_settings({"download_speed_limit_bytes_per_second": bytes_per_second})

    def update_show_history_on_startup(self, *, is_enabled: bool) -> AppSettings:
        return self._update_settings({"show_history_on_startup": is_enabled})

    def update_open_downloads_dir_after_queue_completed(
        self,
        *,
        is_enabled: bool,
    ) -> AppSettings:
        return self._update_settings({"open_downloads_dir_after_queue_completed": is_enabled})

    def update_confirm_clear_queue(self, *, is_enabled: bool) -> AppSettings:
        return self._update_settings({"confirm_clear_queue": is_enabled})

    def _update_settings(self, updates: dict[str, Any]) -> AppSettings:
        current_settings = self.load()
        settings = current_settings.model_copy(update=updates)
        validated_settings = AppSettings.model_validate(settings.model_dump())

        self.save(settings=validated_settings)

        return validated_settings

    def _build_default_settings(self) -> AppSettings:
        return AppSettings(downloads_dir=self.default_downloads_dir)
