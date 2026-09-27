from __future__ import annotations

import math
from typing import Any


def _round(value: float | None, digits: int = 6) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return round(value, digits)


def _linear_regression(points: list[tuple[float, float]]) -> tuple[float, float, float]:
    n = len(points)
    if n < 2:
        raise ValueError("At least two points are required for regression")
    sx = sum(x for x, _ in points)
    sy = sum(y for _, y in points)
    sxx = sum(x * x for x, _ in points)
    sxy = sum(x * y for x, y in points)
    denominator = n * sxx - sx * sx
    if abs(denominator) < 1e-15:
        raise ValueError("Time values are not suitable for regression")
    slope = (n * sxy - sx * sy) / denominator
    intercept = (sy - slope * sx) / n
    mean_y = sy / n
    ss_tot = sum((y - mean_y) ** 2 for _, y in points)
    ss_res = sum((y - (intercept + slope * x)) ** 2 for x, y in points)
    r_squared = 1.0 if ss_tot <= 1e-15 else max(0.0, 1.0 - ss_res / ss_tot)
    return slope, intercept, r_squared


def noncompartmental_analysis(
    observations: list[dict[str, float]],
    *,
    terminal_points: int = 3,
    dose: float | None = None,
    route: str = "other",
    time_unit: str = "h",
    concentration_unit: str = "mg/L",
    dose_unit: str = "mg",
) -> dict[str, Any]:
    if len(observations) < 3:
        raise ValueError("At least three concentration-time observations are required")

    pairs = sorted(
        [(float(row["time"]), float(row["concentration"])) for row in observations],
        key=lambda item: item[0],
    )
    if any(t < 0 or c < 0 for t, c in pairs):
        raise ValueError("Time and concentration values must be non-negative")
    if any(pairs[i][0] <= pairs[i - 1][0] for i in range(1, len(pairs))):
        raise ValueError("Time values must be unique")
    if not any(c > 0 for _, c in pairs):
        raise ValueError("At least one concentration must be greater than zero")

    cmax = max(c for _, c in pairs)
    tmax = next(t for t, c in pairs if c == cmax)
    clast_time, clast = next((t, c) for t, c in reversed(pairs) if c > 0)

    auc_last = 0.0
    aumc_last = 0.0
    for (t1, c1), (t2, c2) in zip(pairs, pairs[1:]):
        dt = t2 - t1
        auc_last += dt * (c1 + c2) / 2.0
        aumc_last += dt * ((t1 * c1) + (t2 * c2)) / 2.0

    positive = [(t, c) for t, c in pairs if c > 0]
    selected = positive[-max(3, min(int(terminal_points), 8)) :]
    lambda_z = None
    half_life = None
    terminal_r2 = None
    auc_extra = None
    auc_inf = None
    pct_extrapolated = None
    clearance = None
    volume_z = None
    mrt_last = (aumc_last / auc_last) if auc_last > 0 else None

    if len(selected) >= 3:
        regression_points = [(t, math.log(c)) for t, c in selected]
        slope, _intercept, r_squared = _linear_regression(regression_points)
        if slope < 0:
            lambda_z = -slope
            half_life = math.log(2.0) / lambda_z
            terminal_r2 = r_squared
            auc_extra = clast / lambda_z
            auc_inf = auc_last + auc_extra
            pct_extrapolated = (auc_extra / auc_inf * 100.0) if auc_inf > 0 else None
            if dose and dose > 0 and route == "iv" and auc_inf > 0:
                clearance = dose / auc_inf
                volume_z = clearance / lambda_z

    warnings: list[str] = []
    if lambda_z is None:
        warnings.append("Terminal half-life could not be estimated from a declining log-linear terminal phase.")
    elif terminal_r2 is not None and terminal_r2 < 0.8:
        warnings.append("Terminal regression fit is weak (R² < 0.80); interpret half-life and AUC∞ cautiously.")
    if pct_extrapolated is not None and pct_extrapolated > 20:
        warnings.append("More than 20% of AUC∞ is extrapolated beyond the last measured concentration.")
    if pairs[0][0] > 0:
        warnings.append("The first observation occurs after time zero; AUC before the first sample is not represented.")

    return {
        "method": "linear_trapezoidal_nca",
        "observations": [{"time": t, "concentration": c} for t, c in pairs],
        "metrics": {
            "cmax": _round(cmax),
            "tmax": _round(tmax),
            "clast": _round(clast),
            "tlast": _round(clast_time),
            "auc_0_last": _round(auc_last),
            "auc_extra": _round(auc_extra),
            "auc_0_inf": _round(auc_inf),
            "percent_auc_extrapolated": _round(pct_extrapolated, 3),
            "lambda_z": _round(lambda_z),
            "terminal_half_life": _round(half_life),
            "terminal_r_squared": _round(terminal_r2, 4),
            "mrt_0_last": _round(mrt_last),
            "clearance": _round(clearance),
            "volume_z": _round(volume_z),
        },
        "units": {
            "time": time_unit,
            "concentration": concentration_unit,
            "dose": dose_unit,
            "auc": f"{concentration_unit}·{time_unit}",
            "lambda_z": f"1/{time_unit}",
            "half_life": time_unit,
            "clearance": f"{dose_unit}/({concentration_unit}·{time_unit})",
            "volume_z": f"{dose_unit}/{concentration_unit}",
        },
        "terminal_points_used": len(selected),
        "warnings": warnings,
        "research_notice": "Research/education calculation only. Verify units, sampling assumptions and model suitability before scientific or clinical interpretation.",
    }


def one_compartment_simulation(
    *,
    model: str,
    dose: float,
    volume: float,
    elimination_half_life: float,
    duration: float,
    points: int = 101,
    bioavailability: float = 1.0,
    absorption_rate: float | None = None,
    time_unit: str = "h",
    dose_unit: str = "mg",
    volume_unit: str = "L",
) -> dict[str, Any]:
    if dose <= 0 or volume <= 0 or elimination_half_life <= 0 or duration <= 0:
        raise ValueError("Dose, volume, half-life and duration must be greater than zero")
    if points < 20 or points > 500:
        raise ValueError("Simulation points must be between 20 and 500")
    if not (0 < bioavailability <= 1):
        raise ValueError("Bioavailability must be greater than 0 and at most 1")

    ke = math.log(2.0) / elimination_half_life
    step = duration / (points - 1)
    output: list[dict[str, float]] = []

    if model == "one_compartment_iv_bolus":
        for index in range(points):
            t = step * index
            c = (dose / volume) * math.exp(-ke * t)
            output.append({"time": _round(t) or 0.0, "concentration": _round(c) or 0.0})
    elif model == "one_compartment_oral":
        if absorption_rate is None or absorption_rate <= 0:
            raise ValueError("A positive absorption rate is required for the oral model")
        if abs(absorption_rate - ke) < 1e-9:
            raise ValueError("Absorption rate must differ from the elimination rate")
        factor = bioavailability * dose * absorption_rate / (volume * (absorption_rate - ke))
        for index in range(points):
            t = step * index
            c = factor * (math.exp(-ke * t) - math.exp(-absorption_rate * t))
            output.append({"time": _round(t) or 0.0, "concentration": _round(max(c, 0.0)) or 0.0})
    else:
        raise ValueError("Unsupported one-compartment model")

    cmax = max(row["concentration"] for row in output)
    tmax = next(row["time"] for row in output if row["concentration"] == cmax)
    auc = 0.0
    for left, right in zip(output, output[1:]):
        auc += (right["time"] - left["time"]) * (left["concentration"] + right["concentration"]) / 2.0

    concentration_unit = f"{dose_unit}/{volume_unit}"
    return {
        "method": model,
        "parameters": {
            "dose": dose,
            "volume": volume,
            "elimination_half_life": elimination_half_life,
            "elimination_rate": _round(ke),
            "bioavailability": bioavailability,
            "absorption_rate": absorption_rate,
            "duration": duration,
            "points": points,
        },
        "curve": output,
        "metrics": {
            "cmax_simulated": _round(cmax),
            "tmax_simulated": _round(tmax),
            "auc_0_duration": _round(auc),
        },
        "units": {
            "time": time_unit,
            "dose": dose_unit,
            "volume": volume_unit,
            "concentration": concentration_unit,
            "auc": f"{concentration_unit}·{time_unit}",
            "rate": f"1/{time_unit}",
        },
        "research_notice": "One-compartment educational simulation only. It does not select, recommend or validate a patient dose.",
    }
