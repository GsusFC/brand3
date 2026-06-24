"""Social link parsing helpers for observatory brand profiles."""

from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse
from typing import Any

from web.observatory_index_support import _unique_links


def _social_links_from_packs(packs: list[dict[str, Any]]) -> list[str]:
    urls = []
    for pack in packs:
        urls.extend(pack.get("official_urls") or [])
        urls.extend(pack.get("analyzed_urls") or [])
        source_map = pack.get("source_map") if isinstance(pack.get("source_map"), dict) else {}
        for source in source_map.values():
            if isinstance(source, dict):
                urls.append(str(source.get("url") or ""))
    return [url for url in urls if _is_social_url(url)]


def _social_links_from_web_payloads(payloads: list[dict[str, Any]]) -> list[str]:
    urls = []
    for payload in payloads:
        html = str(payload.get("html") or "")
        if html:
            parser = _SocialLinkParser()
            try:
                parser.feed(html)
            except Exception:
                pass
            urls.extend(parser.urls)
    return [
        canonical
        for canonical in (_canonical_social_profile_url(url) for url in urls)
        if canonical
    ]


class _SocialLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attr_map = {name: (value or "") for name, value in attrs}
        href = attr_map.get("href", "")
        if href:
            self.urls.append(href)


def _is_social_url(url: str) -> bool:
    host = urlparse(str(url or "")).netloc.lower()
    host = host.removeprefix("www.")
    social_hosts = (
        "linkedin.com",
        "x.com",
        "twitter.com",
        "instagram.com",
        "youtube.com",
        "tiktok.com",
        "github.com",
        "facebook.com",
        "threads.net",
    )
    return any(host == marker or host.endswith(f".{marker}") for marker in social_hosts)


def _canonical_social_profile_url(url: str) -> str | None:
    raw = str(url or "").strip()
    parsed = urlparse(raw)
    host = parsed.netloc.lower().removeprefix("www.")
    if not host or not _is_social_url(raw):
        return None
    segments = [segment for segment in parsed.path.strip("/").split("/") if segment]
    lower = [segment.lower() for segment in segments]

    if "linkedin.com" in host:
        if len(lower) >= 2 and lower[0] in {"company", "school", "showcase"}:
            return raw
        return None

    if host == "x.com" or host.endswith(".x.com") or "twitter.com" in host:
        if lower[:2] == ["intent", "user"] or lower[:2] == ["intent", "follow"]:
            screen_name = (parse_qs(parsed.query).get("screen_name") or [""])[0].strip()
            if screen_name:
                return f"https://x.com/{screen_name.lstrip('@')}"
        if len(lower) == 1 and lower[0] not in {"home", "intent", "i", "share", "search"}:
            return raw
        return None

    if "instagram.com" in host or "threads.net" in host:
        if len(lower) == 1 and lower[0] not in {
            "about",
            "explore",
            "p",
            "reel",
            "stories",
            "tv",
        }:
            return raw
        return None

    if "youtube.com" in host:
        if len(segments) == 1 and segments[0].startswith("@"):
            return raw
        if len(lower) >= 2 and lower[0] in {"channel", "c", "user"}:
            return raw
        return None

    if "tiktok.com" in host:
        if len(segments) == 1 and segments[0].startswith("@"):
            return raw
        return None

    if "github.com" in host:
        if len(lower) == 1 and lower[0] not in {
            "about",
            "collections",
            "events",
            "features",
            "login",
            "marketplace",
            "topics",
        }:
            return raw
        return None

    if "facebook.com" in host:
        if len(lower) == 1 and lower[0] not in {
            "events",
            "groups",
            "login",
            "marketplace",
            "pages",
            "plugins",
            "share",
            "sharer",
            "watch",
        }:
            return raw
        return None

    return None


def _unique_social_links(urls: list[str]) -> list[dict[str, str]]:
    out = []
    seen = set()
    for url in _unique_links(urls):
        canonical = _canonical_social_profile_url(url)
        if not canonical:
            continue
        url = canonical
        parsed = urlparse(url)
        host = parsed.netloc.lower().removeprefix("www.")
        if not host or host in seen:
            continue
        seen.add(host)
        out.append({"label": _social_label(host), "url": url, "host": host})
    return out


def _social_label(host: str) -> str:
    if "linkedin.com" in host:
        return "LinkedIn"
    if host == "x.com" or "twitter.com" in host:
        return "X"
    if "instagram.com" in host:
        return "Instagram"
    if "youtube.com" in host:
        return "YouTube"
    if "tiktok.com" in host:
        return "TikTok"
    if "github.com" in host:
        return "GitHub"
    if "facebook.com" in host:
        return "Facebook"
    if "threads.net" in host:
        return "Threads"
    return host


__all__ = [
    "_canonical_social_profile_url",
    "_is_social_url",
    "_social_label",
    "_unique_social_links",
    "_social_links_from_web_payloads",
    "_social_links_from_packs",
    "_SocialLinkParser",
]
