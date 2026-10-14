"""Regression tests for conservative, deterministic emergency language screening.

Run: PYTHONPATH=backend python -m unittest discover -s tests -p 'test_clinical_guardrails.py'
"""
import unittest

from app.clinical.guardrails import evaluate_input, asks_for_self_medication, patient_safety_notice


class ClinicalSafetyTests(unittest.TestCase):
    def test_emergency_disclosures(self):
        examples = [
            "I have chest pain",
            "I cannot breathe",
            "My face is drooping",
            "I have sudden loss of vision",
            "I am suicidal",
            "I want to end my life",
            "I had an overdose on purpose",
            "I am pregnant with severe bleeding",
            "I have chest tightness",
        ]
        for message in examples:
            with self.subTest(message=message):
                decision = evaluate_input(message)
                self.assertTrue(decision.emergency)
                self.assertFalse(decision.blocked)
                self.assertTrue(decision.matched_red_flags)

    def test_nonmedical_request_is_blocked(self):
        decision = evaluate_input("write my essay")
        self.assertTrue(decision.blocked)
        self.assertFalse(decision.emergency)

    def test_routine_request_does_not_trigger_emergency(self):
        decision = evaluate_input("I have had a mild itchy scalp for a week")
        self.assertFalse(decision.emergency)
        self.assertFalse(decision.blocked)

    def test_medication_dose_request_is_detected(self):
        self.assertTrue(asks_for_self_medication("what dose should I take"))

    def test_emergency_notice_requires_immediate_help(self):
        notice = patient_safety_notice(True).lower()
        self.assertIn("immediately", notice)
        self.assertIn("emergency", notice)


if __name__ == "__main__":
    unittest.main()
