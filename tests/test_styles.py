from __future__ import annotations

from yaloader.ui.styles import APP_STYLE_SHEET
from yaloader.ui.widgets.app_header import (
    build_title_font_family_stack,
    build_title_label_style_sheet,
    build_version_label_style_sheet,
    escape_qss_font_family,
)


def test_app_style_sheet_does_not_override_title_font_family() -> None:
    assert "__YALOADER_TITLE_FONT_FAMILY__" not in APP_STYLE_SHEET

    title_label_block_start = APP_STYLE_SHEET.index("QLabel#TitleLabel {")
    title_label_block_end = APP_STYLE_SHEET.index("}", title_label_block_start)
    title_label_block = APP_STYLE_SHEET[title_label_block_start:title_label_block_end]

    assert "font-family" not in title_label_block


def test_build_title_label_style_sheet_uses_loaded_font_family() -> None:
    title_style_sheet = build_title_label_style_sheet(title_font_family="Death Stars")

    assert "font-family:" in title_style_sheet
    assert '"Death Stars"' in title_style_sheet
    assert '"Segoe UI Black"' in title_style_sheet
    assert "color: #FFFFFF;" in title_style_sheet


def test_build_title_font_family_stack_uses_fallbacks() -> None:
    font_family_stack = build_title_font_family_stack(title_font_family="Loaded Font")

    assert font_family_stack.startswith('"Loaded Font"')
    assert '"Death Stars"' in font_family_stack
    assert '"Segoe UI Black"' in font_family_stack
    assert '"Arial Black"' in font_family_stack


def test_escape_qss_font_family_escapes_special_characters() -> None:
    assert escape_qss_font_family(value='My "Font"') == 'My \\"Font\\"'


def test_app_style_sheet_contains_version_label_style() -> None:
    version_label_block_start = APP_STYLE_SHEET.index("QLabel#VersionLabel {")
    version_label_block_end = APP_STYLE_SHEET.index("}", version_label_block_start)
    version_label_block = APP_STYLE_SHEET[version_label_block_start:version_label_block_end]

    assert "font-size: 8pt;" in version_label_block
    assert "color: #6E7681;" in version_label_block


def test_build_version_label_style_sheet_uses_loaded_font_family() -> None:
    version_style_sheet = build_version_label_style_sheet(title_font_family="Death Stars")

    assert "font-family:" in version_style_sheet
    assert '"Death Stars"' in version_style_sheet
    assert '"Segoe UI Black"' in version_style_sheet
    assert "font-size: 8pt;" in version_style_sheet
    assert "color: #6E7681;" in version_style_sheet
