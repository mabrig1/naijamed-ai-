"""Deployment rewrites must expose the FastAPI owner and login endpoints.

This is a static config contract; no production credentials are required.
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class VercelEntryPointTests(unittest.TestCase):
    def test_main_fastapi_routes_are_explicit_and_before_spa_fallback(self):
        config = json.loads((ROOT / "vercel.json").read_text())
        rules = config["rewrites"]
        sources = {row["source"]: (idx, row["destination"]) for idx, row in enumerate(rules)}
        for source in (
            "/api/auth/:path*", "/api/owner/:path*",
            "/api/clinical/:path*", "/api/health",
        ):
            with self.subTest(path=source):
                self.assertIn(source, sources)
                i, destination = sources[source]
                self.assertEqual(destination, "/api/index")
                self.assertLess(i, len(rules)-1)
        spa = rules[-1]
        self.assertNotIn("/api/", spa["destination"])
        self.assertIn("api|assets", spa["source"])


if __name__ == "__main__":
    unittest.main()
