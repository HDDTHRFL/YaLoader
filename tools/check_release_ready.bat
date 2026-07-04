@echo off
setlocal EnableExtensions

cd /d "%~dp0\.."

echo Checking YaLoader release readiness
uv run python scripts\check_release_ready.py %*
if errorlevel 1 goto failed

echo.
echo Release readiness check completed successfully.
exit /b 0

:failed
echo.
echo Release readiness check failed.
exit /b 1