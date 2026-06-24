from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from yaloader.application.dto.download_request import DownloadRequest
from yaloader.application.ports.process_runner import ProcessRunner
from yaloader.domain.enums import DownloadMode, OutputFormat, VideoQuality

YtDlpOptions = dict[str, object]
YtDlpPostProcessorOptions = dict[str, object]

DEFAULT_RETRIES = 10
DEFAULT_FRAGMENT_RETRIES = 10
DEFAULT_AUDIO_QUALITY = "0"
OUTPUT_TEMPLATE = "%(title).200B.%(ext)s"
REMOTE_COMPONENTS: Final[list[str]] = ["ejs:github"]
FFMPEG_EXECUTABLE_NAME: Final = "ffmpeg"

VIDEO_FORMAT_UNAVAILABLE_FALLBACK_SELECTOR: Final = "bv*+ba/b"
VIDEO_FORMAT_UNAVAILABLE_FALLBACKS: Final[tuple[str, ...]] = (
    "bv*+ba",
    "b",
)


@dataclass(frozen=True, slots=True)
class YtDlpOptionsBuilder:
    cookies_file: Path | None = None
    process_runner: ProcessRunner | None = None

    def build(self, request: DownloadRequest) -> YtDlpOptions:
        return self._build_options(
            request=request,
            format_selector=self._build_format_selector(request=request),
            should_merge_video=request.mode is DownloadMode.VIDEO,
            postprocessors=self._build_postprocessors(request=request),
        )

    def build_video_only(self, request: DownloadRequest) -> YtDlpOptions:
        if request.mode is not DownloadMode.VIDEO:
            message = "Video-only options can be built only for video requests."
            raise ValueError(message)

        return self._build_options(
            request=request,
            format_selector=self._build_video_only_format_selector(
                output_format=request.output_format,
                video_quality=request.video_quality,
            ),
            should_merge_video=False,
            postprocessors=(),
        )

    def build_audio_companion(
        self,
        *,
        request: DownloadRequest,
        audio_format: OutputFormat,
    ) -> YtDlpOptions:
        audio_request = DownloadRequest(
            url=request.url,
            target_dir=request.target_dir,
            mode=DownloadMode.AUDIO,
            output_format=audio_format,
            video_quality=request.video_quality,
            include_playlist=request.include_playlist,
            download_speed_limit_bytes_per_second=(request.download_speed_limit_bytes_per_second),
        )

        return self.build(request=audio_request)

    def _build_options(
        self,
        *,
        request: DownloadRequest,
        format_selector: str,
        should_merge_video: bool,
        postprocessors: tuple[YtDlpPostProcessorOptions, ...],
    ) -> YtDlpOptions:
        options: YtDlpOptions = {
            "format": format_selector,
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

        if should_merge_video:
            options["merge_output_format"] = request.output_format.value

        if self.cookies_file is not None and self.cookies_file.is_file():
            options["cookiefile"] = str(self.cookies_file)

        ffmpeg_location = self._find_ffmpeg_location()

        if ffmpeg_location is not None:
            options["ffmpeg_location"] = str(ffmpeg_location)

        if postprocessors:
            options["postprocessors"] = list(postprocessors)

        return options

    def _build_output_template(self, target_dir: Path) -> str:
        return str(target_dir / OUTPUT_TEMPLATE)

    def _find_ffmpeg_location(self) -> Path | None:
        if self.process_runner is None:
            return None

        return self.process_runner.find_executable(FFMPEG_EXECUTABLE_NAME)

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
                    f"bv*{height_filter}+ba",
                    f"b[ext=mp4]{height_filter}",
                    f"b{height_filter}",
                    *VIDEO_FORMAT_UNAVAILABLE_FALLBACKS,
                ]
            )

        if output_format is OutputFormat.WEBM:
            return self._join_format_fallbacks(
                [
                    f"bv*[ext=webm]{height_filter}+ba[ext=webm]",
                    f"bv*{height_filter}+ba",
                    f"b[ext=webm]{height_filter}",
                    f"b{height_filter}",
                    *VIDEO_FORMAT_UNAVAILABLE_FALLBACKS,
                ]
            )

        message = f"Unsupported video output format: {output_format}"
        raise ValueError(message)

    def _build_video_only_format_selector(
        self,
        *,
        output_format: OutputFormat,
        video_quality: VideoQuality,
    ) -> str:
        height_filter = self._build_height_filter(video_quality=video_quality)
        exact_height_filter = self._build_exact_height_filter(video_quality=video_quality)

        if output_format is OutputFormat.MP4:
            if video_quality is VideoQuality.BEST:
                return self._join_format_fallbacks(
                    [
                        "bv*[ext=mp4]",
                        "bv*",
                        "b[ext=mp4]",
                        "b",
                    ]
                )

            return self._join_format_fallbacks(
                [
                    f"bv*[ext=mp4][vcodec^=avc1]{exact_height_filter}",
                    f"bv*[ext=mp4]{exact_height_filter}",
                    f"bv*[ext=mp4][vcodec^=avc1]{height_filter}",
                    f"bv*[ext=mp4]{height_filter}",
                    f"bv*[vcodec^=avc1]{height_filter}",
                    f"bv*{height_filter}",
                    "bv*",
                    f"b[ext=mp4]{height_filter}",
                    f"b{height_filter}",
                    "b",
                ]
            )

        if output_format is OutputFormat.WEBM:
            return self._join_format_fallbacks(
                [
                    f"bv*[ext=webm]{height_filter}",
                    f"bv*{height_filter}",
                    "bv*",
                    f"b[ext=webm]{height_filter}",
                    f"b{height_filter}",
                    "b",
                ]
            )

        message = f"Unsupported video-only output format: {output_format}"
        raise ValueError(message)

    def _join_format_fallbacks(self, format_fallbacks: list[str]) -> str:
        unique_format_fallbacks: list[str] = []

        for format_fallback in format_fallbacks:
            if not format_fallback:
                continue

            if format_fallback in unique_format_fallbacks:
                continue

            unique_format_fallbacks.append(format_fallback)

        return "/".join(unique_format_fallbacks)

    def _build_height_filter(self, *, video_quality: VideoQuality) -> str:
        if video_quality is VideoQuality.BEST:
            return ""

        return f"[height<={video_quality.value.removesuffix('p')}]"

    def _build_exact_height_filter(self, *, video_quality: VideoQuality) -> str:
        if video_quality is VideoQuality.BEST:
            return ""

        return f"[height={video_quality.value.removesuffix('p')}]"

    def _build_audio_format_selector(self, *, output_format: OutputFormat) -> str:
        if output_format is OutputFormat.MP3:
            return "ba/b"

        if output_format is OutputFormat.M4A:
            return "ba[ext=m4a]/ba/b"

        message = f"Unsupported audio output format: {output_format}"
        raise ValueError(message)

    def _build_postprocessors(
        self,
        *,
        request: DownloadRequest,
    ) -> tuple[YtDlpPostProcessorOptions, ...]:
        if request.mode is DownloadMode.VIDEO:
            return ()

        if request.output_format is OutputFormat.MP3:
            return (
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": DEFAULT_AUDIO_QUALITY,
                },
            )

        if request.output_format is OutputFormat.M4A:
            return (
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "m4a",
                },
            )

        return ()
