# YaLoader development guide

This document is intended for developers and describes the technical development rules for YaLoader.

The user guide is located in `README.md`.

## Development goals

YaLoader should be maintained as a full desktop application, not as a thin wrapper around yt-dlp.

Main goals:

- clean architecture;
- strict typing;
- responsive PyQt6 interface;
- no long-running operations in the main UI thread;
- isolation of yt-dlp and external tools in the infrastructure layer;
- simple feature extension;
- Windows-first implementation with preparation for future multi-platform architecture.

## Stack

- Python 3.13+
- PyQt6
- yt-dlp
- FFmpeg
- Deno
- pydantic
- httpx
- loguru
- pytest
- ruff
- mypy
- uv
- PyInstaller

## Development requirements

Local development requires:

- Windows 10 or Windows 11;
- Python 3.13 or newer;
- uv;
- Git.

For normal application use, FFmpeg and Deno can be prepared by the application itself in portable form. For development, it is still important to test scenarios where tools are missing, already installed, or require reinstallation.

## Quick start

```powershell
git clone <repository-url>
cd yaloader
uv sync
uv run yaloader
```

## Project structure

```text
src/yaloader/
├── ui/
├── application/
├── domain/
├── infrastructure/
├── services/
├── models/
└── config/
```

## Layer responsibilities

### domain

The `domain` layer contains business rules, entities, value objects, enum typing, and pure domain validation.

Allowed:

- dataclass;
- enum;
- pure functions;
- domain rules;
- value objects.

Not allowed:

- PyQt6;
- yt-dlp;
- httpx;
- subprocess;
- Windows API;
- filesystem workflows that belong to infrastructure;
- UI logic.

### application

The `application` layer contains DTOs, ports, and application services.

Allowed:

- pydantic DTOs;
- Protocol interfaces;
- queue services;
- history services;
- orchestration use cases;
- interfaces for infrastructure.

Not allowed:

- direct calls to Qt widgets;
- direct calls to the yt-dlp runtime;
- direct calls to Windows shell integration.

### infrastructure

The `infrastructure` layer contains implementations of external integrations.

Examples:

- yt-dlp downloader;
- yt-dlp metadata extractor;
- browser cookies exporter;
- FFmpeg portable installer;
- Deno portable installer;
- HTTP file downloader;
- Windows Explorer integration.

Infrastructure may depend on `application` and `domain`, but `domain` and `application` must not depend on infrastructure details.

### ui

The `ui` layer contains PyQt6 widgets, windows, controllers, styles, and user scenarios.

Rules:

- widgets must not call yt-dlp directly;
- widgets must not perform heavy operations;
- long-running operations must run through controllers and background workers;
- business logic must not live inside widgets;
- the UI must remain responsive.

### services

The `services` layer is responsible for the composition root.

`services/app_container.py` assembles application dependencies:

- paths;
- settings;
- services;
- infrastructure adapters;
- shared state;
- download queue;
- history;
- metadata services.

## Dependency direction

Preferred dependency direction:

```text
ui -> application -> domain
ui -> services
services -> application
services -> infrastructure
infrastructure -> application
infrastructure -> domain
```

Reverse dependencies should be avoided.

## DTOs

DTOs should be used for data that crosses layer boundaries.

Rules:

- use pydantic;
- make DTOs immutable where possible;
- explicitly validate input data;
- do not pass Qt widgets between layers;
- do not pass raw yt-dlp objects outside infrastructure unless necessary;
- avoid unstructured dictionaries outside infrastructure.

## Typing

The project should remain compatible with mypy strict.

Rules:

- avoid `Any`;
- use `object` when the type is truly unknown;
- use `Protocol` for ports;
- use `Final` for constants where it improves readability;
- avoid implicit optional scenarios;
- write small functions with clear types.

## UI and background operations

The main PyQt6 thread must not be blocked.

The following must run in the background:

- downloading;
- download preparation;
- metadata reading;
- cookies export;
- FFmpeg installation;
- Deno installation;
- tool update checks;
- heavy filesystem operations.

The UI should receive results through controller polling or a Qt-safe signal/slot mechanism.

## Logging

The project uses loguru.

Using `print()` in application code is not allowed.

Logs should help diagnose:

- application startup;
- environment status;
- tool preparation;
- downloads;
- yt-dlp errors;
- cookies import;
- Windows Explorer integration issues.

Secrets, cookies, tokens, and private keys must not be logged.

## Secrets

Before publishing or sending code, run:

```powershell
.\tools\check_secrets.bat
```

Do not commit:

- `.env`;
- `cookies.txt`;
- private keys;
- access tokens;
- browser cookie exports;
- local logs;
- generated bundles.

## Checks before commit

Preferred full local verification command:

```powershell
.\tools\verify_project.bat
```

The command above is the preferred local gate before commit. The individual commands below describe the checks that should remain aligned with CI.

```powershell
uv run ruff check . --fix
uv run ruff format .
uv run ruff check .
uv run mypy src
uv run pytest
.\tools\check_secrets.bat
```

## GitHub Actions CI

The repository contains a GitHub Actions workflow:

```text
.github/workflows/ci.yml
```

The workflow runs on `push`, `pull_request`, and manual `workflow_dispatch`.

It checks:

- formatting with `ruff format --check`;
- linting with `ruff check`;
- typing with `mypy`;
- tests with `pytest`;
- local secret scanning with `tools/check_secrets.bat`.

CI should stay aligned with the local pre-commit check commands.

## Running the application

```powershell
uv run yaloader
```

## Building the Windows executable

```powershell
.\tools\build_winexe.bat
```

The PyInstaller spec is located here:

```text
specs/yaloader.spec
```

## Creating a release package

```powershell
.\tools\package_release.bat
.\tools\check_release_ready.bat <version>
```

The release archive is created in `dist/release/` and must keep the official asset name:

```text
YaLoader-v<version>-windows-x64.zip
```

The release archive contains only end-user files:

- `YaLoader.exe`;
- `README.md`;
- `README_RU.md`;
- `LICENSE`;
- `SHA256SUMS.txt`.

`docs/DEVELOPMENT.md` is repository-only developer documentation and must not be copied into release archives.

The release packaging step also creates:

- `YaLoader-v<version>-windows-x64.zip.sha256`;
- `GITHUB_RELEASE_DESCRIPTION-v<version>.md`.

Copy the generated GitHub release description into the GitHub Release body and upload the archive from `dist/release/` as the main release asset.

## Creating a bundle for review

```powershell
.\tools\make_bundle.bat
```

The bundle is created in `_bundle/`. This directory must not be committed.

## Adding a new feature

Recommended order:

1. Add or update domain rules if there is business logic.
2. Add or update DTOs in `application/dto`.
3. Add a port in `application/ports` if an infrastructure dependency is needed.
4. Implement the infrastructure adapter.
5. Wire dependencies in `services/app_container.py`.
6. Add controller/UI integration.
7. Add tests.
8. Run all checks.

## Adding a new setting

Recommended order:

1. Add a field to `AppSettings`.
2. Add an update method to `SettingsService`.
3. Connect the setting to the required service or controller.
4. Add the UI control after application behavior exists.
5. Add tests for saving and applying the setting.

## Adding a new backend or external integration

Do not connect a backend directly to widgets.

Recommended order:

1. Add or extend an application port.
2. Implement an adapter in `infrastructure`.
3. Add DTOs if needed.
4. Wire the implementation through `AppContainer`.
5. Keep the UI independent from backend-specific details.

## Naming style

Names should be clear and production-style.

Avoid unclear abbreviations:

- `tmp`;
- `obj`;
- `val`;
- `data` when a more specific name can be used.

Short names are acceptable only in a very small local context where the meaning is obvious.

## Git commit style

A commit should describe one logical step.

Examples:

```text
Add local secret scanning before publishing
Refine local secret scanning rules
Add source-available non-commercial license
Expose portable tools to yt-dlp runtime
Improve public project documentation
```

Do not add extra commands to the same block after the `git commit ...` command.
