@echo off
setlocal EnableExtensions

cd /d "%~dp0\.."

echo Packaging YaLoader release
uv run python scripts\package_release.py %*
if errorlevel 1 goto failed

echo.
echo Release packaging completed successfully.
exit /b 0

:failed
echo.
echo Release packaging failed.
exit /b 1