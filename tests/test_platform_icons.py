from __future__ import annotations

from yaloader.domain.source_platform import SourcePlatform
from yaloader.ui.platform_icons import get_source_platform_icon_path


def test_vk_audio_uses_vk_platform_icon() -> None:
    icon_path = get_source_platform_icon_path(platform=SourcePlatform.VK_AUDIO)

    assert icon_path is not None
    assert icon_path.name == "vkvideo.png"
