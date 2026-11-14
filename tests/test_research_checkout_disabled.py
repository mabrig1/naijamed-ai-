"""The test-phase service pages and APIs cannot create orders or start payments."""
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from api import research_commerce, research_studio


class ResearchTestingGateTests(unittest.TestCase):
    def test_commerce_create_order_off_before_auth_or_mongodb(self):
        for path in ("/api/research-commerce", "/api/research_commerce"):
            with self.subTest(path=path), \
                 patch.object(research_commerce.settings, "RESEARCH_CHECKOUT_ENABLED", False), \
                 patch.object(research_commerce, "get_db", side_effect=AssertionError("DB must not be touched")):
                response = TestClient(research_commerce.app).post(path, json={
                    "action": "create_order", "service_id": "admet-screening",
                    "tier_id": "starter", "market": "local",
                })
                self.assertEqual(response.status_code, 503, response.text)
                self.assertIn("testing", response.json()["detail"])

    def test_studio_create_order_off_before_auth_or_mongodb(self):
        for path in ("/api/research-studio", "/api/research_studio"):
            with self.subTest(path=path), \
                 patch.object(research_studio.settings, "RESEARCH_CHECKOUT_ENABLED", False), \
                 patch.object(research_studio, "get_db", side_effect=AssertionError("DB must not be touched")):
                response = TestClient(research_studio.app).post(path, json={
                    "action": "create_order", "service_id": "admet-screening",
                })
                self.assertEqual(response.status_code, 503, response.text)
                self.assertIn("testing", response.json()["detail"])

    def test_public_catalog_and_nonmutating_quote_remain_available(self):
        with patch.object(research_commerce.settings, "RESEARCH_CHECKOUT_ENABLED", False):
            client = TestClient(research_commerce.app)
            self.assertEqual(len(client.get("/api/research-commerce").json()["services"]), 7)
            quote = client.post("/api/research-commerce", json={
                "action": "quote", "service_id": "admet-screening",
                "tier_id": "starter", "market": "local",
            })
            self.assertEqual(quote.status_code, 200, quote.text)


if __name__ == "__main__":
    unittest.main()
