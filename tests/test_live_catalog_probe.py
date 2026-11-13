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
    def test_bad_json_fails(self, fetch):
        fetch.return_value = FakeResponse("application/json", b'{"status":"ok"}')
        self.assertFalse(check(URL)[0])

    @patch("scripts.check_live_catalog.urlopen")
    def test_http_404_fails(self, fetch):
        fetch.side_effect = HTTPError(URL, 404, "Not Found", {}, None)
        self.assertFalse(check(URL)[0])

    def test_http_url_rejected(self):
        self.assertFalse(check("http://example.com/api/research-commerce")[0])
