import unittest
from app.pharmaos import module_catalog, research_pipeline, grant_handoff

class PharmaOSTests(unittest.TestCase):
    def test_catalog_bundles_existing_research_engines(self):
        keys={row["key"] for row in module_catalog()}
        self.assertIn("literature", keys)
        self.assertIn("docking", keys)
        self.assertIn("admet", keys)
        self.assertIn("grants", keys)

    def test_pipeline_preserves_research_integrity_boundary(self):
        plan=research_pipeline("Natural-product AMR discovery","antimicrobial resistance")
        self.assertTrue(plan["integrity"]["computational_results_are_hypotheses"])
        self.assertTrue(plan["integrity"]["experimental_validation_required"])
        self.assertTrue(plan["integrity"]["provenance_required"])

    def test_grant_handoff_does_not_overclaim(self):
        handoff=grant_handoff({"title":"AMR pilot","evidence":[{"kind":"docking","status":"predicted"}]})
        self.assertEqual(handoff["preliminary_evidence_count"],1)
        self.assertIn("not experimental",handoff["claims_boundary"])

if __name__ == "__main__":
    unittest.main()
