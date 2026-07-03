"""Tests for GitHub proof link observation and org-level fallback."""

from types import SimpleNamespace

from src.collectors.github_proof_collector import (
    GitHubProofCollector,
    GitHubRepoProof,
    _extract_org_slugs,
    observed_github_urls_from_web_data,
)


def test_observed_urls_include_links_from_raw_html() -> None:
    web_data = SimpleNamespace(
        links=[],
        markdown_content="# Acme\nNo links survive markdown capture.",
        html='<footer><a href="https://github.com/vercel">GitHub</a></footer>',
    )

    urls = observed_github_urls_from_web_data(web_data)

    assert "https://github.com/vercel" in urls


def test_extract_org_slugs_accepts_org_level_urls_and_skips_repo_urls() -> None:
    orgs = _extract_org_slugs(
        [
            "https://github.com/vercel",
            "https://github.com/vercel/next.js",
            "https://github.com/about",
            "https://github.com/Vercel/",
        ]
    )

    assert orgs == [("vercel", "https://github.com/vercel")]


def test_collect_resolves_org_repos_when_no_repo_links_observed() -> None:
    class StubCollector(GitHubProofCollector):
        def _fetch_org_repos(self, org: str, *, source_url: str) -> tuple[list[GitHubRepoProof], str]:
            proof = GitHubRepoProof(
                full_name=f"{org}/next.js",
                html_url=f"https://github.com/{org}/next.js",
                stars=120000,
                source_url=source_url,
            )
            return [proof], ""

    data = StubCollector().collect("Vercel", "https://vercel.com", ["https://github.com/vercel"])

    assert data.status == "ok"
    assert [repo.full_name for repo in data.repos] == ["vercel/next.js"]
    assert data.diagnostics["observed_org_count"] == 1
    assert data.diagnostics["observed_repo_count"] == 0


def test_collect_still_skips_when_no_github_links_observed() -> None:
    data = GitHubProofCollector().collect("Acme", "https://acme.example", ["https://acme.example/about"])

    assert data.status == "skipped"
    assert "no GitHub repository links observed" in data.diagnostics["reason"]
