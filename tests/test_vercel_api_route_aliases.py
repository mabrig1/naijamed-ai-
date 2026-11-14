"""Regression tests for Vercel rewrite paths.

The deployment routes /api/research-commerce into the underscore-named
Python function, but ASGI may receive the original, hyphenated URL path.
Keep both variants valid. Do not hit MongoDB, payment providers or auth.
"""
import unittest
from fastapi.testclient import TestClient

from api.research_commerce import app as commerce_app
from api.research_commerce_webhook import app as webhook_app
from api.research_studio import app as studio_app
from api.nchesent_bridge import app as bridge_app
from api.nchesent_analysis import app as analysis_app


class RouteAliasTests(unittest.TestCase):
    def test_public_commerce_catalog_on_both_url_spellings(self):
        with TestClient(commerce_app) as client:
            for path in ("/api/research-commerce", "/api/research_commerce"):
                with self.subTest(path=path):
                    response = client.get(path)
                    self.assertEqual(response.status_code, 200)
                    self.assertIn("application/json", response.headers["content-type"])
                    body = response.json()
                    self.assertEqual(len(body["services"]), 7)
                    self.assertTrue(all(item.get("tiers") for item in body["services"]))
                    self.assertIsInstance(body["addons"], list)

    def test_quote_does_not_depend_on_mongodb_or_database_indexes(self):
        from unittest.mock import patch
        payload = {
            "action": "quote",
            "service_id": "scope-consultation",
            "tier_id": "standard",
            "market": "local",
            "addon_ids": [],
        }
        with patch("api.research_commerce.get_db", side_effect=AssertionError("Do not touch MongoDB for quotes")):
            with TestClient(commerce_app) as client:
                for path in ("/api/research-commerce", "/api/research_commerce"):
                    with self.subTest(path=path):
                        response = client.post(path, json=payload)
                        self.assertEqual(response.status_code, 200, response.text)
                        quote = response.json()
                        self.assertEqual(quote["service_id"], "scope-consultation")
                        self.assertEqual(quote["currency"], "NGN")
                        self.assertEqual(quote["amount_major"], 25000)

    def test_public_quote_validates_invalid_service_without_db(self):
        from unittest.mock import patch
        with patch("api.research_commerce.get_db", side_effect=AssertionError("No database connection expected")):
            response = TestClient(commerce_app).post("/api/research-commerce", json={
                "action": "quote", "service_id": "not-real", "tier_id": "standard",
            })
        self.assertEqual(response.status_code, 404)

    def test_honeypot_request_has_no_database_side_effect(self):
        from unittest.mock import patch
        with patch("api.research_commerce.get_db", side_effect=AssertionError("No insert expected")):
            response = TestClient(commerce_app).post("/api/research-commerce", json={
                "action": "capture_lead", "website": "spam.invalid",
            })
        self.assertEqual(response.status_code, 200)

    def test_studio_catalog_on_both_url_spellings(self):
        with TestClient(studio_app) as client:
            for path in ("/api/research-studio", "/api/research_studio"):
                with self.subTest(path=path):
                    response = client.get(path)
                    self.assertEqual(response.status_code, 200)
                    self.assertIn("application/json", response.headers["content-type"])

    def test_post_routes_are_registered_but_never_call_external_services(self):
        cases = [
            (commerce_app, "/api/research-commerce", "POST"),
            (commerce_app, "/api/research_commerce", "POST"),
            (studio_app, "/api/research-studio", "POST"),
            (studio_app, "/api/research_studio", "POST"),
            (commerce_app, "/api/research-commerce/paystack-webhook", "POST"),
            (commerce_app, "/api/research_commerce/paystack_webhook", "POST"),
            (webhook_app, "/api/research-commerce/paystack-webhook", "POST"),
            (webhook_app, "/api/research_commerce_webhook", "POST"),
            (bridge_app, "/api/nchesent-bridge", "GET"),
            (bridge_app, "/api/nchesent_bridge", "GET"),
            (analysis_app, "/api/nchesent-analysis", "POST"),
            (analysis_app, "/api/nchesent_analysis", "POST"),
        ]
        for app, path, method in cases:
            with self.subTest(path=path, method=method):
                routes = [r for r in app.routes if getattr(r, "path", None) == path]
                self.assertTrue(any(method in r.methods for r in routes), f"Missing {method} {path}")

    def test_unknown_public_endpoint_still_returns_404(self):
        response = TestClient(commerce_app).get("/api/unknown-test-endpoint")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
