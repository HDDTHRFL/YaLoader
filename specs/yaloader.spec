# -*- mode: python ; coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

SPEC_DIR = Path(SPECPATH).resolve()
PROJECT_ROOT = SPEC_DIR.parent
SRC_DIR = PROJECT_ROOT / "src"
PACKAGE_DIR = SRC_DIR / "yaloader"
ASSETS_DIR = PACKAGE_DIR / "ui" / "assets"
APP_ICON_PATH = ASSETS_DIR / "app_icon.ico"

yt_dlp_datas, yt_dlp_binaries, yt_dlp_hiddenimports = collect_all("yt_dlp")

datas = [
    (str(ASSETS_DIR), "yaloader/ui/assets"),
    *yt_dlp_datas,
]

binaries = [
    *yt_dlp_binaries,
]

hiddenimports = [
    "pythoncom",
    "pywintypes",
    "win32com",
    "win32com.client",
    "win32con",
    "win32gui",
    *yt_dlp_hiddenimports,
]

a = Analysis(
    [str(PACKAGE_DIR / "main.py")],
    pathex=[str(SRC_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="YaLoader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(APP_ICON_PATH),
)
