"""GitHub repository proof collector for developer/tooling brands."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
import re
import time
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


GITHUB_API_URL = "https://api.github.com"
GITHUB_PROOF_VERSION = "github-proof-v1"
USER_AGENT = "Brand3/0.1"
_GITHUB_REPO_RE = re.compile(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")
_GITHUB_URL_RE = re.compile(r"https?://github\.com/[^\s\"'<>)\]]+")
_GITHUB_ORG_RE = re.compile(r"github\.com/([A-Za-z0-9_.-]+)/?$")
_MAX_ORGS = 2
_NON_REPO_NAMES = {
    "about",
    "apps",
    "blog",
    "collections",
    "contact",
    "customer-stories",
    "enterprise",
    "explore",
    "features",
    "marketplace",
    "mobile",
    "new",
    "notifications",
    "organizations",
    "pricing",
    "security",
    "settings",
    "sponsors",
    "topics",
}


@dataclass(slots=True)
class GitHubRepoProof:
    full_name: str
    html_url: str
    description: str = ""
    stars: int = 0
    forks: int = 0
    watchers: int = 0
    open_issues: int = 0
    topics: list[str] = field(default_factory=list)
    license_name: str = ""
    language: str = ""
    pushed_at: str = ""
    updated_at: str = ""
    archived: bool = False
    disabled: bool = False
    source_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "full_name": self.full_name,
            "html_url": self.html_url,
            "description": self.description,
            "stars": self.stars,
            "forks": self.forks,
            "watchers": self.watchers,
            "open_issues": self.open_issues,
            "topics": list(self.topics),
            "license_name": self.license_name,
            "language": self.language,
            "pushed_at": self.pushed_at,
            "updated_at": self.updated_at,
            "archived": self.archived,
            "disabled": self.disabled,
            "source_url": self.source_url,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GitHubRepoProof":
        return cls(
            full_name=str(data.get("full_name") or ""),
            html_url=str(data.get("html_url") or ""),
            description=str(data.get("description") or ""),
            stars=int(data.get("stars") or 0),
            forks=int(data.get("forks") or 0),
            watchers=int(data.get("watchers") or 0),
            open_issues=int(data.get("open_issues") or 0),
            topics=[str(item) for item in data.get("topics") or [] if str(item).strip()],
            license_name=str(data.get("license_name") or ""),
            language=str(data.get("language") or ""),
            pushed_at=str(data.get("pushed_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
            archived=bool(data.get("archived")),
            disabled=bool(data.get("disabled")),
            source_url=str(data.get("source_url") or ""),
        )


@dataclass(slots=True)
class GitHubProofData:
    brand_name: str
    brand_url: str
    provider: str = "github"
    status: str = "ok"
    repos: list[GitHubRepoProof] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": GITHUB_PROOF_VERSION,
            "provider": self.provider,
            "status": self.status,
            "brand_name": self.brand_name,
            "brand_url": self.brand_url,
            "repos": [repo.to_dict() for repo in self.repos],
            "diagnostics": dict(self.diagnostics),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GitHubProofData":
        repos = data.get("repos") if isinstance(data.get("repos"), list) else []
        return cls(
            brand_name=str(data.get("brand_name") or ""),
            brand_url=str(data.get("brand_url") or ""),
            provider=str(data.get("provider") or "github"),
            status=str(data.get("status") or "ok"),
            repos=[GitHubRepoProof.from_dict(item) for item in repos if isinstance(item, dict)],
            diagnostics=data.get("diagnostics") if isinstance(data.get("diagnostics"), dict) else {},
        )


class GitHubProofCollector:
    """Fetch public GitHub repository metrics for repos observed on owned pages."""

    def __init__(
        self,
        token: str | None = None,
        *,
        timeout_seconds: int = 8,
        limit: int = 3,
    ) -> None:
        self.token = (token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()
        self.timeout_seconds = max(1, int(timeout_seconds or 8))
        self.limit = max(1, min(int(limit or 3), 5))

    def collect(self, brand_name: str, brand_url: str, observed_urls: list[str]) -> GitHubProofData:
        repos = _extract_repo_slugs(observed_urls)[: self.limit]
        # Org-level links (github.com/<org>, the common footer pattern) only
        # resolve when no explicit repo link was observed.
        orgs = [] if repos else _extract_org_slugs(observed_urls)[:_MAX_ORGS]
        if not repos and not orgs:
            return GitHubProofData(
                brand_name=brand_name,
                brand_url=brand_url,
                status="skipped",
                diagnostics={"reason": "no GitHub repository links observed on owned capture"},
            )
        proofs: list[GitHubRepoProof] = []
        errors: list[dict[str, str]] = []
        for slug, source_url in repos:
            proof, error = self._fetch_repo(slug, source_url=source_url)
            if proof:
                proofs.append(proof)
            elif error:
                errors.append({"repo": slug, "error": error})
        for org, source_url in orgs:
            org_proofs, error = self._fetch_org_repos(org, source_url=source_url)
            proofs.extend(org_proofs[: max(0, self.limit - len(proofs))])
            if error:
                errors.append({"repo": org, "error": error})
        status = "ok" if proofs else "error"
        if proofs and errors:
            status = "partial"
        return GitHubProofData(
            brand_name=brand_name,
            brand_url=brand_url,
            status=status,
            repos=proofs,
            diagnostics={
                "strategy": GITHUB_PROOF_VERSION,
                "observed_repo_count": len(repos),
                "observed_org_count": len(orgs),
                "fetched_repo_count": len(proofs),
                "errors": errors,
            },
        )

    def _fetch_repo(self, slug: str, *, source_url: str) -> tuple[GitHubRepoProof | None, str]:
        request = Request(
            f"{GITHUB_API_URL}/repos/{slug}",
            headers=self._headers(),
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            return None, _http_error_message(exc)
        except Exception as exc:
            return None, str(exc)
        if not isinstance(payload, dict):
            return None, "github_response_not_object"
        return _proof_from_payload(payload, slug=slug, source_url=source_url), ""

    def _fetch_org_repos(self, org: str, *, source_url: str) -> tuple[list[GitHubRepoProof], str]:
        request = Request(
            f"{GITHUB_API_URL}/orgs/{org}/repos?per_page=30&type=public",
            headers=self._headers(),
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            return [], _http_error_message(exc)
        except Exception as exc:
            return [], str(exc)
        if not isinstance(payload, list):
            return [], "github_org_response_not_list"
        entries = [item for item in payload if isinstance(item, dict) and not item.get("archived")]
        entries.sort(key=lambda item: int(item.get("stargazers_count") or 0), reverse=True)
        return (
            [
                _proof_from_payload(item, slug=str(item.get("full_name") or f"{org}/unknown"), source_url=source_url)
                for item in entries[: self.limit]
            ],
            "",
        )

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers


def observed_github_urls_from_web_data(web_data: Any) -> list[str]:
    if web_data is None:
        return []
    urls: list[str] = []
    for item in getattr(web_data, "links", None) or []:
        if "github.com/" in str(item).lower():
            urls.append(str(item))
    # Markdown captures usually strip hrefs, so the raw HTML is often the only
    # place footer/nav GitHub links survive.
    for attr in ("markdown_content", "html"):
        text = str(getattr(web_data, attr, "") or "")
        urls.extend(match.group(0) for match in _GITHUB_URL_RE.finditer(text))
    return urls


def _proof_from_payload(payload: dict[str, Any], *, slug: str, source_url: str) -> GitHubRepoProof:
    license_payload = payload.get("license") if isinstance(payload.get("license"), dict) else {}
    return GitHubRepoProof(
        full_name=str(payload.get("full_name") or slug),
        html_url=str(payload.get("html_url") or f"https://github.com/{slug}"),
        description=str(payload.get("description") or ""),
        stars=int(payload.get("stargazers_count") or 0),
        forks=int(payload.get("forks_count") or 0),
        watchers=int(payload.get("watchers_count") or 0),
        open_issues=int(payload.get("open_issues_count") or 0),
        topics=[str(item) for item in payload.get("topics") or [] if str(item).strip()],
        license_name=str(license_payload.get("name") or ""),
        language=str(payload.get("language") or ""),
        pushed_at=str(payload.get("pushed_at") or ""),
        updated_at=str(payload.get("updated_at") or ""),
        archived=bool(payload.get("archived")),
        disabled=bool(payload.get("disabled")),
        source_url=source_url,
    )


def _extract_org_slugs(urls: list[str]) -> list[tuple[str, str]]:
    seen: set[str] = set()
    orgs: list[tuple[str, str]] = []
    for raw_url in urls:
        url = str(raw_url or "").strip()
        if _GITHUB_REPO_RE.search(url):
            continue
        match = _GITHUB_ORG_RE.search(url)
        if not match:
            continue
        org = match.group(1).strip(".")
        if not org or org.lower() in _NON_REPO_NAMES:
            continue
        key = org.lower()
        if key in seen:
            continue
        seen.add(key)
        orgs.append((org, url))
    return orgs


def _extract_repo_slugs(urls: list[str]) -> list[tuple[str, str]]:
    seen: set[str] = set()
    repos: list[tuple[str, str]] = []
    for raw_url in urls:
        url = str(raw_url or "").strip()
        match = _GITHUB_REPO_RE.search(url)
        if not match:
            continue
        owner = match.group(1).strip(".")
        repo = match.group(2).strip(".")
        if not owner or not repo or owner.lower() in _NON_REPO_NAMES or repo.lower() in _NON_REPO_NAMES:
            continue
        slug = f"{owner}/{repo}"
        key = slug.lower()
        if key in seen:
            continue
        seen.add(key)
        repos.append((slug, url))
    return repos


def _http_error_message(exc: HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8")[:500]
    except Exception:
        body = ""
    return f"HTTP {exc.code}: {body}".strip()


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)
