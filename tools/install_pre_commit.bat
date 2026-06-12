@echo off
setlocal

cd /d "%~dp0.."

echo Installing pre-commit hooks
uv run pre-commit install
if errorlevel 1 goto failed

echo.
echo Running pre-commit on all files
uv run pre-commit run --all-files
if errorlevel 1 goto failed

echo.
echo Pre-commit hooks installed successfully.
exit /b 0

:failed
echo.
echo Pre-commit setup failed.
exit /b 1
