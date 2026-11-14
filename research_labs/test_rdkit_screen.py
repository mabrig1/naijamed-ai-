import csv
import tempfile
import unittest
from pathlib import Path

from research_labs.rdkit_screen import FIELDS, analyze_smiles, screen_csv


class ScreeningTests(unittest.TestCase):
    def test_aspirin_known_formula_and_approximate_weight(self):
        aspirin = analyze_smiles("CC(=O)Oc1ccccc1C(=O)O", "aspirin")
        self.assertEqual(aspirin["status"], "computed")
        self.assertEqual(aspirin["molecular_formula"], "C9H8O4")
        self.assertAlmostEqual(aspirin["molecular_weight_g_mol"], 180.159, delta=0.1)
        self.assertEqual(aspirin["lipinski_rule_of_five"], "pass")
        self.assertIn("qed", aspirin)
        self.assertEqual(tuple(aspirin.keys()), FIELDS)

    def test_invalid_smiles_never_gets_fabricated_values(self):
        result = analyze_smiles("not_a_smiles", "invalid")
        self.assertEqual(result["status"], "invalid")
        self.assertEqual(result["molecular_weight_g_mol"], "")
        self.assertEqual(result["qed"], "")
        self.assertTrue(result["error"])

    def test_csv_batch_and_missing_column(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            source = directory / "compounds.csv"
            target = directory / "descriptors.csv"
            source.write_text("compound,smiles\nethanol,CCO\naspirin,CC(=O)Oc1ccccc1C(=O)O\nbad,invalid$$\n")
            summary = screen_csv(source, target)
            self.assertEqual(summary, {"total": 3, "computed": 2, "invalid": 1})
            with target.open(newline="", encoding="utf-8") as fd:
                rows = list(csv.DictReader(fd))
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0]["molecular_formula"], "C2H6O")
            self.assertEqual(rows[-1]["status"], "invalid")
            source.write_text("name,structure\nx,CCO\n")
            with self.assertRaisesRegex(ValueError, "smiles"):
                screen_csv(source, target)

    def test_rejects_input_output_collision(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "items.csv"
            source.write_text("smiles\nCCO\n")
            with self.assertRaisesRegex(ValueError, "differ"):
                screen_csv(source, source)


if __name__ == "__main__":
    unittest.main()
