# Methodology Passport Card

## 1. Project Information

| Field | Value |
|---|---|
| Title | Multidimensional Spacetime and the Theory of Relativity: A Computational Benchmark of Black-Hole Properties in D-Dimensional Spacetime |
| Authors | Talgat Bakytuly, Dauletuly Amirlan |
| GitHub repository | https://github.com/Tako1337/spacetime-dimensions-bh |

## 2. Research Type

Mixed-Methods.

- Qualitative part (RQ1, RQ2): literature synthesis. These questions are descriptive and need no measurements (see Task 1).
- Quantitative part (RQ3): computational experiment based on exact analytic solutions (Tangherlini, Myers-Perry).

Justification: there are no direct observations of extra dimensions, so RQ3 is tested by computing theoretical models under fixed conditions.

## 3. Hypotheses

- **H0:** for every D from 5 to 11, black-hole properties do not differ qualitatively from D = 4: the solution has an upper bound on spin (the horizon disappears for χ ≤ χ_cap) and stable circular orbits exist.
- **H1:** for at least one D ≥ 5, the properties differ qualitatively from D = 4: a horizon exists at χ = χ_cap = 4, whereas in D = 4 it disappears for χ > 0.5.

H0 is rejected if B(D) = 1 for at least one D ≥ 5 while B(4) = 0, and all guardrail metrics pass.

## 4. Variable Matrix

### Independent variables

| Variable | Values |
|---|---|
| Spacetime dimension D | 4, 5, 6, 7, 8, 9, 10, 11 |
| Spin χ = a / μ^(1/(D−3)) | 41 values on [0, 4] |
| Solution family | Schwarzschild-Tangherlini; Myers-Perry (single spin) |

### Dependent variables

| Variable | Units |
|---|---|
| Horizon existence | 0/1 |
| Horizon radius r_h | G = c = 1, M = 1 |
| Ratio r_ph / r_h | dimensionless |
| Stable circular orbits, r_ISCO | bool / length |
| Horizon area A, entropy S = A/4 | G = c = ħ = 1 |
| Hawking temperature T_H | G = c = ħ = k_B = 1 |
| Maximum spin χ_max | dimensionless |
| Latency per cell | ms (median of 30 runs) |
| Peak memory | MB |

### Controlled variables

| Factor | Value |
|---|---|
| Units | G = c = ħ = k_B = 1 |
| Mass | M = 1 |
| Number of nonzero angular momenta | 1 |
| Charge, Λ, matter fields | none (vacuum) |
| Software | Python 3.13, NumPy 2.5.3, SciPy 1.18.1, PyYAML 6.0.3 |
| Root-finding tolerance | xtol = rtol = 1e-14 (`brentq`) |
| Spin grid | linspace(0, 4, 41) |
| Repeats / warm-up | 30 / 3 |
| Environment | Docker python:3.13-slim, exact dependency pins |
| Input data | deterministic grid from config.yaml |

## 5. Metrics and Baseline

### Primary metric

B(D): equals 1 if a horizon exists at χ = χ_cap = 4, otherwise 0. The presence of a spin bound separates D = 4 (χ ≤ 0.5) and D = 5 (χ < 1) from D ≥ 6, where no bound exists. This directly tests RQ3.

### Secondary metrics

r_ph / r_h; stable circular orbits; T_H; entropy; χ_max; latency; peak memory.

### Guardrail metrics

| Metric | Threshold |
|---|---|
| Root residual of the horizon equation | ≤ 1e-10 |
| Smarr relation error (D−3)M = (D−2)(TS + ΩJ) | ≤ 1e-9 |
| D = 4 reproduction (r_h = 2M, Kerr bound a = M) | tolerance 1e-9 |
| Computation time per cell | ≤ 1000 ms |

If any threshold is violated, the conclusion on the hypothesis is invalid and the script returns a nonzero exit code.

### Baseline

D = 4: Schwarzschild (χ = 0) and Kerr (χ ≤ 0.5) solutions, i.e. standard general relativity. Checked in unit tests: r_h = 2M, r_ISCO = 6M, r_ph/r_h = 3/2, T = 1/(8πM).

## 6. Pipeline Test Results

| D | B(D) | χ_max | r_ph/r_h | Stable orbits |
|---|---|---|---|---|
| 4 | 0 | 0.5 | 1.500 | yes |
| 5 | 0 | 1.0 | 1.414 | no |
| 6 | 1 | ≥ 4 | 1.357 | no |
| 7 | 1 | ≥ 4 | 1.316 | no |
| 8–11 | 1 | ≥ 4 | 1.285–1.223 | no |

All guardrails pass. χ_max for D = 4 and 5 is determined to the grid step. Full analysis is planned for Week 7.

## 7. Limitations

- The experiment checks known analytic results and gives no observational evidence for extra dimensions.
- Stability of ultraspinning horizons (D ≥ 6) is not tested.
- Only vacuum solutions with a single angular momentum are considered; black rings and other horizon topologies are covered in the literature part only.
