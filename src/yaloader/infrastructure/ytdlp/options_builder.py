from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.domain.enums import DownloadMode, OutputFormat, VideoQuality

YtDlpOptions = dict[str, object]
YtDlpPostProcessorOptions = dict[str, object]

DEFAULT_RETRIES = 10
DEFAULT_FRAGMENT_RETRIES = 10
DEFAULT_AUDIO_QUALITY = "0"
OUTPUT_TEMPLATE = "%(title).200B [%(id)s].%(ext)s"
REMOTE_COMPONENTS: Final[list[str]] = ["ejs:github"]


@dataclass(frozen=True, slots=True)
class YtDlpOptionsBuilder:
    cookies_file: Path | None = None

    def build(self, request: DownloadRequest) -> YtDlpOptions:
        options: YtDlpOptions = {
            "format": self._build_format_selector(request=request),
            "outtmpl": self._build_output_template(target_dir=request.target_dir),
            "noplaylist": not request.include_playlist,
            "windowsfilenames": True,
            "ignoreerrors": False,
            "overwrites": False,
            "continuedl": True,
            "retries": DEFAULT_RETRIES,
            "fragment_retries": DEFAULT_FRAGMENT_RETRIES,
            "noprogress": True,
            "remote_components": REMOTE_COMPONENTS,
        }

        if request.mode is DownloadMode.VIDEO:
            options["merge_output_format"] = request.output_format.value

        if self.cookies_file is not None and self.cookies_file.is_file():
            options["cookiefile"] = str(self.cookies_file)

        postprocessors = self._build_postprocessors(request=request)

        if postprocessors:
            options["postprocessors"] = postprocessors

        return options

    def _build_output_template(self, target_dir: Path) -> str:
        return str(target_dir / OUTPUT_TEMPLATE)

    def _build_format_selector(self, request: DownloadRequest) -> str:
        if request.mode is DownloadMode.VIDEO:
            return self._build_video_format_selector(
                output_format=request.output_format,
                video_quality=request.video_quality,
            )

        return self._build_audio_format_selector(output_format=request.output_format)

    def _build_video_format_selector(
        self,
        *,
        output_format: OutputFormat,
        video_quality: VideoQuality,
    ) -> str:
        height_filter = self._build_height_filter(video_quality=video_quality)

        if output_format is OutputFormat.MP4:
            return self._join_format_fallbacks(
                [
                    f"bv*[ext=mp4]{height_filter}+ba[ext=m4a]",
                    f"b[ext=mp4]{height_filter}",
                    f"bv*{height_filter}+ba",
                    f"b{height_filter}",
                ]
            )

        if output_format is OutputFormat.WEBM:
            return self._join_format_fallbacks(
                [
                    f"bv*[ext=webm]{height_filter}+ba[ext=webm]",
                    f"b[ext=webm]{height_filter}",
                    f"bv*{height_filter}+ba",
                    f"b{height_filter}",
                ]
            )

        message = f"Unsupported video output format: {output_format}"
        raise ValueError(message)

    def _join_format_fallbacks(self, format_fallbacks: list[str]) -> str:
        return "/".join(format_fallbacks)

    def _build_audio_format_selector(self, output_format: OutputFormat) -> str:
        if output_format is OutputFormat.MP3:
            return "ba/b"

        if output_format is OutputFormat.M4A:
            return "ba[ext=m4a]/ba/b"

        message = f"Unsupported audio output format: {output_format}"
        raise ValueError(message)

    def _build_height_filter(self, video_quality: VideoQuality) -> str:
        height_limit = self._get_height_limit(video_quality=video_quality)

        if height_limit is None:
            return ""

        return f"[height<={height_limit}]"

    def _get_height_limit(self, video_quality: VideoQuality) -> int | None:
        match video_quality:
            case VideoQuality.BEST:
                return None
            case VideoQuality.P2160:
                return 2160
            case VideoQuality.P1440:
                return 1440
            case VideoQuality.P1080:
                return 1080
            case VideoQuality.P720:
                return 720
            case VideoQuality.P480:
                return 480
            case VideoQuality.P360:
                return 360

    def _build_postprocessors(
        self,
        request: DownloadRequest,
    ) -> list[YtDlpPostProcessorOptions]:
        if request.mode is not DownloadMode.AUDIO:
            return []

        preferred_codec = self._get_audio_preferred_codec(output_format=request.output_format)
        postprocessor: YtDlpPostProcessorOptions = {
            "key": "FFmpegExtractAudio",
            "preferredcodec": preferred_codec,
        }

        if request.output_format is OutputFormat.MP3:
            postprocessor["preferredquality"] = DEFAULT_AUDIO_QUALITY

        return [postprocessor]

    def _get_audio_preferred_codec(self, output_format: OutputFormat) -> str:
        if output_format is OutputFormat.MP3:
            return "mp3"

        if output_format is OutputFormat.M4A:
            return "m4a"

        message = f"Unsupported audio output format: {output_format}"
        raise ValueError(message)
