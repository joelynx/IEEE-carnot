"""S2 safeguard gates and runner v2 arm parsing."""

import unittest

from carnot import improvement_validation_v2 as v2
from carnot.safeguard_s2_v1 import clopper_pearson_upper, gates


def table(facs, slots=None):
    return {f"c{i}": {"fac": f, "matched_slots": (slots[i] if slots else 2), "total_slots": 2} for i, f in enumerate(facs)}


TEMPLATES = {f"c{i}": f"t{i // 2}" for i in range(580)}


class Gates(unittest.TestCase):
    def test_zero_losses_on_290_templates_passes(self):
        base = table([1] * 580)
        result = gates(base, base, base, TEMPLATES)
        self.assertEqual(result["status"], "pass")
        self.assertAlmostEqual(result["G2_upper_95"], 0.010277, places=5)

    def test_one_loss_fails_even_with_gains(self):
        base = table([1] * 578 + [0, 0])
        cand = table([0] + [1] * 579)
        result = gates(base, base, cand, TEMPLATES)
        self.assertFalse(result["G1"])
        self.assertFalse(result["G2"])
        self.assertEqual(len(result["final_gains"]), 2)
        self.assertEqual(result["status"], "fail")

    def test_noisy_baseline_makes_the_run_invalid(self):
        base, rep = table([1] * 580), table([0, 0, 0] + [1] * 577)
        self.assertEqual(gates(base, rep, base, TEMPLATES)["status"], "invalid")
        self.assertTrue(gates(base, table([0, 0] + [1] * 578), base, TEMPLATES)["G3_valid"])

    def test_checkpoint_tolerance_is_noise_calibrated_with_a_floor(self):
        base = table([1] * 580)
        cand = table([1] * 580, [1, 1] + [2] * 578)
        self.assertTrue(gates(base, base, cand, TEMPLATES)["G4"])
        cand = table([1] * 580, [1, 1, 1] + [2] * 577)
        self.assertFalse(gates(base, base, cand, TEMPLATES)["G4"])
        rep = table([1] * 580, [0, 0] + [2] * 578)
        self.assertEqual(gates(base, rep, cand, TEMPLATES)["G4_tolerance"], 4)

    def test_bound_matches_the_plan_table(self):
        self.assertAlmostEqual(clopper_pearson_upper(1, 290), 0.01625, places=4)


class Arms(unittest.TestCase):
    def test_parse_and_reject_overlapping_identities(self):
        self.assertEqual(v2.parse_arms(["R4a=r4:700", "P=p:720"]), [("R4a", "r4", 700), ("P", "p", 720)])
        for bad in (["A=r4:700", "B=r4:702"], ["A=r4:700", "A=p:720"], ["A=x:1"]):
            with self.subTest(bad=bad), self.assertRaises(SystemExit):
                v2.parse_arms(bad)


if __name__ == "__main__":
    unittest.main()
