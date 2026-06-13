@echo off
setlocal EnableExtensions

cd /d "%~dp0.."

if "%~1"=="" (
    echo Usage: tools\bump_version.bat 0.2.0
    exit /b 1
)

echo Updating YaLoader version to %~1
uv run python scripts\bump_version.py "%~1"
if errorlevel 1 goto failed

echo.
echo Updating uv.lock
uv lock
if errorlevel 1 goto failed

echo.
echo Version updated successfully.
echo Next steps:
echo   tools\verify_project.bat
echo   git add .
echo   git commit -m "Bump version to %~1"
exit /b 0

:failed
echo.
echo Version update failed.
exit /b 1
