"""
Visual brand consistency analyzer.

Takes screenshots of brand websites using Firecrawl, then analyzes them
with AI vision for:
- Color palette consistency
- Logo presence and placement
- Typography style signals
- Layout and visual identity coherence

Returns visual consistency scores with confidence levels.
"""

import json
import os
import subprocess
import tempfile
import urllib.request
import urllib.error
import base64
from dataclasses import dataclass, field
from typing import Optional

from src.config import BRAND3_LLM_API_KEY, LLM_BASE_URL, VISION_MODEL


@dataclass
class VisualAnalysisResult:
    """Result of visual brand analysis from screenshot."""
    screenshot_url: str = ""
    screenshot_path: str = ""
    color_palette_score: float = 0.0
    logo_detected: bool = False
    logo_score: float = 0.0
    typography_score: float = 0.0
    layout_consistency_score: float = 0.0
    overall_score: float = 0.0
    confidence: float = 0.0
    details: dict = field(default_factory=dict)
    error: str = ""


class VisualAnalyzer:
    """Analyzes brand website screenshots for visual consistency."""

    def __init__(self, api_key: str = None, vision_api_key: str = None,
                 vision_base_url: str = None, vision_model: str = None):
        self.firecrawl_api_key = api_key or os.environ.get("FIRECRAWL_API_KEY", "")
        self.vision_api_key = vision_api_key or BRAND3_LLM_API_KEY
        self.vision_base_url = vision_base_url or LLM_BASE_URL
        self.vision_model = vision_model or VISION_MODEL

    def take_screenshot(self, url: str) -> dict:
        """
        Take a screenshot of a URL using Firecrawl CLI.
        Returns dict with 'screenshot_url' and optionally 'metadata'.
        """
        cmd = [
            "firecrawl", "scrape", url,
            "--format", "screenshot",
            "--json",
            "--max-age", "0",  # Force fresh screenshot to get non-expired URL
        ]

        env = os.environ.copy()
        if self.firecrawl_api_key:
            env["FIRECRAWL_API_KEY"] = self.firecrawl_api_key

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60, env=env
            )

            if result.returncode != 0:
                return {"error": f"Firecrawl failed: {result.stderr}"}

            # Parse JSON output
            output = result.stdout.strip()
            # Find the JSON part (skip timing/scrape ID lines)
            json_start = output.find("{")
            if json_start == -1:
                return {"error": "No JSON found in firecrawl output"}

            data = json.loads(output[json_start:])
            screenshot_url = data.get("screenshot", "")

            if not screenshot_url:
                return {"error": "No screenshot URL in response"}

            return {
                "screenshot_url": screenshot_url,
                "metadata": data.get("metadata", {}),
            }

        except subprocess.TimeoutExpired:
            return {"error": "Firecrawl screenshot timed out"}
        except json.JSONDecodeError as e:
            return {"error": f"Failed to parse firecrawl output: {e}"}
        except Exception as e:
            return {"error": f"Screenshot failed: {e}"}

    def _download_image(self, url: str) -> Optional[str]:
        """Download image to a temp file, return the path."""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()

            fd, path = tempfile.mkstemp(suffix=".png")
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            return path
        except Exception as e:
            print(f"  Failed to download screenshot: {e}")
            return None

    def _encode_image_base64(self, image_path: str) -> str:
        """Read and base64-encode an image file."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _call_vision_api(self, image_base64: str, prompt: str) -> dict:
        """
        Call a vision-capable LLM to analyze the screenshot.
        Uses OpenAI-compatible vision API format.
        """
        if not self.vision_api_key:
            return {}

        payload = json.dumps({
            "model": self.vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 1200,
            "temperature": 0.1,
        }).encode()

        req = urllib.request.Request(
            f"{self.vision_base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.vision_api_key}",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
                content = data["choices"][0]["message"].get("content", "")
                return self._extract_json(content)
        except Exception as e:
            print(f"  Vision API call failed: {e}")
            return {}

    def _extract_json(self, text: str) -> dict:
        """Extract JSON from potentially markdown-wrapped response."""
        text = text.strip()
        # Handle markdown code blocks
        if "```" in text:
            # Find first code block
            start = text.find("```")
            if start != -1:
                after_marker = text.find("\n", start)
                if after_marker != -1:
                    end = text.find("```", after_marker + 1)
                    if end != -1:
                        text = text[after_marker + 1:end].strip()
        # Try to find JSON object
        if not text.startswith("{"):
            brace_start = text.find("{")
            if brace_start != -1:
                brace_end = text.rfind("}")
                if brace_end != -1:
                    text = text[brace_start:brace_end + 1]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

    def _analyze_with_heuristics(self, metadata: dict) -> VisualAnalysisResult:
        """
        Fallback heuristic analysis when vision API is unavailable.
        Uses metadata from the page (og:image, favicon, etc.) as signals.
        """
        result = VisualAnalysisResult()
        result.confidence = 0.35  # Low confidence for heuristics only

        # Has favicon = minor brand identity signal
        has_favicon = bool(metadata.get("favicon"))
        # Has og:image = social sharing image
        has_og_image = bool(metadata.get("og:image") or metadata.get("ogImage"))
        # Has a clear title
        has_title = bool(metadata.get("title"))
        # Has description
        has_description = bool(metadata.get("description") or metadata.get("og:description"))

        score = 40.0
        if has_favicon:
            score += 10
        if has_og_image:
            score += 15
        if has_title:
            score += 10
        if has_description:
            score += 5

        result.overall_score = min(score, 100.0)
        result.color_palette_score = 50.0
        result.logo_score = 60.0 if has_favicon else 40.0
        result.typography_score = 50.0
        result.layout_consistency_score = 50.0
        result.details = {
            "method": "heuristic_fallback",
            "has_favicon": has_favicon,
            "has_og_image": has_og_image,
        }

        return result

    def analyze_screenshot(self, screenshot_url: str,
                           brand_name: str = "",
                           page_metadata: dict = None) -> VisualAnalysisResult:
        """
        Analyze a screenshot for visual brand consistency.

        Args:
            screenshot_url: URL of the screenshot image
            brand_name: Name of the brand being analyzed
            page_metadata: Optional metadata from the page scrape
        """
        result = VisualAnalysisResult(screenshot_url=screenshot_url)

        # Download the screenshot for local analysis
        image_path = self._download_image(screenshot_url)
        if image_path:
            result.screenshot_path = image_path

        # Try vision analysis
        if image_path and self.vision_api_key:
            image_b64 = self._encode_image_base64(image_path)

            prompt = f"""Analyze this website screenshot for brand quality and authenticity. The brand is "{brand_name}".

Evaluate these aspects and return ONLY valid JSON:

**Visual Consistency:**
1. color_palette_score (0-100): How consistent and intentional is the color palette?
2. logo_detected (true/false): Is there a visible logo?
3. logo_score (0-100): How professional is the logo placement?
4. typography_score (0-100): Typography consistency and hierarchy?
5. layout_consistency_score (0-100): Layout cleanliness?

**Design Authenticity (NEW — judge if this feels custom or template):**
6. design_authenticity (0-100): Does this look custom-designed by a real designer, or does it feel like a template/AI-generated layout?
   - 100 = clearly custom, unique design language, creative layout
   - 70 = professional, some custom elements
   - 50 = clean but generic, could be any SaaS
   - 30 = obviously a template, Tailwind/UI kit, cards-in-a-grid
   - 10 = AI-generated look, cookie-cutter, no visual identity
7. cta_count: How many "Book a Call" / "Get Started" / "Contact" buttons are visible?
8. section_repetition: Does the page repeat the same card/grid layout section after section?

Return JSON:
{{
    "color_palette_score": <0-100>,
    "logo_detected": <true/false>,
    "logo_score": <0-100>,
    "typography_score": <0-100>,
    "layout_consistency_score": <0-100>,
    "overall_score": <0-100>,
    "design_authenticity": <0-100>,
    "cta_count": <number>,
    "section_repetition": <true/false>,
    "details": {{
        "dominant_colors": ["list", "of", "main", "colors"],
        "style": "modern|classic|minimal|playful|corporate|dark-mode-agency",
        "logo_position": "top-left|top-center|top-right|none",
        "design_verdict": "custom|professional-generic|template|ai-generated",
        "authenticity_insights": ["any observations about design authenticity"],
        "observations": "brief description"
    }}
}}"""

            vision_result = self._call_vision_api(image_b64, prompt)

            if vision_result and "overall_score" in vision_result:
                result.color_palette_score = float(vision_result.get("color_palette_score", 50))
                result.logo_detected = bool(vision_result.get("logo_detected", False))
                result.logo_score = float(vision_result.get("logo_score", 50))
                result.typography_score = float(vision_result.get("typography_score", 50))
                result.layout_consistency_score = float(vision_result.get("layout_consistency_score", 50))
                result.overall_score = float(vision_result.get("overall_score", 50))

                # Design authenticity fields (NEW)
                design_auth = float(vision_result.get("design_authenticity", 50))
                cta_count = int(vision_result.get("cta_count", 0))
                section_repetition = bool(vision_result.get("section_repetition", False))

                # Handle both nested details and flat response formats
                details = vision_result.get("details", {})
                if not details:
                    # Some models return fields at top level
                    details = {
                        "dominant_colors": vision_result.get("dominant_colors", []),
                        "style": vision_result.get("style", ""),
                        "logo_position": vision_result.get("logo_position", ""),
                        "design_verdict": vision_result.get("design_verdict", ""),
                        "authenticity_insights": vision_result.get("authenticity_insights", []),
                        "observations": vision_result.get("observations", ""),
                    }

                # Add authenticity data to details
                details["design_authenticity"] = design_auth
                details["cta_count"] = cta_count
                details["section_repetition"] = section_repetition
                details["method"] = "vision_analysis"
                result.details = details
                result.confidence = 0.8
            else:
                # Vision failed, fall back to heuristics
                fallback = self._analyze_with_heuristics(page_metadata or {})
                fallback.screenshot_url = screenshot_url
                fallback.screenshot_path = image_path or ""
                fallback.details["vision_failed"] = True
                return fallback

            # Clean up temp file
            try:
                os.unlink(image_path)
            except OSError:
                pass
        else:
            # No vision API or download failed
            return self._analyze_with_heuristics(page_metadata or {})

        return result

    def analyze_url(self, url: str, brand_name: str = "") -> VisualAnalysisResult:
        """
        Full pipeline: take screenshot of URL, then analyze it.
        """
        print(f"  [Visual] Taking screenshot of {url}...")
        screenshot_data = self.take_screenshot(url)

        if "error" in screenshot_data:
            result = VisualAnalysisResult(error=screenshot_data["error"])
            result.confidence = 0.1
            result.details = {"error": screenshot_data["error"]}
            return result

        screenshot_url = screenshot_data["screenshot_url"]
        metadata = screenshot_data.get("metadata", {})

        print(f"  [Visual] Analyzing screenshot for {brand_name or url}...")
        return self.analyze_screenshot(screenshot_url, brand_name, metadata)
