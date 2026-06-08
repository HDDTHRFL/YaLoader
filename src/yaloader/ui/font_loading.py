from __future__ import annotations

from dataclasses import dataclass

from loguru import logger
from PyQt6.QtGui import QFontDatabase

from yaloader.config.resources import get_title_font_path

FALLBACK_TITLE_FONT_FAMILY = "Death Stars"


@dataclass(frozen=True, slots=True)
class LoadedApplicationFonts:
    title_font_family: str


def load_application_fonts() -> LoadedApplicationFonts:
    title_font_family = load_title_font_family()

    logger.debug("Application title font selected. family={}", title_font_family)

    return LoadedApplicationFonts(title_font_family=title_font_family)


def load_title_font_family() -> str:
    title_font_path = get_title_font_path()

    if not title_font_path.is_file():
        logger.warning("Title font file not found. path={}", title_font_path)
        return FALLBACK_TITLE_FONT_FAMILY

    font_id = QFontDatabase.addApplicationFont(str(title_font_path))

    if font_id < 0:
        logger.warning("Failed to load title font. path={}", title_font_path)
        return FALLBACK_TITLE_FONT_FAMILY

    font_families = QFontDatabase.applicationFontFamilies(font_id)

    if not font_families:
        logger.warning("Loaded title font has no families. path={}", title_font_path)
        return FALLBACK_TITLE_FONT_FAMILY

    selected_family = select_title_font_family(font_families=tuple(font_families))
    logger.debug(
        "Title font loaded. path={} families={} selected={}",
        title_font_path,
        tuple(font_families),
        selected_family,
    )

    return selected_family


def select_title_font_family(*, font_families: tuple[str, ...]) -> str:
    for family in font_families:
        if "death" in family.casefold():
            return family

    return font_families[0]
