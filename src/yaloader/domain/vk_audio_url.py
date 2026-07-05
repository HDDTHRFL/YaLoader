from __future__ import annotations

import re
from typing import Final
from urllib.parse import urlparse

VK_AUDIO_PUBLIC_CATALOG_OWNER_ID_PREFIX: Final = "-200"
VK_AUDIO_PUBLIC_CATALOG_UNSUPPORTED_STATUS_MESSAGE: Final = (
    "Ссылка VK Audio из публичного каталога сейчас не поддерживается. "
    "Скопируйте обычную ссылку на сам трек из своих аудиозаписей."
)

VK_AUDIO_SUPPORTED_HOSTS: Final[frozenset[str]] = frozenset(
    {
        "vk.com",
        "www.vk.com",
        "m.vk.com",
        "vk.ru",
        "www.vk.ru",
        "m.vk.ru",
    }
)

VK_AUDIO_PATH_RE: Final = re.compile(
    r"^/audio(?P<owner_id>-?\d+)_(?P<audio_id>\d+)(?:_(?P<access_key>[A-Za-z0-9]+))?/?$"
)


def is_unsupported_vk_audio_public_catalog_url(*, url: str) -> bool:
    parsed_url = urlparse(url.strip())
    host = parsed_url.hostname.casefold() if parsed_url.hostname is not None else ""

    if host not in VK_AUDIO_SUPPORTED_HOSTS:
        return False

    match = VK_AUDIO_PATH_RE.fullmatch(parsed_url.path)

    if match is None:
        return False

    return is_unsupported_vk_audio_public_catalog_owner_id(owner_id=match.group("owner_id"))


def is_unsupported_vk_audio_public_catalog_owner_id(*, owner_id: str) -> bool:
    return owner_id.startswith(VK_AUDIO_PUBLIC_CATALOG_OWNER_ID_PREFIX)
