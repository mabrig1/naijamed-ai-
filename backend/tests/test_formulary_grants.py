from __future__ import annotations

import unittest

from app.formulary_grants import disclosure_watermark, funder_profile_assessment, readiness_assessment, safe_funder_snapshot


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


    def test_funder_profile_is_completeness_not_prediction(self):
        project = {
            "_id": "FGP-FUNDER",
            "title": "International Research Programme",
            "country": "Nigeria",
            "problem_statement": "Problem " * 80,
            "objectives": ["One", "Two", "Three"],
            "budget_amount": 1000000000,
        }
        profile = {
            "funder_lens": "cross_funder",
            "innovation_case": "Innovation " * 40,
            "global_relevance": "Global relevance " * 30,
            "rigor_feasibility": "Rigor and feasibility " * 30,
            "impact_pathway": "Impact pathway " * 30,
            "institutional_capacity": "Institutional capacity " * 30,
            "ethics_governance": "Ethics and governance " * 30,
            "data_open_science": "Data and open science " * 30,
            "equity_capacity_building": "Equity and capacity " * 30,
            "sustainability_scale": "Sustainability and scale " * 30,
            "policy_translation": "Policy translation " * 30,
            "monitoring_evaluation": "Monitoring and evaluation " * 30,
            "risk_management": "Risk management " * 30,
            "cofunding_leverage": "Leverage " * 30,
            "impact_metrics": ["Metric"],
            "capacity_outputs": ["Capacity"],
            "data_management_commitments": ["DMP"],
        }
        result = funder_profile_assessment(
            project,
            profile,
            partners=[
                {"organization": "UNN", "country": "Nigeria", "status": "committed"},
                {"organization": "Partner EU", "country": "Germany", "status": "interested"},
                {"organization": "Partner Africa", "country": "Ghana", "status": "prospect"},
            ],
            work_packages=[
                {"title": "WP1", "objective": "A", "outputs": ["O"]},
                {"title": "WP2", "objective": "B", "outputs": ["O"]},
                {"title": "WP3", "objective": "C", "outputs": ["O"]},
            ],
            milestones=[
                {"title": "M1", "due_on": "2026-10-01"},
                {"title": "M2", "due_on": "2026-11-01"},
                {"title": "M3", "due_on": None},
                {"title": "M4", "due_on": None},
            ],
        )
        self.assertGreaterEqual(result["score"], 80)
        self.assertIn("not a funding probability", result["notice"].lower())

    def test_safe_funder_snapshot_does_not_include_private_ip_or_contacts(self):
        snapshot = safe_funder_snapshot(
            {
                "_id": "FGP-PRIVATE",
                "title": "Project",
                "originator_name": "Originator",
                "country": "Nigeria",
                "budget_amount": 1000,
                "budget_currency": "NGN",
                "objectives": ["One", "Two", "Three"],
                "problem_statement": "Problem " * 80,
                "secret_internal_note": "DO NOT SHARE",
            },
            {"innovation_case": "Innovation " * 30},
            partners=[{
                "organization": "Partner",
                "country": "Germany",
                "partner_type": "university",
                "status": "interested",
                "proposed_role": "Genomics",
                "contact_email": "private@example.org",
                "lead_contact": "Private Person",
            }],
            work_packages=[],
            milestones=[],
        )
        rendered = str(snapshot)
        self.assertNotIn("secret_internal_note", rendered)
        self.assertNotIn("DO NOT SHARE", rendered)
        self.assertNotIn("private@example.org", rendered)
        self.assertNotIn("Private Person", rendered)
        self.assertIn("privacy_notice", snapshot)


if __name__ == "__main__":
    unittest.main()
