import argparse
import csv
import json
import logging
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

import numpy as np
import yaml

from src import physics

log = logging.getLogger("benchmark")


def load_config(path):
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def build_grid(cfg, sample):
    if sample:
        cells = []
        with open(cfg["paths"]["sample_grid"], newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                cells.append((row["family"], int(row["D"]), float(row["chi"])))
        return cells
    dims = cfg["experiment"]["dimensions"]
    chis = np.linspace(0.0, cfg["experiment"]["chi_cap"], cfg["experiment"]["n_chi"])
    cells = [("tangherlini", D, 0.0) for D in dims]
    cells += [("myers_perry", D, float(c)) for D in dims for c in chis]
    return cells


def evaluate(family, D, chi, M):
    if family == "tangherlini":
        return physics.tangherlini(D, M)
    if family == "myers_perry":
        return physics.myers_perry(D, chi, M)
    raise ValueError(f"unknown family: {family}")


def measure_cell(family, D, chi, M, n_repeats, n_warmup):
    for _ in range(n_warmup):
        evaluate(family, D, chi, M)
    times = []
    for _ in range(n_repeats):
        t0 = time.perf_counter()
        res = evaluate(family, D, chi, M)
        times.append((time.perf_counter() - t0) * 1e3)
    tracemalloc.start()
    evaluate(family, D, chi, M)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return res, statistics.median(times), peak / 1e6


def summarize(rows, cfg, sample):
    g = cfg["guardrails"]
    exist = [r for r in rows if r["horizon_exists"]]
    max_res = max((r["residual"] for r in exist), default=0.0)
    max_smarr = max((r["smarr_rel_err"] for r in exist), default=0.0)
    max_lat = max(r["latency_ms"] for r in rows)

    M = cfg["experiment"]["mass"]
    sch = physics.tangherlini(4, M)
    kerr_in = physics.myers_perry(4, 0.4999, M)["horizon_exists"]
    kerr_out = physics.myers_perry(4, 0.5001, M)["horizon_exists"]
    baseline_ok = (
        abs(sch["r_h"] - 2.0 * M) < g["baseline_tol"] and kerr_in and not kerr_out
    )

    guardrails = {
        "max_root_residual": max_res,
        "max_smarr_rel_err": max_smarr,
        "max_latency_ms": max_lat,
        "baseline_D4_reproduced": bool(baseline_ok),
    }
    guardrails["all_passed"] = bool(
        max_res <= g["max_residual"]
        and max_smarr <= g["max_smarr_err"]
        and max_lat <= g["max_latency_ms"]
        and baseline_ok
    )
    summary = {"mode": "sample" if sample else "full", "n_cells": len(rows),
               "guardrails": guardrails}
    if sample:
        summary["hypothesis_verdict"] = "not evaluated in sample mode"
        return summary

    chi_cap = cfg["experiment"]["chi_cap"]
    per_dim = {}
    for D in cfg["experiment"]["dimensions"]:
        mp = [r for r in rows if r["family"] == "myers_perry" and r["D"] == D]
        tg = next(r for r in rows if r["family"] == "tangherlini" and r["D"] == D)
        adm = [r["chi"] for r in mp if r["horizon_exists"]]
        capped = next(r for r in mp if abs(r["chi"] - chi_cap) < 1e-12)
        per_dim[D] = {
            "primary_B_unbounded_spin": int(capped["horizon_exists"]),
            "chi_max_admissible": max(adm) if adm else 0.0,
            "r_ph_over_r_h": tg["r_ph_over_r_h"],
            "has_stable_circular_orbit": bool(tg["has_stable_orbit"]),
            "temperature_M1": tg["temperature"],
            "entropy_M1": tg["entropy"],
        }
    base = per_dim[4]
    higher = {D: v for D, v in per_dim.items() if D >= 5}
    h1_primary = base["primary_B_unbounded_spin"] == 0 and any(
        v["primary_B_unbounded_spin"] == 1 for v in higher.values()
    )
    h1_secondary = base["has_stable_circular_orbit"] and any(
        not v["has_stable_circular_orbit"] for v in higher.values()
    )
    summary["per_dimension"] = per_dim
    summary["hypothesis_verdict"] = {
        "H0_rejected_by_primary_metric": bool(h1_primary),
        "secondary_ISCO_support": bool(h1_secondary),
        "valid_only_if_guardrails_passed": guardrails["all_passed"],
    }
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/config.yaml")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--sample", action="store_true")
    mode.add_argument("--full", action="store_true")
    args = ap.parse_args(argv)
    sample = not args.full

    cfg = load_config(args.config)
    out_dir = Path(cfg["paths"]["results_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout),
                  logging.FileHandler(out_dir / "benchmark.log", mode="w")],
    )
    tag = "sample" if sample else "full"
    cells = build_grid(cfg, sample)
    log.info("mode=%s cells=%d", tag, len(cells))

    M = cfg["experiment"]["mass"]
    rows = []
    for family, D, chi in cells:
        res, lat, mem = measure_cell(
            family, D, chi, M, cfg["benchmark"]["n_repeats"], cfg["benchmark"]["n_warmup"]
        )
        row = {"family": family, "D": D, "chi": chi, "latency_ms": lat,
               "peak_mem_mb": mem}
        row.update({k: res.get(k, "") for k in cfg["output"]["columns"]})
        rows.append(row)
        log.info("%s D=%d chi=%.3f horizon=%s latency=%.4f ms",
                 family, D, chi, res["horizon_exists"], lat)

    cols = ["family", "D", "chi", "latency_ms", "peak_mem_mb"] + cfg["output"]["columns"]
    with open(out_dir / f"results_{tag}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    summary = summarize(rows, cfg, sample)
    with open(out_dir / f"summary_{tag}.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=float)
    log.info("guardrails: %s", json.dumps(summary["guardrails"]))
    log.info("verdict: %s", summary["hypothesis_verdict"])
    return 0 if summary["guardrails"]["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
