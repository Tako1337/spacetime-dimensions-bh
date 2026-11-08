"""Tests for the statistics module (skipped when pandas is not installed)."""
import json
import tempfile
import unittest
from pathlib import Path

try:
    import numpy as np
    import pandas as pd
except ImportError:  # the Docker image only ships the Task 2 dependencies
    raise unittest.SkipTest("pandas not installed (pip install -r requirements-analysis.txt)")

from src import process_data


def make_frame():
    rows = []
    for phase, n, base in (("warmup", 3, 50.0), ("benchmark", 40, 1.0)):
        for rep in range(n):
            rows.append({"run_id": len(rows) + 1, "ts_us": 0, "phase": phase,
                         "family": "orbit_scan", "D": 4, "n_grid": 1000, "rep": rep,
                         "latency_ms": base + 0.01 * rep, "ok": True, "error": None})
    rows[-1]["latency_ms"] = 99.0          # one spike
    rows[-2].update(ok=False, error="boom")  # one failure
    return pd.DataFrame(rows)


class TestProcessing(unittest.TestCase):
    def test_warmup_is_discarded(self):
        warm, bench = process_data.split_phases(make_frame())
        self.assertEqual((len(warm), len(bench)), (3, 40))
        self.assertEqual(set(bench["phase"]), {"benchmark"})

    def test_outliers_are_flagged_not_deleted(self):
        _, bench = process_data.split_phases(make_frame())
        flagged = process_data.flag_outliers(bench)
        self.assertEqual(len(flagged), len(bench))
        self.assertTrue(flagged["is_outlier"].iloc[-1])

    def test_error_rate_is_a_guardrail(self):
        _, bench = process_data.split_phases(make_frame())
        agg = process_data.aggregate(process_data.flag_outliers(bench), n_boot=200)
        self.assertAlmostEqual(agg.loc[0, "error_rate"], 1 / 40)
        self.assertEqual(agg.loc[0, "n_ok"], 39)

    def test_bootstrap_ci_brackets_statistic_and_is_seeded(self):
        x = np.random.default_rng(0).lognormal(size=60)
        a = process_data.bootstrap_ci(x, np.median, 500, 0.95, np.random.default_rng(42))
        b = process_data.bootstrap_ci(x, np.median, 500, 0.95, np.random.default_rng(42))
        self.assertEqual(a, b)
        self.assertLess(a[0], np.median(x))
        self.assertGreater(a[1], np.median(x))

    def test_schema_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.jsonl"
            path.write_text(json.dumps({"phase": "benchmark", "latency_ms": 1.0}) + "\n")
            with self.assertRaises(ValueError):
                process_data.load_raw(path)


if __name__ == "__main__":
    unittest.main()
