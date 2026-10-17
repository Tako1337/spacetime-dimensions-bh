"""Unit tests for the analytic black-hole formulas (stdlib unittest only)."""
import math
import unittest

from src import physics


class TestBaselineD4(unittest.TestCase):
    def test_schwarzschild(self):
        bh = physics.tangherlini(4, 1.0)
        self.assertAlmostEqual(bh["r_h"], 2.0, places=12)
        self.assertAlmostEqual(bh["temperature"], 1 / (8 * math.pi), places=12)
        self.assertAlmostEqual(bh["r_ph_over_r_h"], 1.5, places=12)
        self.assertAlmostEqual(bh["r_isco"], 6.0, delta=0.06)

    def test_kerr_extremal_bound(self):
        self.assertTrue(physics.myers_perry(4, 0.4999)["horizon_exists"])
        self.assertFalse(physics.myers_perry(4, 0.5001)["horizon_exists"])


class TestHigherDimensions(unittest.TestCase):
    def test_no_stable_orbits_above_four(self):
        for D in range(5, 12):
            with self.subTest(D=D):
                self.assertFalse(physics.tangherlini(D, 1.0)["has_stable_orbit"])

    def test_five_dim_bound(self):
        self.assertTrue(physics.myers_perry(5, 0.99)["horizon_exists"])
        self.assertFalse(physics.myers_perry(5, 1.01)["horizon_exists"])

    def test_ultraspinning_no_bound(self):
        for D in range(6, 12):
            with self.subTest(D=D):
                self.assertTrue(physics.myers_perry(D, 50.0)["horizon_exists"])


class TestConsistency(unittest.TestCase):
    def test_zero_spin_matches_tangherlini(self):
        for D in range(4, 12):
            with self.subTest(D=D):
                mp, tg = physics.myers_perry(D, 0.0), physics.tangherlini(D)
                self.assertAlmostEqual(mp["r_h"] / tg["r_h"], 1.0, places=9)
                self.assertAlmostEqual(mp["temperature"] / tg["temperature"], 1.0, places=9)
                self.assertAlmostEqual(mp["area"] / tg["area"], 1.0, places=9)

    def test_smarr_relation(self):
        for D in range(4, 12):
            for chi in (0.1, 0.3, 0.45):
                with self.subTest(D=D, chi=chi):
                    self.assertLess(physics.myers_perry(D, chi)["smarr_rel_err"], 1e-9)


if __name__ == "__main__":
    unittest.main()
