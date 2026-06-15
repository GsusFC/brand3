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
import time
from dataclasses import dataclass
from html import unescape
from urllib.parse import urlparse
from urllib.error import URLError
from urllib.request import Request, urlopen

_MIN_USABLE_MARKDOWN_CHARS = 200
_TRANSIENT_FETCH_ATTEMPTS = 2
_TRANSIENT_FETCH_DELAY_S = 1.5
_DESKTOP_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

_MAX_OWNED_SUBPAGES = 4
_OWNED_PAGE_ROLE_PRIORITY = ("product", "solutions", "about", "customers", "case_studies", "reviews", "testimonials", "pricing", "trust")


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
    # Set when a capture was wiped because it looked like a consent wall —
    # downstream can then tell "obstructed" apart from "empty" or "failed".
    capture_obstruction: str = ""
    content_source: str = ""
    browser_status: int | None = None
    owned_fallback_urls: list[str] = None

    def __post_init__(self):
        self.links = self.links or []
        self.alternate_domains = self.alternate_domains or []
        self.images = self.images or []
        self.tech_stack = self.tech_stack or []
        self.owned_fallback_urls = self.owned_fallback_urls or []


class WebCollector:
    """Collects web data via Firecrawl CLI."""

    COOKIE_BANNER_KEYWORDS = [
        "aceptar",
        "rechazar cookies",
        "cookie preferences",
        "manage cookies",
        "accept cookies",
        "consent",
    ]

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
        last_error = ""
        for attempt in range(_TRANSIENT_FETCH_ATTEMPTS):
            try:
                from firecrawl import Firecrawl

                doc = Firecrawl(api_key=self.api_key).scrape(
                    url,
                    formats=["markdown", "html"],
                    timeout=60000,
                    wait_for=2000,
                    only_main_content=True,
                )
                break
            except Exception as exc:
                # Transient network failures are the common case here; one
                # retry keeps the capture on the best tier instead of
                # degrading to the HTML/browser fallbacks.
                last_error = str(exc)
                if attempt + 1 < _TRANSIENT_FETCH_ATTEMPTS:
                    time.sleep(_TRANSIENT_FETCH_DELAY_S)
        else:
            return {"error": last_error}
        content = (doc.markdown or "").strip()
        html = (getattr(doc, "html", None) or "").strip()
        return {"content": content, "raw": content, "html": html}

    def _looks_like_cookie_banner(self, title: str, content: str) -> bool:
        title_lower = (title or "").lower()
        preview_lower = (content or "")[:200].lower()
        return any(
            keyword in title_lower or keyword in preview_lower
            for keyword in self.COOKIE_BANNER_KEYWORDS
        )

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
                "User-Agent": _DESKTOP_USER_AGENT
            },
        )
        try:
            with urlopen(request, timeout=20) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                html = response.read().decode(charset, errors="replace")
                return html, ""
        except (URLError, TimeoutError, ValueError) as exc:
            return "", str(exc)

    def _fetch_browser_fallback(self, url: str) -> tuple[dict, str]:
        """Render a page in Chromium when static fetches cannot see useful text."""
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            return {}, f"playwright unavailable: {exc}"

        browser = None
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=_DESKTOP_USER_AGENT,
                    viewport={"width": 1440, "height": 1200},
                )
                page = context.new_page()
                response = page.goto(url, wait_until="domcontentloaded", timeout=45000)
                try:
                    page.wait_for_load_state("networkidle", timeout=12000)
                except PlaywrightTimeoutError:
                    pass

                self._dismiss_cookie_banners(page)

                html = page.content()
                title = page.title() or ""
                body_text = page.locator("body").inner_text(timeout=5000)
                meta_description = page.evaluate(
                    """() => {
                        const el = document.querySelector("meta[name='description'], meta[property='og:description']");
                        return el ? (el.getAttribute("content") || "") : "";
                    }"""
                )
                canonical_url = page.evaluate(
                    """() => {
                        const canonical = document.querySelector("link[rel='canonical']");
                        if (canonical) return canonical.href || canonical.getAttribute("href") || "";
                        const og = document.querySelector("meta[property='og:url']");
                        return og ? (og.getAttribute("content") || "") : "";
                    }"""
                )
                links = page.eval_on_selector_all(
                    "a[href]",
                    """els => els.map(a => a.href).filter(Boolean).slice(0, 80)""",
                )
                status = response.status if response else None
                context.close()
                browser.close()
                browser = None
                return {
                    "status": status,
                    "title": title,
                    "meta_description": meta_description,
                    "canonical_url": canonical_url,
                    "body_text": body_text,
                    "html": html,
                    "links": links,
                }, ""
        except Exception as exc:
            if browser:
                try:
                    browser.close()
                except Exception:
                    pass
            return {}, str(exc)

    def _dismiss_cookie_banners(self, page) -> None:
        """Attempt to click typical cookie consent buttons with short timeouts."""
        combined_selector = (
            "button:has-text('Aceptar'), button:has-text('Accept'), button:has-text('Rechazar'), "
            "button:has-text('Cerrar'), button:has-text('Agree'), button:has-text('Allow all'), "
            "button:has-text('Accept all'), button:has-text('Close'), button:has-text('OK'), "
            "a:has-text('Aceptar'), a:has-text('Accept'), a:has-text('Cerrar'), a:has-text('Close'), "
            "#cookie-accept, #accept-cookies, .cookie-accept, .accept-cookies"
        )
        try:
            page.locator(combined_selector).first.click(timeout=500)
        except Exception:
            pass

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

    def _has_usable_markdown_content(self, content: str) -> bool:
        return len((content or "").strip()) >= _MIN_USABLE_MARKDOWN_CHARS

    def _body_text_to_markdown(
        self,
        body_text: str,
        *,
        title: str = "",
        meta_description: str = "",
    ) -> str:
        lines = []
        seen = set()
        for raw_line in (body_text or "").splitlines():
            line = self._normalize_html_text(raw_line)
            if not line or len(line) < 3:
                continue
            lowered = line.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            lines.append(line)

        content_parts = []
        if title:
            content_parts.append(f"# {title}")
        if meta_description and meta_description.lower() != title.lower():
            content_parts.append(meta_description)
        content_parts.extend(lines)
        return self._clean_markdown_content(
            "\n\n".join(part for part in content_parts if part).strip()
        )
    def _extract_internal_links(
        self,
        markdown: str,
        base_url: str,
        *,
        html: str = "",
        links: list[str] | None = None,
    ) -> list[str]:
        """Extract absolute internal page links from observed Markdown, HTML, and browser links."""
        if not base_url:
            return []

        from urllib.parse import urljoin

        parsed_base = urlparse(base_url)
        base_domain = parsed_base.netloc.lower()
        if base_domain.startswith("www."):
            base_domain = base_domain[4:]

        candidates = []
        candidates.extend(re.findall(r'\[[^\]]*\]\(([^)]+)\)', markdown or ""))
        candidates.extend(re.findall(r'href=["\']([^"\']+)["\']', html or "", flags=re.IGNORECASE))
        candidates.extend(links or [])

        internal_links = []
        seen = set()

        for link in candidates:
            link = str(link or "").strip()
            if not link or link.startswith("#") or link.startswith("javascript:") or link.startswith("mailto:") or link.startswith("tel:"):
                continue

            absolute_url = urljoin(base_url, link)

            try:
                parsed_link = urlparse(absolute_url)
                link_domain = parsed_link.netloc.lower()
                if link_domain.startswith("www."):
                    link_domain = link_domain[4:]

                if link_domain == base_domain and self._looks_like_page_link(parsed_link.path):
                    normalized = parsed_link._replace(fragment="").geturl()
                    normalized = normalized.rstrip("/")
                    base_normalized = base_url.rstrip("/")
                    if normalized not in seen and normalized != base_normalized:
                        seen.add(normalized)
                        internal_links.append(normalized)
            except Exception:
                continue

        return internal_links

    @staticmethod
    def _looks_like_page_link(path: str) -> bool:
        lowered = (path or "").lower()
        blocked_extensions = (
            ".css",
            ".js",
            ".json",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".webp",
            ".ico",
            ".pdf",
            ".zip",
            ".mp4",
            ".mov",
            ".webm",
        )
        return not lowered.endswith(blocked_extensions)

    def _score_internal_links(self, links: list[str], base_url: str) -> list[str]:
        """Score and sort internal links based on their relevance keywords."""
        high_value = {
            "pricing": 10,
            "precios": 10,
            "feature": 8,
            "product": 8,
            "producto": 8,
            "platform": 8,
            "plataforma": 8,
            "solution": 7,
            "solucion": 7,
            "about": 6,
            "nosotros": 6,
            "company": 5,
            "how": 5,
            "service": 5,
            "servicio": 5,
            "technology": 5,
            "tecnologia": 5,
            "customer": 6,
            "customers": 6,
            "client": 6,
            "clientes": 6,
            "case-stud": 6,
            "success-stor": 6,
            "casos": 6,
            "reviews": 6,
            "resenas": 6,
            "reseñas": 6,
            "opiniones": 6,
            "testimonial": 6,
            "testimonio": 6,
        }
        
        low_value = {
            "blog": -5,
            "news": -5,
            "press": -5,
            "contact": -3,
            "contacto": -3,
            "support": -5,
            "soporte": -5,
            "help": -5,
            "faq": -5,
            "privacy": -10,
            "terms": -10,
            "condiciones": -10,
            "legal": -10,
            "login": -8,
            "signin": -8,
            "signup": -8,
            "register": -8,
            "careers": -5,
            "jobs": -5,
            "empleo": -5,
        }
        
        scored_links = []
        for link in links:
            parsed = urlparse(link)
            path = parsed.path.lower()
            query = parsed.query.lower()
            
            score = 0
            for kw, weight in high_value.items():
                if kw in path or kw in query:
                    score += weight
                    
            for kw, penalty in low_value.items():
                if kw in path or kw in query:
                    score += penalty
                    
            if score >= -2:
                scored_links.append((score, link))
                
        scored_links.sort(key=lambda x: x[0], reverse=True)
        return [link for _, link in scored_links]

    def _select_internal_links_to_crawl(self, links: list[str], base_url: str) -> list[str]:
        scored_links = self._score_internal_links(links, base_url)
        selected: list[str] = []

        for role in _OWNED_PAGE_ROLE_PRIORITY:
            for link in scored_links:
                if link in selected:
                    continue
                if self._link_role(link) == role:
                    selected.append(link)
                    break
            if len(selected) >= _MAX_OWNED_SUBPAGES:
                return selected

        for link in scored_links:
            if link in selected:
                continue
            selected.append(link)
            if len(selected) >= _MAX_OWNED_SUBPAGES:
                break

        return selected

    @staticmethod
    def _link_role(link: str) -> str:
        path = urlparse(link).path.lower()
        if any(marker in path for marker in ("pricing", "precios", "plans")):
            return "pricing"
        if any(marker in path for marker in ("customer", "client", "clientes")):
            return "customers"
        if any(marker in path for marker in ("case-stud", "success-stor", "stories", "casos")):
            return "case_studies"
        if any(marker in path for marker in ("reviews", "resenas", "reseñas", "opiniones")):
            return "reviews"
        if any(marker in path for marker in ("testimonial", "testimonio")):
            return "testimonials"
        if any(marker in path for marker in ("security", "trust", "privacy", "compliance")):
            return "trust"
        if any(marker in path for marker in ("about", "company", "nosotros", "manifesto")):
            return "about"
        if any(marker in path for marker in ("solution", "solucion", "use-case", "industry")):
            return "solutions"
        if any(marker in path for marker in ("feature", "product", "producto", "platform", "plataforma")):
            return "product"
        return "other"


    def scrape(self, url: str, crawl_subpages: bool = True) -> WebData:
        """Scrape a website and return structured data."""
        data = WebData(url=url)

        # Basic scrape
        result = self._run_firecrawl(url)
        if "error" not in result:
            data.markdown_content = self._clean_markdown_content(result.get("content", ""))
            data.html = result.get("html", "") or data.html
            data.title = self._extract_title(data.markdown_content)
            data.markdown_content = self._trim_to_title(data.markdown_content, data.title)
            if self._looks_like_cookie_banner(data.title, data.markdown_content):
                print(
                    f"  WARNING: scrape may be cookie banner, not content"
                    f" (title: {data.title[:80]})"
                )
                data.title = ""
                data.markdown_content = ""
                data.capture_obstruction = "cookie_banner"
        else:
            data.error = result["error"]

        if not self._has_usable_markdown_content(data.markdown_content):
            html, html_error = self._fetch_html_fallback(url)
            if html:
                data.html = html
                data.canonical_url, data.alternate_domains = self._extract_canonical_metadata(html)
                data.meta_description = self._extract_meta_description(html)
                data.title = self._extract_html_title(html) or data.title
                data.markdown_content = self._html_to_markdown_fallback(html)
                data.markdown_content = self._trim_to_title(data.markdown_content, data.title)
                data.error = ""
                data.capture_obstruction = ""
            elif html_error and not data.error:
                data.error = html_error

        if not self._has_usable_markdown_content(data.markdown_content):
            payload, browser_error = self._fetch_browser_fallback(url)
            if payload:
                data.html = payload.get("html") or data.html
                data.links = payload.get("links") or data.links
                data.browser_status = payload.get("status")
                data.title = payload.get("title") or data.title
                data.meta_description = payload.get("meta_description") or data.meta_description
                data.canonical_url = payload.get("canonical_url") or data.canonical_url
                data.markdown_content = self._body_text_to_markdown(
                    payload.get("body_text") or "",
                    title=data.title,
                    meta_description=data.meta_description,
                )
                data.markdown_content = self._trim_to_title(data.markdown_content, data.title)
                if self._looks_like_cookie_banner(data.title, data.markdown_content):
                    print(
                        f"  WARNING: browser fallback may be cookie banner, not content"
                        f" (title: {data.title[:80]})"
                    )
                    data.markdown_content = ""
                    data.capture_obstruction = "cookie_banner"
                if self._has_usable_markdown_content(data.markdown_content):
                    data.content_source = "browser_fallback"
                    data.error = ""
                    data.capture_obstruction = ""
            elif browser_error and not data.error:
                data.error = browser_error

        if crawl_subpages and self._has_usable_markdown_content(data.markdown_content):
            internal_links = self._extract_internal_links(
                data.markdown_content,
                url,
                html=data.html,
                links=data.links,
            )
            subpages_to_crawl = self._select_internal_links_to_crawl(internal_links, url)
            
            subpage_contents = []
            owned_fallback_urls = []
            for subpage_url in subpages_to_crawl:
                subpage_data = self.scrape(subpage_url, crawl_subpages=False)
                if subpage_data.markdown_content:
                    owned_fallback_urls.append(subpage_url)
                    subpage_contents.append(
                        f"\n\n---\n## Subpage: {subpage_url}\n{subpage_data.markdown_content}"
                    )
            
            if subpage_contents:
                data.markdown_content += "".join(subpage_contents)
                data.owned_fallback_urls = list(dict.fromkeys(data.owned_fallback_urls + owned_fallback_urls))

        return data


    def scrape_multiple(self, urls: list[str]) -> list[WebData]:
        """Scrape multiple URLs."""
        return [self.scrape(url) for url in urls]
