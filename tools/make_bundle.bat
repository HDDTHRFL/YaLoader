@echo off
setlocal EnableExtensions

cd /d "%~dp0\.."

set "PROJECT_ROOT=%CD%"
set "PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe"
set "BUNDLE_SCRIPT=%PROJECT_ROOT%\scripts\make_bundle.py"

if not exist "%PYTHON_EXE%" (
    echo Python executable was not found:
    echo %PYTHON_EXE%
    echo.
    echo Activate or create project virtual environment first.
    exit /b 1
)

if not exist "%BUNDLE_SCRIPT%" (
    echo Bundle script was not found:
    echo %BUNDLE_SCRIPT%
    exit /b 1
)

"%PYTHON_EXE%" "%BUNDLE_SCRIPT%"

if errorlevel 1 (
    echo.
    echo Failed to create project bundle.
    exit /b 1
)

endlocal