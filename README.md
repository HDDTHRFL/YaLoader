# YaLoader

YaLoader is a modern Windows desktop application for downloading video and audio using yt-dlp and FFmpeg.

## Stack

- Python 3.13+
- PyQt6
- yt-dlp
- FFmpeg
- qasync
- pydantic
- loguru
- pytest
- ruff
- mypy
- uv

## Development

Install dependencies:

```powershell
uv sync
```

Run application:

```powershell
uv run yaloader
```

Run checks:

```powershell
uv run ruff check .
uv run ruff format .
uv run mypy src
uv run pytest
```