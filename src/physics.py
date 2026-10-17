import math

import numpy as np
from scipy.optimize import brentq
from scipy.special import gamma


def omega(D):
    return 2.0 * math.pi ** ((D - 1) / 2.0) / gamma((D - 1) / 2.0)


def mu_from_mass(D, M):
    return 16.0 * math.pi * M / ((D - 2) * omega(D))


def length_scale(D, mu):
    return mu ** (1.0 / (D - 3))


def circular_orbit_stability(D, mu, n_grid=20000, r_span=1e3):
    n = D - 3
    r_h = mu ** (1.0 / n)
    r_ph = r_h * ((n + 2) / 2.0) ** (1.0 / n)
    r = r_ph * np.geomspace(1.0 + 1e-6, r_span, n_grid)
    l2 = n * mu * r ** (2 - n) / (2.0 - (n + 2) * mu * r ** (-n))
    stable = np.diff(l2) > 0
    if not stable.any():
        return False, float("nan")
    return True, float(r[np.argmax(stable)])


def tangherlini(D, M=1.0):
    mu = mu_from_mass(D, M)
    n = D - 3
    r_h = mu ** (1.0 / n)
    r_ph = r_h * ((n + 2) / 2.0) ** (1.0 / n)
    area = omega(D) * r_h ** (D - 2)
    temperature = n / (4.0 * math.pi * r_h)
    has_stable, r_isco = circular_orbit_stability(D, mu)
    return {
        "horizon_exists": True,
        "mu": mu,
        "r_h": r_h,
        "r_ph": r_ph,
        "r_ph_over_r_h": r_ph / r_h,
        "area": area,
        "entropy": area / 4.0,
        "temperature": temperature,
        "has_stable_orbit": has_stable,
        "r_isco": r_isco,
        "residual": 0.0,
        "smarr_rel_err": abs(n * M - (D - 2) * temperature * area / 4.0) / (n * M),
    }


def myers_perry(D, chi, M=1.0):
    mu = mu_from_mass(D, M)
    scale = length_scale(D, mu)
    a = chi * scale
    J = 2.0 * M * a / (D - 2)

    def g(r):
        return r ** (D - 5) * (r * r + a * a) - mu

    lo = max(a, 1e-9 * scale) if D == 4 else 1e-9 * scale
    hi = scale * (1.0 + 1e-6)
    if g(lo) >= 0.0:
        return {"horizon_exists": False, "mu": mu, "J": J, "a": a}
    r_h = brentq(g, lo, hi, xtol=1e-14, rtol=1e-14, maxiter=500)
    area = omega(D) * (r_h**2 + a * a) * r_h ** (D - 4)
    temperature = ((D - 3) * r_h**2 + (D - 5) * a * a) / (
        4.0 * math.pi * r_h * (r_h**2 + a * a)
    )
    omega_h = a / (r_h**2 + a * a)
    smarr = abs((D - 3) * M - (D - 2) * (temperature * area / 4.0 + omega_h * J)) / (
        (D - 3) * M
    )
    return {
        "horizon_exists": True,
        "mu": mu,
        "a": a,
        "J": J,
        "j": J / M ** ((D - 2) / (D - 3)),
        "r_h": r_h,
        "area": area,
        "entropy": area / 4.0,
        "temperature": temperature,
        "omega_h": omega_h,
        "residual": abs(g(r_h)) / mu,
        "smarr_rel_err": smarr,
    }
