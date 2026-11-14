import json
import re
import unittest
from pathlib import Path

from scripts.export_public_catalog import generate, ROOT


class PublicCatalogRecoveryTests(unittest.TestCase):
    def test_generated_catalog_matches_backend(self):
        snapshot = ROOT / "frontend/src/generated/bioinformatics-catalog.json"
        self.assertEqual(snapshot.read_text(encoding="utf-8"), generate())
        catalog = json.loads(snapshot.read_text(encoding="utf-8"))
        self.assertFalse(catalog["checkout_available"])
        self.assertEqual(catalog["catalog_mode"], "reference")
        self.assertTrue(all(service["tiers"] for service in catalog["services"]))

    def test_vercel_spa_fallback_does_not_capture_api(self):
        for filename in ("vercel.json", "frontend/vercel.json"):
            config = json.loads((ROOT / filename).read_text(encoding="utf-8"))
            spa_rules = [item for item in config["rewrites"] if item["destination"] == "/index.html"]
            self.assertEqual(len(spa_rules), 1)
            rule = spa_rules[0]["source"]
            self.assertRegex("/bioinformatics-services", re.compile(rule))
            self.assertIsNone(re.compile(rule).match("/api/research-commerce"))
            self.assertIsNone(re.compile(rule).match("/api/research_commerce"))
            self.assertIsNone(re.compile(rule).match("/assets/example.js"))


if __name__ == "__main__":
    unittest.main()
