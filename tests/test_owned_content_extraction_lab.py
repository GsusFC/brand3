import unittest

from src.quality.owned_content_extraction import (
    evaluate_owned_content_extraction,
    extract_section_aware_html,
)


NAV_HEAVY_HTML = """
<html>
  <head>
    <title>Northstar Ops</title>
    <meta name="description" content="Revenue operations automation for complex enterprise teams." />
  </head>
  <body>
    <header>
      <nav>
        <ul>
          <li>Login</li>
          <li>Careers</li>
          <li>Contact us</li>
        </ul>
      </nav>
    </header>
    <main>
      <h1>Agentic workflows for revenue operations</h1>
      <p>Northstar Ops connects CRM, billing, and customer success systems into auditable agentic workflows.</p>
      <p>Enterprise teams use the platform to reduce manual handoffs and protect SOC 2 controls.</p>
      <h2>Customers</h2>
      <p>Customer operations leaders use Northstar to coordinate renewal, pricing, and expansion motions.</p>
    </main>
    <footer>
      <ul>
        <li>Privacy policy</li>
        <li>Terms of service</li>
      </ul>
    </footer>
  </body>
</html>
"""

COOKIE_BANNER_HTML = """
<html>
  <head>
    <title>Traceframe</title>
    <meta name="description" content="Developer observability for incident response." />
  </head>
  <body>
    <div class="cookie-banner">
      <p>Accept cookies</p>
      <p>Reject all</p>
      <p>Manage preferences</p>
    </div>
    <main>
      <h1>Developer observability for incident response</h1>
      <p>Traceframe gives enterprise engineering teams a platform for debugging production workflows.</p>
      <p>Security, automation, and workflow context are preserved in every incident timeline.</p>
    </main>
  </body>
</html>
"""


class OwnedContentExtractionLabTests(unittest.TestCase):
    def test_section_aware_html_removes_page_chrome_but_keeps_strategy_terms(self):
        text = extract_section_aware_html(NAV_HEAVY_HTML)

        self.assertIn("Agentic workflows for revenue operations", text)
        self.assertIn("SOC 2 controls", text)
        self.assertNotIn("Login", text)
        self.assertNotIn("Privacy policy", text)

    def test_bakeoff_ranks_section_aware_above_current_html_on_nav_heavy_case(self):
        result = evaluate_owned_content_extraction(
            case_id="nav_heavy_saas_homepage",
            html=NAV_HEAVY_HTML,
            expected_terms=[
                "agentic workflows",
                "revenue operations",
                "soc 2",
                "pricing",
            ],
            rejected_terms=[
                "login",
                "careers",
                "privacy policy",
                "terms of service",
            ],
        )

        self.assertEqual(result.winner, "section_aware_html")
        by_method = {item.method: item for item in result.results}
        self.assertIn("brand3_current_html_fallback", by_method)
        self.assertIn("visible_body_text", by_method)
        self.assertGreater(
            by_method["section_aware_html"].score,
            by_method["brand3_current_html_fallback"].score,
        )
        self.assertEqual(by_method["section_aware_html"].rejected_hits, [])
        self.assertIn("login", by_method["visible_body_text"].rejected_hits)

    def test_bakeoff_output_is_serializable(self):
        result = evaluate_owned_content_extraction(
            case_id="nav_heavy_saas_homepage",
            html=NAV_HEAVY_HTML,
            expected_terms=["agentic workflows"],
            rejected_terms=["login"],
        )

        payload = result.as_dict()

        self.assertEqual(payload["case_id"], "nav_heavy_saas_homepage")
        self.assertIsInstance(payload["results"], list)
        self.assertIn("winner", payload)

    def test_section_aware_html_removes_cookie_banner_container(self):
        text = extract_section_aware_html(COOKIE_BANNER_HTML)

        self.assertIn("Developer observability for incident response", text)
        self.assertNotIn("Accept cookies", text)
        self.assertNotIn("Manage preferences", text)


if __name__ == "__main__":
    unittest.main()
