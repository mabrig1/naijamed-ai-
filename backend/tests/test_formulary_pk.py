from __future__ import annotations

import math
import unittest

from app.formulary_pk import noncompartmental_analysis, one_compartment_simulation


class FormularyPKTests(unittest.TestCase):
    def test_nca_recovers_terminal_half_life_for_exponential_decay(self):
        observations = [
            {"time": 0.0, "concentration": 10.0},
            {"time": 1.0, "concentration": 10.0 * math.exp(-math.log(2) / 2)},
            {"time": 2.0, "concentration": 5.0},
            {"time": 3.0, "concentration": 5.0 * math.exp(-math.log(2) / 2)},
            {"time": 4.0, "concentration": 2.5},
        ]
        result = noncompartmental_analysis(observations, terminal_points=3)
        self.assertAlmostEqual(result["metrics"]["terminal_half_life"], 2.0, places=4)
        self.assertAlmostEqual(result["metrics"]["terminal_r_squared"], 1.0, places=4)
        self.assertAlmostEqual(result["metrics"]["cmax"], 10.0, places=4)
        self.assertEqual(result["metrics"]["tmax"], 0.0)

    def test_iv_bolus_simulation_starts_at_dose_over_volume(self):
        result = one_compartment_simulation(
            model="one_compartment_iv_bolus",
            dose=100.0,
            volume=20.0,
            elimination_half_life=4.0,
            duration=8.0,
            points=21,
        )
        curve = result["curve"]
        self.assertAlmostEqual(curve[0]["concentration"], 5.0, places=5)
        midpoint = min(curve, key=lambda row: abs(row["time"] - 4.0))
        self.assertAlmostEqual(midpoint["concentration"], 2.5, places=3)

    def test_oral_simulation_is_non_negative_and_has_nonzero_tmax(self):
        result = one_compartment_simulation(
            model="one_compartment_oral",
            dose=100.0,
            volume=20.0,
            elimination_half_life=4.0,
            duration=12.0,
            points=101,
            bioavailability=0.8,
            absorption_rate=1.2,
        )
        self.assertTrue(all(row["concentration"] >= 0 for row in result["curve"]))
        self.assertGreater(result["metrics"]["cmax_simulated"], 0)
        self.assertGreater(result["metrics"]["tmax_simulated"], 0)

    def test_duplicate_time_is_rejected(self):
        with self.assertRaises(ValueError):
            noncompartmental_analysis(
                [
                    {"time": 0.0, "concentration": 10.0},
                    {"time": 1.0, "concentration": 8.0},
                    {"time": 1.0, "concentration": 7.0},
                ]
            )


if __name__ == "__main__":
    unittest.main()
