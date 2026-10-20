"""Safe cross-app descriptive research compute tests."""
import unittest
from pydantic import ValidationError
from api.nchesent_analysis import SyntheticCohort, analyze_synthetic_cohort

DAYS = (0, 1, 2, 3, 7, 14, 21, 28, 42)


def fixture():
    days = []
    for day in DAYS:
        documented = 32 if day == 0 else (20 if day in (3, 7, 14, 21, 28) else 0)
        tested = documented
        positive = 32 if day == 0 else (2 if day == 3 else 0)
        days.append({
            "day": day,
            "documented": documented,
            "tested": tested,
            "positive": positive,
            "negative": tested - positive,
            "notTested": 0,
            "missing": 32 - documented,
            "densityCount": tested,
            "densitySum": positive * 900,
        })
    return {
        "schemaVersion": "1.0",
        "source": "NcheSent",
        "dataset": "synthetic",
        "clinicalUse": False,
        "scored": False,
        "analysisType": "synthetic_longitudinal_counts",
        "modelVersion": "0.2.0",
        "totalExamples": 32,
        "days": days,
    }


class PharmaOSResearchComputeTests(unittest.TestCase):
    def test_descriptive_arithmetic(self):
        sample = SyntheticCohort.model_validate(fixture())
        result = analyze_synthetic_cohort(sample)
        self.assertEqual(result["dataset"], "synthetic")
        self.assertFalse(result["clinicalUse"])
        self.assertFalse(result["scored"])
        self.assertEqual(result["totalExamples"], 32)
        self.assertEqual(result["summary"]["visitSlots"], 32 * 9)
        self.assertEqual(result["summary"]["positiveObservations"], 34)
        day3 = next(day for day in result["days"] if day["day"] == 3)
        self.assertEqual(day3["syntheticPositivityPercent"], 10.0)
        self.assertEqual(day3["documentationPercent"], 62.5)
        self.assertIsNone(next(day for day in result["days"] if day["day"] == 1)["syntheticPositivityPercent"])
        self.assertNotIn("treatmentRecommendation", result)
        self.assertNotIn("failureRate", result)

    def test_refuse_clinical_and_identifying_fields(self):
        for update in [
            {"dataset": "clinical"},
            {"clinicalUse": True},
            {"scored": True},
            {"patientId": "P001"},
            {"analysisType": "treatment_recommendation"},
            {"source": "Unverified"},
            {"totalExamples": -1},
        ]:
            with self.subTest(update=update):
                with self.assertRaises(ValidationError):
                    SyntheticCohort.model_validate({**fixture(), **update})

    def test_refuse_malformed_day_counts(self):
        for change in [
            {"tested": 5000},
            {"positive": 100},
            {"documented": 999},
            {"missing": 1},
            {"densityCount": 5000},
            {"densitySum": -2},
            {"extraPatientField": "leak"},
        ]:
            sample = fixture()
            sample["days"][3] = {**sample["days"][3], **change}
            with self.subTest(change=change):
                with self.assertRaises(ValidationError):
                    SyntheticCohort.model_validate(sample)

    def test_refuse_days_out_of_order_or_duplicate(self):
        sample = fixture()
        sample["days"][1]["day"] = 3
        with self.assertRaises(ValidationError):
            SyntheticCohort.model_validate(sample)

    def test_density_missingness_does_not_imply_efficacy(self):
        sample = fixture()
        sample["days"][3]["densityCount"] = 0
        sample["days"][3]["densitySum"] = 0
        report = analyze_synthetic_cohort(SyntheticCohort.model_validate(sample))
        day3 = next(day for day in report["days"] if day["day"] == 3)
        self.assertIsNone(day3["meanRecordedDensity"])
        self.assertIn("unlinked aggregate counts", report["limitations"][0])


if __name__ == "__main__":
    unittest.main()
