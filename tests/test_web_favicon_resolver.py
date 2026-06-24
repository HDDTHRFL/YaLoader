from __future__ import annotations

from pathlib import Path

from yaloader.infrastructure.web.favicon_resolver import (
    WebFaviconResolver,
    build_favicon_cache_key,
    build_favicon_host_variants,
    build_favicon_url_candidates,
    extract_favicon_host,
    normalize_favicon_host,
)


def test_extract_favicon_host_normalizes_url_host() -> None:
    assert extract_favicon_host(url="https://WWW.Instagram.COM/reel/test/") == "www.instagram.com"


def test_normalize_favicon_host_rejects_empty_host() -> None:
    assert normalize_favicon_host(host=None) is None
    assert normalize_favicon_host(host="") is None


def test_build_favicon_host_variants_adds_root_domain_for_www_host() -> None:
    assert build_favicon_host_variants(host="www.instagram.com") == (
        "www.instagram.com",
        "instagram.com",
    )


def test_build_favicon_url_candidates_contains_direct_and_fallback_sources() -> None:
    candidates = build_favicon_url_candidates(url="https://www.instagram.com/reel/test/")

    assert "https://www.instagram.com/favicon.ico" in candidates
    assert "https://instagram.com/favicon.ico" in candidates
    assert "https://icons.duckduckgo.com/ip3/www.instagram.com.ico" in candidates
    assert "https://www.google.com/s2/favicons?domain=www.instagram.com&sz=64" in candidates


def test_resolver_returns_cached_icon_without_network(tmp_path: Path) -> None:
    host = "www.instagram.com"
    cached_icon_path = tmp_path / f"{build_favicon_cache_key(host=host)}.png"
    cached_icon_path.write_bytes(b"cached")

    resolver = WebFaviconResolver(cache_dir=tmp_path)

    assert (
        resolver.resolve_icon_path(url="https://www.instagram.com/reel/test/") == cached_icon_path
    )
