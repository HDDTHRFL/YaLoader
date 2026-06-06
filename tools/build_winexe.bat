@echo off
setlocal EnableExtensions

chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

cd /d "%~dp0.."

echo ===============================
echo Проверка uv
echo.

where uv >nul 2>nul
if errorlevel 1 (
    echo [Ошибка] uv не найден в PATH.
    echo Установи uv и повтори сборку.
    pause
    exit /b 1
)

echo [OK] uv найден.

echo.
echo ===============================
echo Синхронизация окружения
echo.

call uv sync --dev
if errorlevel 1 (
    echo.
    echo [Ошибка] uv sync --dev завершился с ошибкой.
    pause
    exit /b 1
)

echo.
echo ===============================
echo Проверки качества
echo.

call uv run ruff format .
if errorlevel 1 (
    echo.
    echo [Ошибка] ruff format завершился с ошибкой.
    pause
    exit /b 1
)

call uv run ruff check .
if errorlevel 1 (
    echo.
    echo [Ошибка] ruff check завершился с ошибкой.
    pause
    exit /b 1
)

call uv run mypy src
if errorlevel 1 (
    echo.
    echo [Ошибка] mypy завершился с ошибкой.
    pause
    exit /b 1
)

call uv run pytest
if errorlevel 1 (
    echo.
    echo [Ошибка] pytest завершился с ошибкой.
    pause
    exit /b 1
)

echo.
echo ===============================
echo Создание бандла проекта
echo.

call tools\make_bundle.bat
if errorlevel 1 (
    echo.
    echo [Ошибка] make_bundle.bat завершился с ошибкой.
    pause
    exit /b 1
)

echo.
echo ===============================
echo Очистка build / dist
echo.

if exist build (
    rmdir /s /q build
    if exist build (
        echo [Ошибка] Не удалось удалить build.
        pause
        exit /b 1
    ) else (
        echo [OK] build очищена.
    )
) else (
    echo [OK] build отсутствует.
)

if exist dist (
    rmdir /s /q dist
    if exist dist (
        echo [Ошибка] Не удалось удалить dist.
        pause
        exit /b 1
    ) else (
        echo [OK] dist очищена.
    )
) else (
    echo [OK] dist отсутствует.
)

echo.
echo ===============================
echo Очистка __pycache__ / *.pyc
echo.

for /d /r . %%d in (__pycache__) do (
    if exist "%%d" (
        rmdir /s /q "%%d"
        if exist "%%d" (
            echo [Ошибка] Не удалось удалить %%d
            pause
            exit /b 1
        )
    )
)

for /r . %%f in (*.pyc) do (
    if exist "%%f" (
        del /f /q "%%f"
        if exist "%%f" (
            echo [Ошибка] Не удалось удалить %%f
            pause
            exit /b 1
        )
    )
)

echo [OK] __pycache__ и *.pyc очищены.

echo.
echo ===============================
echo Сборка YaLoader.exe onefile
echo.

call uv run pyinstaller --noconfirm --clean specs\yaloader.spec
if errorlevel 1 (
    echo.
    echo [Ошибка] Сборка YaLoader.exe завершилась с ошибкой.
    pause
    exit /b 1
)

if not exist "dist\YaLoader.exe" (
    echo.
    echo [Ошибка] dist\YaLoader.exe не найден после сборки.
    pause
    exit /b 1
)

echo.
echo [OK] Onefile-сборка завершена: dist\YaLoader.exe
explorer dist
pause