@echo off
setlocal

cd /d "%~dp0.."

echo [1/7] Ruff autofix
uv run ruff check . --fix
if errorlevel 1 goto failed

echo.
echo [2/7] Ruff format
uv run ruff format .
if errorlevel 1 goto failed

echo.
echo [3/7] Ruff check
uv run ruff check .
if errorlevel 1 goto failed

echo.
echo [4/7] Mypy
uv run mypy src
if errorlevel 1 goto failed

echo.
echo [5/7] Pytest
uv run pytest
if errorlevel 1 goto failed

echo.
echo [6/7] Secret check
call tools\check_secrets.bat
if errorlevel 1 goto failed

echo.
echo [7/7] Bundle
call tools\make_bundle.bat
if errorlevel 1 goto failed

echo.
echo Project verification completed successfully.
exit /b 0

:failed
echo.
echo Project verification failed.
exit /b 1
