@echo off
setlocal

cd /d "%~dp0.."

echo Checking Git history for secrets and generated files
uv run python scripts\check_git_history.py
if errorlevel 1 goto failed

echo.
echo Git history check completed successfully.
exit /b 0

:failed
echo.
echo Git history check failed.
exit /b 1
