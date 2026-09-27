from __future__ import annotations

import unittest

from app.formulary_grants import disclosure_watermark, readiness_assessment


class FormularyGrantStudioTests(unittest.TestCase):
    def test_early_project_exposes_protection_and_consortium_gaps(self):
        project = {
            "_id": "FGP-TEST",
            "title": "Flagship Project",
            "originator_name": "Originator",
            "country": "Nigeria",
            "budget_amount": 1_000_000_000,
            "summary": "Short",
            "problem_statement": "",
            "objectives": [],
        }
        result = readiness_assessment(
            project,
            partners=[],
            work_packages=[],
            milestones=[],
            ip_assets=[],
            disclosures=[],
        )
        self.assertLess(result["score"], 50)
        keys = {row["key"]: row["status"] for row in result["checks"]}
        self.assertEqual(keys["background_ip"], "gap")
        self.assertEqual(keys["partners"], "gap")
        self.assertEqual(keys["workpackages"], "gap")

    def test_mature_project_reconciles_budget_and_recognises_origin_trail(self):
        project = {
            "_id": "FGP-TEST",
            "title": "Flagship Project",
            "originator_name": "Originator",
            "country": "Nigeria",
            "budget_amount": 1_000_000_000,
            "summary": "A " * 120,
            "problem_statement": "Problem " * 80,
            "objectives": ["One", "Two", "Three"],
            "funder_name": "International Funder",
            "call_url": "https://example.org/call",
            "deadline": "2027-01-01",
        }
        partners = [
            {"organization": "UNN", "country": "Nigeria", "status": "committed"},
            {"organization": "Partner Europe", "country": "Germany", "status": "interested"},
            {"organization": "Partner Africa", "country": "Ghana", "status": "prospect"},
        ]
        work_packages = [
            {"title": "WP1", "budget_amount": 300_000_000},
            {"title": "WP2", "budget_amount": 300_000_000},
            {"title": "WP3", "budget_amount": 400_000_000},
        ]
        milestones = [
            {"title": "M1", "due_on": "2026-10-01"},
            {"title": "M2", "due_on": "2026-11-01"},
            {"title": "M3", "due_on": None},
            {"title": "M4", "due_on": None},
        ]
        ip_assets = [{"category": "proposal", "title": "Master concept"}]
        disclosures = [{"recipient_name": "IP office", "confidentiality_basis": "NDA"}]
        result = readiness_assessment(
            project,
            partners=partners,
            work_packages=work_packages,
            milestones=milestones,
            ip_assets=ip_assets,
            disclosures=disclosures,
        )
        self.assertGreaterEqual(result["score"], 85)
        self.assertEqual(result["budget"]["unallocated"], 0)
        self.assertFalse(any("without a recorded confidentiality" in risk for risk in result["risks"]))

    def test_disclosure_without_confidentiality_basis_is_flagged(self):
        result = readiness_assessment(
            {"_id": "FGP-X", "title": "X", "originator_name": "O"},
            partners=[],
            work_packages=[],
            milestones=[],
            ip_assets=[],
            disclosures=[{"recipient_name": "Someone", "confidentiality_basis": ""}],
        )
        self.assertTrue(any("confidentiality" in risk.lower() for risk in result["risks"]))

    def test_watermark_names_originator_and_project(self):
        text = disclosure_watermark(
            {"_id": "FGP-123", "title": "NEXUS-AMR Africa", "originator_name": "A. Originator"},
            "v2.0",
        )
        self.assertIn("NEXUS-AMR Africa", text)
        self.assertIn("A. Originator", text)
        self.assertIn("FGP-123", text)
        self.assertIn("v2.0", text)


if __name__ == "__main__":
    unittest.main()
