"""Data processing and statistical aggregation (Task 3).

raw .jsonl  ->  validated, warm-up filtered, outlier-flagged, aggregated CSV.

Statistical choices:
  * warm-up runs (phase == "warmup") are discarded before any statistic;
  * errors are kept as a guardrail (error_rate), latency statistics use ok runs;
  * outliers are only *flagged* (Tukey 1.5 x IQR), never deleted: a real load
    spike and hardware noise cannot be told apart from latency alone;
  * median and percentiles are reported with a percentile-bootstrap 95% CI,
    which needs no normality assumption (latency is right-skewed).
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from src import physics

REQUIRED = ["run_id", "ts_us", "phase", "family", "D", "n_grid", "rep",
            "latency_ms", "ok", "error"]
KEYS = ["D", "n_grid"]


def load_config(path="configs/config.yaml"):
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_raw(path):
    """Read a JSON Lines file and validate its schema."""
    df = pd.read_json(path, lines=True)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"raw log is missing columns: {missing}")
    bad_phase = set(df["phase"].unique()) - {"warmup", "benchmark"}
    if bad_phase:
        raise ValueError(f"unknown phase labels: {sorted(bad_phase)}")
    return df


def split_phases(df):
    """Return (warmup, benchmark) frames; only benchmark runs enter statistics."""
    warm = df[df["phase"] == "warmup"].copy()
    bench = df[df["phase"] == "benchmark"].copy()
    return warm, bench


def flag_outliers(bench, factor=1.5):
    """Add a boolean column `is_outlier` (Tukey fences per cell, ok runs only)."""
    bench = bench.copy()
    bench["is_outlier"] = False
    for _, idx in bench[bench["ok"]].groupby(KEYS).groups.items():
        x = bench.loc[idx, "latency_ms"]
        q1, q3 = x.quantile(0.25), x.quantile(0.75)
        iqr = q3 - q1
        bench.loc[idx, "is_outlier"] = (x < q1 - factor * iqr) | (x > q3 + factor * iqr)
    return bench


def bootstrap_ci(x, stat, n_boot, level, rng):
    """Percentile bootstrap CI of `stat` (a function of an array and axis)."""
    x = np.asarray(x, dtype=float)
    idx = rng.integers(0, x.size, size=(n_boot, x.size))
    stats = stat(x[idx], axis=1)
    alpha = (1.0 - level) / 2.0
    lo, hi = np.quantile(stats, [alpha, 1.0 - alpha])
    return float(lo), float(hi)


def _pct(q):
    return lambda a, axis: np.percentile(a, q, axis=axis)


def aggregate(bench, n_boot=2000, level=0.95, seed=42):
    """One row per (D, n_grid): location, spread, tails, CIs, error rate."""
    rng = np.random.default_rng(seed)
    rows = []
    for (D, n_grid), g in bench.groupby(KEYS, sort=True):
        ok = g[g["ok"]]["latency_ms"].to_numpy()
        row = {"D": int(D), "n_grid": int(n_grid), "n_runs": len(g),
               "n_ok": int(ok.size),
               "error_rate": 1.0 - ok.size / len(g),
               "outlier_frac": float(g["is_outlier"].mean())}
        if ok.size:
            row.update({
                "mean_ms": ok.mean(), "sd_ms": ok.std(ddof=1) if ok.size > 1 else 0.0,
                "p25_ms": np.percentile(ok, 25), "p50_ms": np.percentile(ok, 50),
                "p75_ms": np.percentile(ok, 75), "p95_ms": np.percentile(ok, 95),
                "p99_ms": np.percentile(ok, 99),
            })
            for name, fn in (("p50", np.median), ("p95", _pct(95)), ("p99", _pct(99))):
                lo, hi = bootstrap_ci(ok, fn, n_boot, level, rng)
                row[f"{name}_ci_low_ms"], row[f"{name}_ci_high_ms"] = lo, hi
        rows.append(row)
    return pd.DataFrame(rows)


def physics_summary(cfg):
    """Scientific result per dimension, computed from the analytic solutions."""
    exp = cfg["experiment"]
    M, chi_cap = exp["mass"], exp["chi_cap"]
    chis = np.linspace(0.0, chi_cap, exp["n_chi"])
    rows = []
    for D in exp["dimensions"]:
        adm = [c for c in chis if physics.myers_perry(D, float(c), M)["horizon_exists"]]
        tg = physics.tangherlini(D, M)
        rows.append({
            "D": D,
            "B_horizon_at_chi_cap": int(physics.myers_perry(D, chi_cap, M)["horizon_exists"]),
            "chi_max_on_grid": max(adm) if adm else 0.0,
            "r_ph_over_r_h": tg["r_ph_over_r_h"],
            "has_stable_circular_orbit": bool(tg["has_stable_orbit"]),
            "temperature_M1": tg["temperature"],
            "entropy_M1": tg["entropy"],
        })
    return pd.DataFrame(rows)


def run(cfg):
    """Full pipeline; returns (warmup, bench, summary, physics) frames."""
    a = cfg["analysis"]
    np.random.seed(a["seed"])
    raw = load_raw(a["raw"])
    warm, bench = split_phases(raw)
    bench = flag_outliers(bench, a["iqr_factor"])
    summary = aggregate(bench, a["n_bootstrap"], a["ci_level"], a["seed"])
    phys = physics_summary(cfg)
    return warm, bench, summary, phys


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default="configs/config.yaml")
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    a = cfg["analysis"]
    warm, bench, summary, phys = run(cfg)
    for key, frame in (("processed", summary), ("physics_summary", phys)):
        Path(a[key]).parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(a[key], index=False, float_format="%.6g")
    print(json.dumps({"warmup_runs_discarded": len(warm),
                      "benchmark_runs": len(bench),
                      "cells": len(summary),
                      "max_error_rate": float(summary["error_rate"].max())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
