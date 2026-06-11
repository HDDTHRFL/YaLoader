@echo off
setlocal EnableExtensions

cd /d "%~dp0\.."

set "PROJECT_ROOT=%CD%"
set "PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe"
set "SECRET_CHECK_SCRIPT=%PROJECT_ROOT%\scripts\check_secrets.py"

if not exist "%PYTHON_EXE%" (
    echo Python executable was not found:
    echo %PYTHON_EXE%
    echo.
    echo Activate or create project virtual environment first.
    endlocal
    exit /b 1
)

if not exist "%SECRET_CHECK_SCRIPT%" (
    echo Secret check script was not found:
    echo %SECRET_CHECK_SCRIPT%
    endlocal
    exit /b 1
)

"%PYTHON_EXE%" "%SECRET_CHECK_SCRIPT%" --root "%PROJECT_ROOT%"
set "EXIT_CODE=%ERRORLEVEL%"

endlocal & exit /b %EXIT_CODE%
