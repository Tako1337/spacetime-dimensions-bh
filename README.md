# Spacetime Dimensionality and Black-Hole Properties: A Computational Benchmark

**Authors:** Talgat Bakytuly, Dauletuly Amirlan
**Course:** Research Methods, Task 2

## Research Question

How does changing the number of spacetime dimensions *D* affect the geometry and properties of black holes? (RQ3 from Task 1, *Multidimensional Spacetime and the Theory of Relativity*.)

RQ1 and RQ2 are descriptive and covered by the literature review. RQ3 is tested computationally: we evaluate the Schwarzschild-Tangherlini and single-spin Myers-Perry solutions for *D* = 4...11 and compare them with the *D* = 4 baseline (Schwarzschild/Kerr).

- **H0:** for *D* >= 5 the properties do not differ qualitatively from *D* = 4.
- **H1:** for some *D* >= 5 they do (no spin bound, no stable circular orbits).

Units: G = c = hbar = k_B = 1, M = 1.

## Overview

| Item | Value |
|---|---|
| Independent variables | dimension *D*, spin chi = a / mu^(1/(D-3)), solution family |
| Primary metric | B(D): horizon exists at chi = 4 (no spin bound) |
| Secondary metrics | r_ph/r_h, stable circular orbits, T_H, entropy, chi_max |
| Guardrails | root residual <= 1e-10, Smarr error <= 1e-9, D = 4 reproduced, latency <= 1 s |
| Baseline | D = 4 Schwarzschild / Kerr |

## Planned benchmarks

| ID | Benchmark | Family | Sweep |
|---|---|---|---|
| B1 | Horizon radius, area, entropy, temperature | Tangherlini | D = 4...11 |
| B2 | Photon sphere ratio, stable orbits | Tangherlini | D = 4...11 |
| B3 | Spin bound | Myers-Perry | D = 4...11, chi in [0, 4], 41 points |
| B4 | Smarr relation check | Myers-Perry | all cells |
| B5 | Latency and peak memory | both | 30 repeats per cell |

## Structure

```
.
├── README.md
├── LICENSE
├── Dockerfile
├── requirements.txt
├── .gitignore
├── configs/config.yaml
├── data/sample/sample_grid.csv
├── src/
│   ├── physics.py
│   └── benchmark.py
├── scripts/run.sh
├── tests/test_physics.py
├── notebooks/
├── docs/methodology_card.md
└── results/
```

## System requirements

Docker, or Python 3.13 with `pip install -r requirements.txt`. Runs in under a second, under 100 MB RAM.

## Quickstart

```bash
git clone https://github.com/Tako1337/spacetime-dimensions-bh.git && cd spacetime-dimensions-bh
docker build -t dimbh .
docker run --rm -v "$(pwd)/results:/app/results" dimbh
```

Full sweep: add `--full` after `dimbh`. Tests:

```bash
docker run --rm --entrypoint python dimbh -m unittest discover -s tests -t .
```

Without Docker:

```bash
pip install -r requirements.txt && ./scripts/run.sh --sample
```

Output goes to `results/` (`results_<mode>.csv`, `summary_<mode>.json`, `benchmark.log`).

## Limitations

The benchmark checks known analytic results and gives no observational evidence for extra dimensions. Stability of ultraspinning horizons (D >= 6) is not tested.

## License / Citation

MIT License. Cite as: Bakytuly, T., Dauletuly, A. (2026). *Spacetime Dimensionality and Black-Hole Properties: A Computational Benchmark*. GitHub.

References: Tangherlini (1963); Myers and Perry (1986); Emparan and Reall (2008); Emparan (2025).
