"""Publication-ready figures (Task 3).

The three rules of scientific visualisation are enforced here, not left to
the caller: (1) axes carry names and units, log scales where values span
orders of magnitude; (2) uncertainty is always drawn (shaded 95% bootstrap
CI or error bars); (3) palette is colour-blind safe and every series also
differs by marker and line style, so the figure survives monochrome print.
Every figure is written as vector .pdf and as .png at 300 DPI.
"""
import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from src import process_data

MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*"]
LINESTYLES = ["-", "--", "-.", ":", (0, (5, 1)), (0, (3, 1, 1, 1)), (0, (1, 1)), (0, (5, 2))]
DPI = 300


def set_style():
    sns.set_theme(style="whitegrid", font_scale=1.2, palette="colorblind")
    plt.rcParams.update({
        "pdf.fonttype": 42,          # embed TrueType, editable in LaTeX/Illustrator
        "savefig.dpi": DPI,
        "figure.dpi": 100,
        "axes.titleweight": "bold",
    })


def save_figure(fig, stem, out_dir):
    """Write <stem>.pdf (vector) and <stem>.png (300 DPI); return both paths."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext in ("pdf", "png"):
        p = out_dir / f"{stem}.{ext}"
        fig.savefig(p, bbox_inches="tight", dpi=DPI)
        paths.append(p)
    return paths


def plot_latency_vs_load(summary, dims, baseline_dim=4):
    """Fig. 1. (a) median latency vs workload per dimension, (b) tail percentiles
    of the baseline. Bands are 95% percentile-bootstrap CIs."""
    set_style()
    pal = sns.color_palette("colorblind", len(dims))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 5.0))

    for i, D in enumerate(dims):
        g = summary[summary["D"] == D].sort_values("n_grid")
        label = f"D = {D}" + (" (baseline)" if D == baseline_dim else "")
        ax1.plot(g["n_grid"], g["p50_ms"], color=pal[i], marker=MARKERS[i],
                 linestyle=LINESTYLES[i], linewidth=1.8, markersize=6, label=label)
        ax1.fill_between(g["n_grid"], g["p50_ci_low_ms"], g["p50_ci_high_ms"],
                         color=pal[i], alpha=0.25, linewidth=0)
    ax1.set(xscale="log", yscale="log",
            xlabel="Workload: radial grid points N (count)",
            ylabel="Median latency per orbit scan (ms)",
            title="(a) Median latency vs workload")
    ax1.legend(title="Spacetime dimension", fontsize=10, title_fontsize=10)

    base = summary[summary["D"] == baseline_dim].sort_values("n_grid")
    pal2 = sns.color_palette("colorblind", 3)
    for j, (q, name) in enumerate((("p50", "p50"), ("p95", "p95"), ("p99", "p99"))):
        ax2.plot(base["n_grid"], base[f"{q}_ms"], color=pal2[j], marker=MARKERS[j],
                 linestyle=LINESTYLES[j], linewidth=1.8, markersize=6, label=name)
        ax2.fill_between(base["n_grid"], base[f"{q}_ci_low_ms"], base[f"{q}_ci_high_ms"],
                         color=pal2[j], alpha=0.25, linewidth=0)
    ax2.set(xscale="log", yscale="log",
            xlabel="Workload: radial grid points N (count)",
            ylabel="Latency per orbit scan (ms)",
            title=f"(b) Tail latency, baseline D = {baseline_dim}")
    ax2.legend(title="Percentile", fontsize=10, title_fontsize=10)
    fig.tight_layout()
    return fig


def plot_distribution_boxplot(bench, n_grid, n_boot=2000, level=0.95, seed=42,
                              baseline_dim=4):
    """Fig. 2. Latency distribution per dimension at fixed workload. Boxes show
    p25-p75 and whiskers 1.5 IQR; the black marker is the median with its 95%
    bootstrap CI. The baseline box is hatched."""
    set_style()
    d = bench[(bench["n_grid"] == n_grid) & bench["ok"]]
    dims = sorted(d["D"].unique())
    pal = sns.color_palette("colorblind", len(dims))
    rng = np.random.default_rng(seed)
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    data = [d.loc[d["D"] == D, "latency_ms"].to_numpy() for D in dims]
    bp = ax.boxplot(data, positions=range(len(dims)), widths=0.6, patch_artist=True,
                    showfliers=True, medianprops={"color": "none"},
                    flierprops={"marker": "x", "markersize": 5, "markeredgecolor": "0.3"})
    for i, (box, D) in enumerate(zip(bp["boxes"], dims)):
        box.set(facecolor=pal[i], alpha=0.75, edgecolor="black", linewidth=1.2)
        if D == baseline_dim:
            box.set_hatch("//")
    for i, x in enumerate(data):
        lo, hi = process_data.bootstrap_ci(x, np.median, n_boot, level, rng)
        med = float(np.median(x))
        ax.errorbar(i, med, yerr=[[med - lo], [hi - med]], fmt="o", color="black",
                    markersize=6, capsize=4, elinewidth=1.6, zorder=5,
                    label="median, 95% bootstrap CI" if i == 0 else None)
    ax.set_xticks(range(len(dims)))
    ax.set_xticklabels([f"{D}\n(baseline)" if D == baseline_dim else str(D) for D in dims])
    ax.set_ylim(bottom=0)
    ax.set(xlabel="Spacetime dimension D (dimensionless)",
           ylabel="Latency per orbit scan (ms)",
           title=f"Latency distribution at N = {n_grid:,} grid points")
    ax.legend(loc="upper left", fontsize=10)
    fig.tight_layout()
    return fig


def make_all(cfg, summary=None, bench=None):
    """Generate and save both figures; returns the list of written paths."""
    a = cfg["analysis"]
    if summary is None or bench is None:
        _, bench, summary, _ = process_data.run(cfg)
    paths = []
    fig1 = plot_latency_vs_load(summary, a["fig_dimensions"])
    paths += save_figure(fig1, "fig1_latency_vs_load", a["figures_dir"])
    fig2 = plot_distribution_boxplot(bench, a["box_n_grid"], a["n_bootstrap"],
                                     a["ci_level"], a["seed"])
    paths += save_figure(fig2, "fig2_distribution_boxplot", a["figures_dir"])
    plt.close("all")
    return paths


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default="configs/config.yaml")
    args = ap.parse_args(argv)
    for p in make_all(process_data.load_config(args.config)):
        print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
