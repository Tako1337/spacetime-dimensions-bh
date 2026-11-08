"""Tests for the raw-data collector (needs only numpy/scipy)."""
import unittest

from src import collect


class TestRunCell(unittest.TestCase):
    def test_records_and_phases(self):
        counter = [0]
        recs = collect.run_cell(5, 500, 1.0, n_warmup=2, n_repeats=4, counter=counter)
        self.assertEqual(len(recs), 6)
        self.assertEqual([r["phase"] for r in recs], ["warmup"] * 2 + ["benchmark"] * 4)
        self.assertEqual([r["run_id"] for r in recs], list(range(1, 7)))
        self.assertTrue(all(r["ok"] and r["error"] is None for r in recs))
        self.assertTrue(all(r["latency_ms"] > 0 for r in recs))

    def test_failures_are_logged_not_dropped(self):
        original = collect.target
        collect.target = lambda D, mu, n: (_ for _ in ()).throw(RuntimeError("boom"))
        try:
            recs = collect.run_cell(5, 500, 1.0, 0, 3, [0])
        finally:
            collect.target = original
        self.assertEqual(len(recs), 3)
        self.assertTrue(all(not r["ok"] and "RuntimeError" in r["error"] for r in recs))


if __name__ == "__main__":
    unittest.main()
