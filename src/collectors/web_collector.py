"""
Web collector using Firecrawl.

Scrapes the brand's website and extracts:
- HTML structure, meta tags, content
- Visual assets (logo, colors — via screenshots)
- Tech stack detection
- Page speed signals
"""

import re
import subprocess
import json
from dataclasses import dataclass


@dataclass
class WebData:
    """Raw web data from scraping."""
    url: str
    title: str = ""
    meta_description: str = ""
    markdown_content: str = ""
    html: str = ""
    links: list = None
    images: list = None
    screenshot_path: str = ""
    tech_stack: list[str] = None
    load_time_ms: int = 0
    error: str = ""

    def __post_init__(self):
        self.links = self.links or []
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

    def __init__(self, api_key: str = None):
        self.api_key = api_key

    def _run_firecrawl(self, url: str, options: list[str] = None) -> dict:
        """Run firecrawl CLI and return parsed output."""
        cmd = ["firecrawl", "scrape", url, "--format", "markdown"]
        if options:
            cmd.extend(options)

        env = None
        if self.api_key:
            import os
            env = {**os.environ, "FIRECRAWL_API_KEY": self.api_key}

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, env=env
        )

        if result.returncode != 0:
            return {"error": result.stderr}

        # Parse output — skip first line (Scrape ID)
        lines = result.stdout.strip().split("\n")
        content = "\n".join(lines[1:]) if lines else ""
        return {"content": content, "raw": result.stdout}

    def _clean_markdown_content(self, content: str) -> str:
        """Remove obvious cookie/consent UI sludge from scraped markdown."""
        if not content:
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

    def scrape(self, url: str) -> WebData:
        """Scrape a website and return structured data."""
        data = WebData(url=url)

        # Basic scrape
        result = self._run_firecrawl(url)
        if "error" in result:
            data.error = result["error"]
            return data

        data.markdown_content = self._clean_markdown_content(result.get("content", ""))
        data.title = self._extract_title(data.markdown_content)
        data.markdown_content = self._trim_to_title(data.markdown_content, data.title)

        return data

    def scrape_multiple(self, urls: list[str]) -> list[WebData]:
        """Scrape multiple URLs."""
        return [self.scrape(url) for url in urls]
