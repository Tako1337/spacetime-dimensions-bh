"""Raw-data collector (Task 3).

Times the circular-orbit stability scan (the dominant cost of one benchmark
cell) while the workload N (number of radial grid points) and the spacetime
dimension D are swept. One JSON object per run is written to a .jsonl file.

Design rules (see docs/domain_model.md):
  * only the target call sits between the two perf_counter_ns() reads;
  * records are kept in memory and written after all timing is finished,
    so file I/O never contaminates a measurement;
  * each cell gets a warm-up phase that is logged but marked phase="warmup";
  * failures are logged (ok=false), never silently dropped;
  * the order of cells is shuffled with a fixed seed to spread slow drift
    of the machine over all cells instead of biasing one of them.
"""
import argparse
import gc
import hashlib
import json
import logging
import os
import platform
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import scipy
import yaml

from src import physics

log = logging.getLogger("collect")
FAMILY = "orbit_scan"


def _cpu_model():
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as fh:
            for line in fh:
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "unknown"


def _ram_gb():
    try:
        return round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1e9, 2)
    except (ValueError, OSError, AttributeError):
        return None


def _git_commit():
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                             text=True, timeout=5, check=True)
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def environment_metadata(config_path, cfg):
    raw = Path(config_path).read_bytes()
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_model": _cpu_model(),
        "cpu_count": os.cpu_count(),
        "ram_gb": _ram_gb(),
        "in_docker": Path("/.dockerenv").exists(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "pyyaml": yaml.__version__,
        "git_commit": _git_commit(),
        "config_sha256": hashlib.sha256(raw).hexdigest(),
        "collect_config": cfg["collect"],
    }


def target(D, mu, n_grid):
    """The measured function: orbit-stability scan with n_grid radial points."""
    return physics.circular_orbit_stability(D, mu, n_grid=n_grid)


def run_cell(D, n_grid, M, n_warmup, n_repeats, counter):
    """Time one (D, n_grid) cell. Returns a list of records (no I/O here)."""
    mu = physics.mu_from_mass(D, M)
    records = []
    gc.collect()
    gc.disable()
    try:
        for phase, count in (("warmup", n_warmup), ("benchmark", n_repeats)):
            for rep in range(count):
                error = None
                t0 = time.perf_counter_ns()
                try:
                    target(D, mu, n_grid)
                except Exception as exc:  # logged, not dropped
                    error = f"{type(exc).__name__}: {exc}"
                t1 = time.perf_counter_ns()
                counter[0] += 1
                records.append({
                    "run_id": counter[0],
                    "ts_us": time.time_ns() // 1000,
                    "phase": phase,
                    "family": FAMILY,
                    "D": D,
                    "n_grid": n_grid,
                    "rep": rep,
                    "latency_ms": (t1 - t0) / 1e6,
                    "ok": error is None,
                    "error": error,
                })
    finally:
        gc.enable()
    return records


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default="configs/config.yaml")
    ap.add_argument("--out", default=None, help="override collect.output")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    with open(args.config, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    c = cfg["collect"]
    M = cfg["experiment"]["mass"]
    out_path = Path(args.out or c["output"])
    meta_path = Path(c["metadata"])
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cells = [(D, n) for D in c["dimensions"] for n in c["n_grid_values"]]
    random.Random(c["seed"]).shuffle(cells)
    log.info("cells=%d warmup=%d repeats=%d", len(cells), c["n_warmup"], c["n_repeats"])

    started = datetime.now(timezone.utc).isoformat()
    counter = [0]
    records = []
    for D, n_grid in cells:
        records.extend(run_cell(D, n_grid, M, c["n_warmup"], c["n_repeats"], counter))
    finished = datetime.now(timezone.utc).isoformat()

    with open(out_path, "w", encoding="utf-8") as fh:  # I/O only after timing
        for rec in records:
            fh.write(json.dumps(rec) + "\n")
    meta = environment_metadata(args.config, cfg)
    meta.update({"started_utc": started, "finished_utc": finished,
                 "n_records": len(records), "n_cells": len(cells)})
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    n_bad = sum(1 for r in records if not r["ok"])
    log.info("wrote %d records (%d failed) to %s", len(records), n_bad, out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
