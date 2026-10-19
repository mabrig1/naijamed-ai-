"""Contract/security tests for the synthetic-only NcheSent receiver."""
import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from api.nchesent_bridge import NcheSentSummary, configured_upstream

FIXTURE = {
    "schemaVersion": "1.0",
    "source": "NcheSent",
    "dataset": "synthetic",
    "clinicalUse": False,
    "modelVersion": "0.1.0",
    "generatedAt": "2026-10-19T07:00:00.000Z",
    "totalAssessments": 4,
    "byState": {"Lagos": 4},
    "byRegimen": {"AL": 4},
    "byBand": {"LOW": 4},
    "notice": "Synthetic and unvalidated. No clinical decisions.",
}


class ResearchBridgeContractTests(unittest.TestCase):
    def test_valid_synthetic_summary(self):
        result = NcheSentSummary.model_validate(FIXTURE)
        self.assertFalse(result.clinicalUse)
        self.assertEqual(result.totalAssessments, 4)

    def test_real_data_rejected(self):
        with self.assertRaises(ValidationError):
            NcheSentSummary.model_validate({**FIXTURE, "dataset": "clinical"})

    def test_patient_data_rejected(self):
        with self.assertRaises(ValidationError):
            NcheSentSummary.model_validate({**FIXTURE, "patientId": "secret"})

    def test_mismatched_counts_rejected(self):
        with self.assertRaises(ValidationError):
            NcheSentSummary.model_validate({**FIXTURE, "byState": {"Lagos": 3}})

    def test_wrong_schema_rejected(self):
        with self.assertRaises(ValidationError):
            NcheSentSummary.model_validate({**FIXTURE, "schemaVersion": "2.0"})

    def test_unconfigured_rejected(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HTTPException) as err:
                configured_upstream()
            self.assertEqual(err.exception.status_code, 503)

    def test_untrusted_url_rejected(self):
        for host in ("http://nchesent.pages.dev", "https://127.0.0.1", "https://example.org",
                     "https://nchesent.pages.dev/steal", "https://nchesent.pages.dev@evil.com"):
            with self.subTest(host=host), patch.dict(os.environ, {"NCHESENT_BASE_URL": host}):
                with self.assertRaises(HTTPException):
                    configured_upstream()

    def test_verified_host_accepted(self):
        with patch.dict(os.environ, {"NCHESENT_BASE_URL": "https://nchesent.mabrigkorie.org"}):
            self.assertEqual(configured_upstream(), "https://nchesent.mabrigkorie.org")


if __name__ == "__main__":
    unittest.main()
