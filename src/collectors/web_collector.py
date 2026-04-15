"""
Web collector using Firecrawl.

Scrapes the brand's website and extracts:
- HTML structure, meta tags, content
- Visual assets (logo, colors — via screenshots)
- Tech stack detection
- Page speed signals
"""

import re
import json
from dataclasses import dataclass
from html import unescape
from urllib.parse import urlparse
from urllib.error import URLError
from urllib.request import Request, urlopen

from firecrawl import Firecrawl


@dataclass
class WebData:
    """Raw web data from scraping."""
    url: str
    title: str = ""
    meta_description: str = ""
    markdown_content: str = ""
    html: str = ""
    canonical_url: str = ""
    alternate_domains: list[str] = None
    links: list = None
    images: list = None
    screenshot_path: str = ""
    tech_stack: list[str] = None
    load_time_ms: int = 0
    error: str = ""

    def __post_init__(self):
        self.links = self.links or []
        self.alternate_domains = self.alternate_domains or []
        self.images = self.images or []
        self.tech_stack = self.tech_stack or []


class WebCollector:
    """Collects web data via Firecrawl CLI."""

    COOKIE_PATTERNS = [
        r"we value your privacy",
        r"cookie",
        r"consent preferences",
        r"accept all",
        r"reject all",
        r"customise",
        r"customize",
        r"necessary always active",
        r"manage preferences",
        r"no cookies to display",
        r"revisit consent",
        r"show more",
        r"necessaryalways active",
        r"strictly necessary",
        r"functional",
        r"analytics",
        r"performance",
        r"advertisement",
    ]

    FIRECRAWL_PROMPT_PATTERNS = [
        r"turn websites into llm-ready data",
        r"authenticate with your firecrawl account",
        r"login with browser",
        r"enter api key manually",
        r"you are not logged in",
    ]

    def __init__(self, api_key: str = None):
        self.api_key = api_key

    def _run_firecrawl(self, url: str) -> dict:
        """Scrape URL via Firecrawl Python SDK. Returns legacy {content, raw, error} shape."""
        if not self.api_key:
            return {"error": "FIRECRAWL_API_KEY not set"}
        try:
            doc = Firecrawl(api_key=self.api_key).scrape(
                url, formats=["markdown"], timeout=60000
            )
        except Exception as exc:
            return {"error": str(exc)}
        content = (doc.markdown or "").strip()
        return {"content": content, "raw": content}

    def _clean_markdown_content(self, content: str) -> str:
        """Remove obvious cookie/consent UI sludge from scraped markdown."""
        if not content:
            return ""

        lowered_content = content.lower()
        if any(re.search(pattern, lowered_content) for pattern in self.FIRECRAWL_PROMPT_PATTERNS):
            return ""

        cleaned_lines = []
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped:
                cleaned_lines.append("")
                continue

            lowered = stripped.lower()
            if any(re.search(pattern, lowered) for pattern in self.COOKIE_PATTERNS):
                continue
            if stripped.startswith("![") and "consent" in lowered:
                continue
            if len(stripped) <= 24 and lowered in {
                "accept all",
                "reject all",
                "customise",
                "customize",
                "close",
                "show more",
            }:
                continue

            cleaned_lines.append(stripped)

        # Collapse excessive blank lines introduced by filtering.
        collapsed = []
        previous_blank = False
        for line in cleaned_lines:
            is_blank = not line
            if is_blank and previous_blank:
                continue
            collapsed.append(line)
            previous_blank = is_blank

        trimmed = self._trim_preamble(collapsed)

        return "\n".join(trimmed).strip()

    def _trim_preamble(self, lines: list[str]) -> list[str]:
        """Drop leading UI/navigation sludge before the first meaningful content block."""
        meaningful_index = None

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            if self._is_meaningful_content_line(stripped) and not self._is_link_only_line(stripped):
                meaningful_index = idx
                break

        if meaningful_index is None:
            for idx, line in enumerate(lines):
                stripped = line.strip()
                if stripped and self._is_meaningful_content_line(stripped):
                    meaningful_index = idx
                    break

        if meaningful_index is None or meaningful_index <= 0:
            return lines
        return lines[meaningful_index:]

    def _is_meaningful_content_line(self, line: str) -> bool:
        if line.startswith("# "):
            return True
        if len(line) >= 28:
            return True
        if any(mark in line for mark in [".", ",", ":", "?", "!"]):
            return True
        if line.startswith("[") and "](" in line and len(line) >= 36:
            return True
        return False

    def _is_link_only_line(self, line: str) -> bool:
        return line.startswith("[") and "](" in line

    def _extract_title(self, content: str) -> str:
        """Extract a meaningful title from cleaned markdown."""
        for line in content.split("\n"):
            if line.startswith("# "):
                return line[2:].strip()

        for line in content.split("\n"):
            stripped = line.strip()
            if stripped and not stripped.startswith("![") and len(stripped) <= 120:
                return stripped
        return ""

    def _trim_to_title(self, content: str, title: str) -> str:
        """Drop any leading content that appears before the extracted title."""
        if not content or not title:
            return content

        lines = content.splitlines()
        for idx, line in enumerate(lines):
            normalized = line.strip()
            if normalized == title or normalized == f"# {title}":
                if idx > 0:
                    return "\n".join(lines[idx:]).strip()
                return content
        return content

    def _fetch_html_fallback(self, url: str) -> tuple[str, str]:
        """Fetch raw HTML directly when Firecrawl returns no useful markdown."""
        request = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/123.0.0.0 Safari/537.36"
                )
            },
        )
        try:
            with urlopen(request, timeout=20) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                html = response.read().decode(charset, errors="replace")
                return html, ""
        except (URLError, TimeoutError, ValueError) as exc:
            return "", str(exc)

    def _extract_html_title(self, html: str) -> str:
        match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return ""
        return self._normalize_html_text(match.group(1))

    def _extract_meta_description(self, html: str) -> str:
        patterns = [
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
            r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
            if match:
                return self._normalize_html_text(match.group(1))
        return ""

    def _normalize_html_text(self, text: str) -> str:
        cleaned = unescape(re.sub(r"\s+", " ", text or "")).strip()
        return cleaned

    def _extract_domains_from_urls(self, urls: list[str]) -> list[str]:
        domains = []
        seen = set()
        for value in urls:
            if not value:
                continue
            parsed = urlparse(value if "://" in value else f"https://{value}")
            host = (parsed.netloc or parsed.path or "").strip().lower()
            if host.startswith("www."):
                host = host[4:]
            if not host or "." not in host or host in seen:
                continue
            seen.add(host)
            domains.append(host)
        return domains

    def _extract_canonical_metadata(self, html: str) -> tuple[str, list[str]]:
        if not html:
            return "", []

        urls = []
        patterns = [
            r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\'](.*?)["\']',
            r'<link[^>]+rel=["\']alternate["\'][^>]+href=["\'](.*?)["\']',
            r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\'](.*?)["\']',
            r'"url"\s*:\s*"(https?://[^"]+)"',
        ]
        for pattern in patterns:
            urls.extend(
                match.strip()
                for match in re.findall(pattern, html, flags=re.IGNORECASE | re.DOTALL)
                if match and isinstance(match, str)
            )

        canonical_url = urls[0] if urls else ""
        alternate_domains = self._extract_domains_from_urls(urls)
        return canonical_url, alternate_domains

    def _html_to_markdown_fallback(self, html: str) -> str:
        """Extract a minimal, readable text snapshot from raw HTML."""
        if not html:
            return ""

        title = self._extract_html_title(html)
        meta_description = self._extract_meta_description(html)

        body = re.sub(
            r"<(script|style|noscript|svg|iframe)[^>]*>.*?</\1>",
            " ",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )

        block_matches = re.findall(
            r"<(h1|h2|h3|p|li)[^>]*>(.*?)</\1>",
            body,
            flags=re.IGNORECASE | re.DOTALL,
        )

        lines = []
        seen = set()
        for _, fragment in block_matches:
            text = re.sub(r"<[^>]+>", " ", fragment)
            text = self._normalize_html_text(text)
            if not text or len(text) < 12:
                continue
            lowered = text.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            lines.append(text)
            if len(lines) >= 24:
                break

        content_parts = []
        if title:
            content_parts.append(f"# {title}")
        if meta_description and meta_description.lower() != title.lower():
            content_parts.append(meta_description)
        content_parts.extend(lines)

        return "\n\n".join(part for part in content_parts if part).strip()

    def scrape(self, url: str) -> WebData:
        """Scrape a website and return structured data."""
        data = WebData(url=url)

        # Basic scrape
        result = self._run_firecrawl(url)
        if "error" not in result:
            data.markdown_content = self._clean_markdown_content(result.get("content", ""))
            data.title = self._extract_title(data.markdown_content)
            data.markdown_content = self._trim_to_title(data.markdown_content, data.title)
        else:
            data.error = result["error"]

        if not data.markdown_content:
            html, html_error = self._fetch_html_fallback(url)
            if html:
                data.html = html
                data.canonical_url, data.alternate_domains = self._extract_canonical_metadata(html)
                data.meta_description = self._extract_meta_description(html)
                data.title = self._extract_html_title(html) or data.title
                data.markdown_content = self._html_to_markdown_fallback(html)
                data.markdown_content = self._trim_to_title(data.markdown_content, data.title)
                data.error = ""
            elif html_error and not data.error:
                data.error = html_error

        return data

    def scrape_multiple(self, urls: list[str]) -> list[WebData]:
        """Scrape multiple URLs."""
        return [self.scrape(url) for url in urls]
