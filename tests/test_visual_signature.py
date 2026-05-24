from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.collectors.web_collector import WebData
from src.visual_signature import extract_visual_signature
from src.visual_signature.adapters.firecrawl_adapter import FirecrawlVisualSignatureAdapter
from src.visual_signature.types import (
    VisualAcquisitionResult,
    VisualAssetCandidate,
    VisualSignatureInput,
)


FIXTURE_HTML = """
<html>
  <head>
    <link rel="icon" href="/favicon.ico">
    <style>
      :root { --brand: #2255ff; --surface: #ffffff; }
      body { background: #ffffff; color: #111111; font-family: Inter, sans-serif; font-size: 16px; font-weight: 400; }
      h1 { font-family: Inter, sans-serif; font-size: 52px; font-weight: 700; color: rgb(17, 17, 17); }
      .hero { display: grid; background: #f5f7fb; }
      .cards { display: flex; }
      .button.primary.cta { background: #2255ff; color: #ffffff; }
    </style>
  </head>
  <body>
    <header>
      <nav>
        <img src="https://example.com/logo.svg" alt="Example Brand logo">
        <a href="/product">Product</a>
        <a href="/pricing">Pricing</a>
      </nav>
    </header>
    <main>
      <section class="hero grid">
        <h1>Example Brand</h1>
        <a class="button primary cta" href="/start">Get started</a>
      </section>
      <section class="cards">
        <article class="card">Workflow signal</article>
      </section>
    </main>
    <footer>Example Brand</footer>
  </body>
</html>
"""


def _web_data() -> WebData:
    return WebData(
        url="https://example.com",
        title="Example Brand",
        meta_description="Fixture brand",
        markdown_content="# Example Brand\n[Get started](https://example.com/start)",
        html=FIXTURE_HTML,
        canonical_url="https://example.com",
        links=["https://example.com/start"],
        images=["https://example.com/logo.svg", "https://example.com/icon.svg"],
        screenshot_path="https://example.com/screenshot.png",
        browser_status=200,
    )


@dataclass
class RaisingAdapter:
    name = "custom"
    called: bool = False

    def acquire(self, input_data: VisualSignatureInput) -> VisualAcquisitionResult:
        self.called = True
        raise AssertionError("adapter should not be called when web_data is provided")


@dataclass
class FixtureAdapter:
    name = "custom"
    called: bool = False

    def acquire(self, input_data: VisualSignatureInput) -> VisualAcquisitionResult:
        self.called = True
        return VisualAcquisitionResult(
            adapter="custom",
            requested_url=input_data.website_url,
            final_url=input_data.website_url,
            status_code=200,
            rendered_html=FIXTURE_HTML,
            raw_html=FIXTURE_HTML,
            markdown="# Example Brand\n[Get started](https://example.com/start)",
            links=["https://example.com/start"],
            images=[
                VisualAssetCandidate(
                    url="https://example.com/logo.svg",
                    alt="Example Brand logo",
                    source="images",
                    role_hint="logo",
                )
            ],
            metadata={"favicon": "https://example.com/favicon.ico"},
            acquired_at="2026-05-08T00:00:00",
        )


@dataclass
class FailureAdapter:
    name = "custom"

    def acquire(self, input_data: VisualSignatureInput) -> VisualAcquisitionResult:
        return VisualAcquisitionResult(
            adapter="custom",
            requested_url=input_data.website_url,
            final_url=input_data.website_url,
            errors=["fixture acquisition failure"],
            acquired_at="2026-05-08T00:00:00",
        )


class FakeSuccessfulWebCollector:
    def scrape(self, url: str) -> WebData:
        data = _web_data()
        data.url = url
        return data


class FakeFailingWebCollector:
    def scrape(self, url: str) -> WebData:
        raise RuntimeError("firecrawl fixture failure")


def test_extract_visual_signature_reuses_existing_web_data_without_adapter_call():
    adapter = RaisingAdapter()

    result = extract_visual_signature(
        brand_name="Example Brand",
        website_url="https://example.com",
        web_data=_web_data(),
        adapter=adapter,
    )

    assert adapter.called is False
    assert result["version"] == "visual-signature-mvp-1"
    assert result["interpretation_status"] == "interpretable"
    assert result["acquisition"]["adapter"] == "existing_web_data"
    assert result["colors"]["palette"]
    assert "#2255ff" in result["colors"]["accent_candidates"]
    assert result["typography"]["font_families"][0]["family"] == "Inter"
    assert result["logo"]["logo_detected"] is True
    assert result["layout"]["has_navigation"] is True
    assert "grid" in result["layout"]["layout_patterns"]
    assert result["components"]["primary_ctas"] == ["Get started"]
    assert result["assets"]["screenshot_available"] is True
    assert result["consistency"]["overall_consistency"] > 0
    assert result["extraction_confidence"]["score"] > 0.45


def test_extract_visual_signature_uses_adapter_when_no_existing_web_data():
    adapter = FixtureAdapter()

    result = extract_visual_signature(
        brand_name="Example Brand",
        website_url="https://example.com",
        adapter=adapter,
    )

    assert adapter.called is True
    assert result["acquisition"]["adapter"] == "custom"
    assert result["interpretation_status"] == "interpretable"
    assert result["logo"]["favicon_detected"] is True
    assert result["assets"]["logo_image_candidates"][0]["role_hint"] == "logo"


def test_extract_visual_signature_adds_dom_obstruction_evidence():
    html = """
    <html><body>
      <main><h1>Example Brand</h1></main>
      <div class="cookie-consent fixed bottom-0 z-50" style="position: fixed; bottom: 0; height: 20vh; z-index: 9999;">
        We use cookies. Manage privacy preferences.
      </div>
    </body></html>
    """
    web_data = _web_data()
    web_data.html = html

    result = extract_visual_signature(
        brand_name="Example Brand",
        website_url="https://example.com",
        web_data=web_data,
    )

    obstruction = result["acquisition"]["viewport_obstruction"]
    assert obstruction["present"] is True
    assert obstruction["type"] == "cookie_banner"
    assert obstruction["severity"] in {"moderate", "major"}
    assert obstruction["first_impression_valid"] is False
    assert "dom_keyword:cookie" in obstruction["signals"]


def test_firecrawl_adapter_successful_acquisition_uses_web_collector_result():
    adapter = FirecrawlVisualSignatureAdapter(
        api_key="fixture-key",
        web_collector=FakeSuccessfulWebCollector(),
    )

    acquisition = adapter.acquire(VisualSignatureInput("Example Brand", "https://example.com"))

    assert acquisition.adapter == "firecrawl"
    assert acquisition.errors == []
    assert acquisition.rendered_html == FIXTURE_HTML
    assert acquisition.status_code == 200


def test_firecrawl_adapter_acquisition_failure_is_captured():
    adapter = FirecrawlVisualSignatureAdapter(
        api_key="fixture-key",
        web_collector=FakeFailingWebCollector(),
    )

    acquisition = adapter.acquire(VisualSignatureInput("Example Brand", "https://example.com"))

    assert acquisition.adapter == "firecrawl"
    assert acquisition.errors == ["firecrawl fixture failure"]


def test_failed_acquisition_payload_is_not_interpretable():
    result = extract_visual_signature(
        brand_name="Example Brand",
        website_url="https://example.com",
        adapter=FailureAdapter(),
    )

    assert result["interpretation_status"] == "not_interpretable"
    assert result["acquisition"]["errors"] == ["fixture acquisition failure"]


def test_extract_visual_signature_rejects_invalid_url():
    with pytest.raises(ValueError, match="website_url"):
        extract_visual_signature(
            brand_name="Example Brand",
            website_url="not-a-url",
            web_data=_web_data(),
        )


def test_visual_signature_module_docstring_states_non_scoring_boundary():
    import src.visual_signature as visual_signature

    assert "not yet a Brand3 scoring dimension" in (visual_signature.__doc__ or "")
    assert "Firecrawl is treated only as an acquisition layer" in (visual_signature.__doc__ or "")
