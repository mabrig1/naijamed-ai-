"""Public, read-only discovery without MongoDB or authentication."""
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from api.discovery import app


class PublicLookupTests(unittest.TestCase):
    def test_public_compound_lookup_uses_no_database(self):
        with patch("api.discovery.get_db", side_effect=AssertionError("DB used in public lookup")), \
             patch("api.discovery.pubchem_lookup", return_value={
                 "kind": "compound", "external_id": "2244", "name": "Aspirin",
                 "source": "PubChem", "source_url": "https://pubchem.ncbi.nlm.nih.gov/compound/2244",
             }) as lookup:
            response = TestClient(app).post("/api/discovery", json={
                "action": "lookup_compound", "query": "aspirin",
            })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["result"]["external_id"], "2244")
        lookup.assert_called_once_with("aspirin")

    def test_public_protein_lookup_uses_no_database(self):
        with patch("api.discovery.get_db", side_effect=AssertionError("DB used in public lookup")), \
             patch("api.discovery.rcsb_lookup", return_value={
                 "kind": "protein", "external_id": "1CRN", "name": "Crambin",
                 "source": "RCSB Protein Data Bank",
                 "source_url": "https://www.rcsb.org/structure/1CRN",
             }) as lookup:
            response = TestClient(app).post("/api/discovery", json={
                "action": "lookup_protein", "query": " 1CRN ",
            })
        self.assertEqual(response.status_code, 200, response.text)
        lookup.assert_called_once_with("1CRN")

    def test_private_actions_still_require_authentication(self):
        with patch("api.discovery.get_db", side_effect=AssertionError("No db for unauthenticated calls")):
            for action in ("library", "save_asset", "create_screening_job", "my_networks"):
                with self.subTest(action=action):
                    response = TestClient(app).post("/api/discovery", json={"action": action})
                    self.assertEqual(response.status_code, 401)

    def test_lookup_rejects_oversized_and_empty_input(self):
        with patch("api.discovery.get_db", side_effect=AssertionError("DB used")), \
             patch("api.discovery.pubchem_lookup", side_effect=AssertionError("Provider should not be reached")):
            for value in (" ", "a"*81, "name\nheader"):
                with self.subTest(value=value):
                    response = TestClient(app).post("/api/discovery", json={
                        "action": "lookup_compound", "query": value,
                    })
                    self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
