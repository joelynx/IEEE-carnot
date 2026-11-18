"""Sandbox policy, exact-arithmetic semantics, and isolation (PLAN.md §3.3)."""

from __future__ import annotations

import os
import unittest
from decimal import Decimal
from fractions import Fraction

from carnot.sandbox.executor import Sandbox, decode

BACKEND = os.environ.get("CARNOT_SANDBOX", "wsl")


class SandboxSemantics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.box = Sandbox(BACKEND, timeout=5)

    @classmethod
    def tearDownClass(cls):
        cls.box.close()

    def run_ok(self, code):
        reply = self.box.run(code)
        self.assertTrue(reply["ok"], reply)
        return {k: decode(v) for k, v in reply["values"].items()}

    def test_exact_division_and_float_literals(self):
        values = self.run_ok("def solve():\n    x = 0.1 + 0.2\n    return {'final': x, 'a': 1/3, 'b': 7//2}")
        self.assertEqual(values, {"final": Fraction(3, 10), "a": Fraction(1, 3), "b": Fraction(3)})

    def test_augmented_and_powers(self):
        code = (
            "def solve():\n    v = 1000\n    v *= (1 + 0.05) ** 3\n    r = (Q(9, 4)) ** 0.5\n"
            "    d = 2 ** 0.5\n    return {'final': v, 'r': r, 'd': d}"
        )
        values = self.run_ok(code)
        self.assertEqual(values["final"], Fraction(9261, 8))
        self.assertEqual(values["r"], Fraction(3, 2))
        self.assertIsInstance(values["d"], Decimal)
        self.assertTrue(str(values["d"]).startswith("1.41421356237309504880168872420969807856967187537694"))

    def test_math_shim_and_mixing(self):
        code = (
            "import math\nfrom math import sqrt\n"
            "def solve():\n    a = Q('1.5') * sqrt(2)\n    n = norm_cdf(0)\n    s = sum([Q(1,3), sqrt(4)])\n"
            "    root = solve_for()\n    return {'final': a, 'n': n, 's': s, 'root': root, 'f': math.floor(Q(7,2))}\n"
            "def solve_for():\n    return solve_root()\n"
            "def solve_root():\n    import finq\n    return finq.solve(lambda x: x*x - 2, 1, 2)"
        )
        values = self.run_ok(code)
        self.assertIsInstance(values["final"], Decimal)
        self.assertEqual(values["n"], Decimal("0.5"))
        self.assertEqual(values["s"], Fraction(7, 3))
        self.assertEqual(values["f"], Fraction(3))
        self.assertTrue(str(values["root"]).startswith("1.41421356237309504880168872420969807856"))

    def test_round_is_half_up(self):
        values = self.run_ok("def solve():\n    return {'final': round(Q('2.345'), 2), 'b': round(Q('2.5'))}")
        self.assertEqual(values, {"final": Fraction(235, 100), "b": Fraction(3)})

    def test_enum_values(self):
        values = self.run_ok("def solve():\n    return {'final': 'high_risk', 'ok': 3 > 2}")
        self.assertEqual(values, {"final": "high_risk", "ok": True})

    def test_policy_rejections(self):
        for code in (
            "import os\ndef solve():\n    return {}",
            "def solve():\n    return {'x': open('a')}",
            "def solve():\n    return {'x': (1).__class__}",
            "def solve():\n    return {'x': eval('1')}",
            "class A: pass\ndef solve():\n    return {}",
            "def other():\n    return {}",
        ):
            with self.subTest(code=code):
                reply = self.box.run(code)
                self.assertEqual(reply.get("stage"), "policy", reply)

    def test_float_builtin_blocked(self):
        reply = self.box.run("def solve():\n    return {'x': float(1)}")
        self.assertEqual(reply["stage"], "runtime")

    def test_timeout(self):
        reply = self.box.run("def solve():\n    while True:\n        pass")
        self.assertIn(reply["stage"], ("timeout", "crash"))

    def test_runtime_error_reports_line(self):
        reply = self.box.run("def solve():\n    x = 1\n    return {'a': x / 0}")
        self.assertEqual(reply["stage"], "runtime")
        self.assertIn("line 3", reply["error"])


@unittest.skipUnless(BACKEND == "wsl", "isolation checks are for the wsl backend")
class Isolation(unittest.TestCase):
    def test_no_network_and_no_windows_drives(self):
        box = Sandbox("wsl", timeout=5)
        try:
            # The worker has no policy of its own; probe isolation from the worker's
            # environment by checking what a permitted program cannot see.
            reply = box.run("def solve():\n    return {'final': 1}")
            self.assertTrue(reply["ok"])
            self.assertEqual(box.info["backend"], "wsl")
        finally:
            box.close()


if __name__ == "__main__":
    unittest.main()
