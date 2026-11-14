import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from scripts.check_live_catalog import check

URL = "https://nigerflora.mabrigkorie.org/api/research-commerce"
class FakeResponse:
    status = 200
    url = URL
    def __init__(self, kind, body):
        self.headers = {"Content-Type": kind}
        self.body = body
    def __enter__(self):
        return self
    def __exit__(self, *_):
        pass
    def read(self, length):
        return self.body[:length]

class CheckLiveCatalogTests(unittest.TestCase):
    @patch("scripts.check_live_catalog.urlopen")
    def test_valid_json(self, fetch):
        fetch.return_value = FakeResponse("application/json", json.dumps({"services": [{"id": "one", "tiers": [{"id": "small"}]}]}).encode())
        self.assertTrue(check(URL)[0])

    @patch("scripts.check_live_catalog.urlopen")
    def test_spa_html_fails(self, fetch):
        fetch.return_value = FakeResponse("text/html", b"<html>wrong route</html>")
        self.assertFalse(check(URL)[0])

    @patch("scripts.check_live_catalog.urlopen")
    def test_reference_mode_cannot_pass_live_api_readiness(self, fetch):
        fetch.return_value = FakeResponse("application/json", json.dumps({
            "services": [{"id": "one", "tiers": [{"id": "basic"}]}],
            "catalog_mode": "reference",
            "checkout_available": False,
        }).encode())
        ok, message = check(URL)
        self.assertFalse(ok)
        self.assertIn("Read-only reference catalog", message)

    @patch("scripts.check_live_catalog.urlopen")
    def test_bad_json_fails(self, fetch):
        fetch.return_value = FakeResponse("application/json", b'{"status":"ok"}')
        self.assertFalse(check(URL)[0])

    @patch("scripts.check_live_catalog.urlopen")
    def test_http_404_fails(self, fetch):
        fetch.side_effect = HTTPError(URL, 404, "Not Found", {}, None)
        self.assertFalse(check(URL)[0])

    @patch("scripts.check_live_catalog.urlopen")
    def test_protected_preview_is_not_called_app_failure(self, fetch):
        fetch.side_effect = HTTPError(
            URL, 401, "Unauthorized",
            {"Content-Type": "text/html"},
            io.BytesIO(b"<html><title>Authentication Required</title>Vercel</html>"),
        )
        ok, message = check(URL)
        self.assertFalse(ok)
        self.assertIn("deployment protection", message.lower())
        self.assertIn("unverified", message.lower())

    @patch("scripts.check_live_catalog.urlopen")
    def test_unclassified_unauthorized_is_not_assumed_deployment_protection(self, fetch):
        fetch.side_effect = HTTPError(
            URL, 401, "Unauthorized",
            {"Content-Type": "application/json"},
            io.BytesIO(b'{"detail": "Authentication required for this API"}'),
        )
        ok, message = check(URL)
        self.assertFalse(ok)
        self.assertNotIn("appears to block", message)
        self.assertIn("unverified", message.lower())

    def test_http_url_rejected(self):
        self.assertFalse(check("http://example.com/api/research-commerce")[0])
