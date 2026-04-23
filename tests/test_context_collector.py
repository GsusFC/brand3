import unittest
from unittest.mock import patch

from src.collectors.context_collector import ContextCollector


class _FakeResponse:
    def __init__(self, body: str = "", status: int = 200):
        self.body = body.encode("utf-8")
        self.status = status
        self.headers = self

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, *_args):
        return self.body

    def get_content_charset(self):
        return "utf-8"


class ContextCollectorTests(unittest.TestCase):
    def test_detects_root_files_schema_key_pages_and_confidence(self):
        homepage = """
        <html><head>
          <meta name="description" content="Example builds developer infrastructure for teams.">
          <script type="application/ld+json">
          {"@context":"https://schema.org","@graph":[
            {"@type":"Organization","sameAs":["https://x.com/example"]},
            {"@type":"WebSite","potentialAction":{"@type":"SearchAction"}},
            {"@type":"FAQPage"}
          ]}
          </script>
        </head><body>
          <h1>Example infrastructure</h1>
          <p>Example builds reliable infrastructure for developer teams with docs, product workflows, and support.</p>
          <a href="/about">About</a><a href="/blog">Blog</a><a href="/pricing">Pricing</a>
        </body></html>
        """

        def fake_urlopen(req, timeout=0):
            url = req.full_url
            method = getattr(req, "method", None) or "GET"
            if method == "HEAD":
                return _FakeResponse("", 200 if url.endswith(("/about", "/blog", "/pricing")) else 404)
            if url.endswith("/robots.txt"):
                return _FakeResponse("User-agent: GPTBot\nAllow: /")
            if url.endswith("/sitemap.xml"):
                return _FakeResponse("<urlset><url><loc>https://example.com/about</loc></url></urlset>")
            if url.endswith("/llms.txt"):
                return _FakeResponse("# Example\n\n> Developer infrastructure for reliable systems.")
            if url.endswith("/llms-full.txt"):
                return _FakeResponse("# Example\n" + "full context " * 20)
            if url.endswith("/.well-known/ai-plugin.json"):
                return _FakeResponse('{"schema_version":"v1"}')
            return _FakeResponse(homepage)

        with patch("src.collectors.context_collector.urlopen", side_effect=fake_urlopen):
            data = ContextCollector().scan("https://example.com")

        self.assertTrue(data.robots_found)
        self.assertTrue(data.sitemap_found)
        self.assertTrue(data.llms_txt_found)
        self.assertTrue(data.ai_plugin_found)
        self.assertIn("Organization", data.schema_types)
        self.assertTrue(data.key_pages["about"])
        self.assertGreater(data.coverage, 0.7)
        self.assertGreater(data.confidence, 0.7)

    def test_missing_homepage_returns_insufficient_context(self):
        def fake_urlopen(_req, timeout=0):
            raise OSError("network down")

        with patch("src.collectors.context_collector.urlopen", side_effect=fake_urlopen):
            data = ContextCollector().scan("https://example.com")

        self.assertEqual(data.error, "homepage_unavailable")
        self.assertEqual(data.coverage, 0.0)
        self.assertIn("low_coverage", data.confidence_reason)


if __name__ == "__main__":
    unittest.main()
