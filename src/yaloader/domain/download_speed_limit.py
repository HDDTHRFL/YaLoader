from __future__ import annotations

from dataclasses import dataclass
from typing import Final

BYTES_PER_KIB: Final = 1024
BYTES_PER_MIB: Final = BYTES_PER_KIB * BYTES_PER_KIB

MIN_CUSTOM_DOWNLOAD_SPEED_LIMIT_MB: Final = 0
MAX_CUSTOM_DOWNLOAD_SPEED_LIMIT_MB: Final = 100

DOWNLOAD_SPEED_LIMIT_PRESETS_BYTES: Final[tuple[int | None, ...]] = (
    None,
    512 * BYTES_PER_KIB,
    1 * BYTES_PER_MIB,
    2 * BYTES_PER_MIB,
    5 * BYTES_PER_MIB,
    10 * BYTES_PER_MIB,
    20 * BYTES_PER_MIB,
)


@dataclass(frozen=True, slots=True)
class DownloadSpeedLimit:
    bytes_per_second: int | None = None

    def __post_init__(self) -> None:
        validate_download_speed_limit_bytes_per_second(
            bytes_per_second=self.bytes_per_second,
        )


def validate_download_speed_limit_bytes_per_second(
    *,
    bytes_per_second: int | None,
) -> int | None:
    if bytes_per_second is None:
        return None

    if isinstance(bytes_per_second, bool):
        message = "Download speed limit must be an integer number of bytes per second."
        raise ValueError(message)

    if bytes_per_second <= 0:
        message = "Download speed limit must be greater than zero."
        raise ValueError(message)

    return bytes_per_second


def validate_custom_download_speed_limit_mb(*, megabytes_per_second: int) -> int:
    if isinstance(megabytes_per_second, bool):
        message = "Download speed limit must be an integer number of megabytes per second."
        raise ValueError(message)

    if not (
        MIN_CUSTOM_DOWNLOAD_SPEED_LIMIT_MB
        <= megabytes_per_second
        <= MAX_CUSTOM_DOWNLOAD_SPEED_LIMIT_MB
    ):
        message = (
            "Download speed limit must be between "
            f"{MIN_CUSTOM_DOWNLOAD_SPEED_LIMIT_MB} and "
            f"{MAX_CUSTOM_DOWNLOAD_SPEED_LIMIT_MB} MBytes/s."
        )
        raise ValueError(message)

    return megabytes_per_second


def build_download_speed_limit_from_megabytes(*, megabytes_per_second: int) -> int | None:
    validated_value = validate_custom_download_speed_limit_mb(
        megabytes_per_second=megabytes_per_second,
    )

    if validated_value == 0:
        return None

    return validated_value * BYTES_PER_MIB


def convert_download_speed_limit_to_megabytes(*, bytes_per_second: int | None) -> int:
    if bytes_per_second is None:
        return 0

    validated_value = validate_download_speed_limit_bytes_per_second(
        bytes_per_second=bytes_per_second,
    )

    if validated_value is None:
        return 0

    rounded_value = round(validated_value / BYTES_PER_MIB)

    return max(
        MIN_CUSTOM_DOWNLOAD_SPEED_LIMIT_MB,
        min(MAX_CUSTOM_DOWNLOAD_SPEED_LIMIT_MB, rounded_value),
    )


def is_known_download_speed_limit_preset(*, bytes_per_second: int | None) -> bool:
    return bytes_per_second in DOWNLOAD_SPEED_LIMIT_PRESETS_BYTES


def format_download_speed_limit_label(*, bytes_per_second: int | None) -> str:
    if bytes_per_second is None:
        return "Без ограничения"

    return format_bytes_per_second(bytes_per_second=bytes_per_second)


def format_bytes_per_second(*, bytes_per_second: int) -> str:
    if bytes_per_second >= BYTES_PER_MIB:
        value = bytes_per_second / BYTES_PER_MIB
        return f"{format_decimal_number(value=value)} MBytes/s"

    value = bytes_per_second / BYTES_PER_KIB
    return f"{format_decimal_number(value=value)} KBytes/s"


def format_decimal_number(*, value: float) -> str:
    if value.is_integer():
        return str(int(value))

    return f"{value:.1f}"
