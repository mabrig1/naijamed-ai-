from __future__ import annotations

import unittest

from app.formulary_journal import appraisal_template, evidence_snapshot, fact_check_claim


class FormularyJournalTests(unittest.TestCase):
    def test_appraisal_templates_are_structured(self):
        general = appraisal_template("general")
        pk = appraisal_template("pk")
        self.assertGreaterEqual(len(general), 8)
        self.assertGreaterEqual(len(pk), 6)
        self.assertTrue(all("id" in row and "prompt" in row for row in general))

    def test_evidence_snapshot_excludes_private_source_excerpt(self):
        rows = evidence_snapshot(
            [
                {
                    "_id": "FPE-TEST",
                    "title": "PK Study",
                    "doi": "10.1000/test",
                    "source_excerpt": "PRIVATE FULL-TEXT EXCERPT",
                    "extraction": {
                        "study_design": "parallel",
                        "sample_size": 24,
                        "key_findings": ["A finding"],
                        "evidence_spans": [{"field": "sample_size", "snippet": "n=24"}],
                    },
                }
            ]
        )
        self.assertEqual(rows[0]["id"], "FPE-TEST")
        self.assertEqual(rows[0]["sample_size"], 24)
        self.assertNotIn("source_excerpt", rows[0])
        self.assertNotIn("PRIVATE FULL-TEXT EXCERPT", str(rows[0]))

    def test_fact_check_without_model_is_conservative(self):
        result = fact_check_claim(
            "The intervention reduced exposure.",
            [
                {
                    "_id": "FPE-TEST",
                    "title": "PK Study",
                    "extraction": {"key_findings": ["Exposure was measured."]},
                }
            ],
        )
        self.assertIn(result["verdict"], {"unclear", "supported", "contradicted", "mixed"})
        self.assertTrue(all(value.startswith("PAPER:") for value in result["citations"]))


if __name__ == "__main__":
    unittest.main()
