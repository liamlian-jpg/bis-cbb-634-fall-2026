"""Reproduce the SIR baseline, step-size comparison, and sensitivity figures."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from sir import simulate_sir

ROOT = Path(__file__).resolve().parent
N = 134_023
BETA, GAMMA = 0.35, 0.10
STEPS = [2, 0.5, 0.1, 0.05, 0.01]
REFERENCE_DT = 0.005


def epidemic(beta, gamma, dt):
    horizon = 256
    while horizon <= 2048:
        data = simulate_sir(N - 1, 1, 0, beta, gamma, dt, horizon)
        clear = np.flatnonzero(data.I.to_numpy() < 1)
        if len(clear):
            return data.iloc[:clear[0] + 1].copy()
        horizon *= 2
    raise RuntimeError("Clearance not reached by day 2048.")


def peak(data):
    row = data.loc[data.I.idxmax()]
    return row.t, row.I


def save(fig, name):
    fig.savefig(ROOT / name, dpi=145, bbox_inches="tight")
    plt.close(fig)


def curve_figure(curves, baseline, step):
    fig, ax = plt.subplots(figsize=(8, 4.5), layout="constrained")
    day, infected = peak(baseline)
    ax.fill_between(baseline.t, baseline.I, alpha=0.13, color="#087d79")
    ax.plot(baseline.t, baseline.I, color="#087d79", lw=2)
    ax.scatter(day, infected, color="#09485b", zorder=3)
    ax.annotate(f"Day {day:.2f}  |  {infected:,.0f} infectious",
                (day, infected), xytext=(14, -6), textcoords="offset points")
    ax.set(title=f"New Haven SIR scenario  ·  Euler step {step:g} days",
           xlabel="Days since introduction", ylabel="Infectious people, I(t)", ylim=(0, infected*1.12))
    ax.grid(axis="y", alpha=.2)
    save(fig, "baseline.png")

    fig, ax = plt.subplots(figsize=(8, 4.5), layout="constrained")
    for dt, frame in curves.items():
        ax.plot(frame.t, frame.I, label=f"{dt:g}", lw=1.6)
    ax.set(title="Time-step comparison at fixed transmission and removal rates",
           xlabel="Days since introduction", ylabel="Infectious people, I(t)")
    ax.legend(title="Step (days)", frameon=False)
    ax.grid(axis="y", alpha=.2)
    save(fig, "step-comparison.png")


def heatmap(grid, metric, title, unit, filename, cmap):
    pivot = grid.pivot(index="gamma", columns="beta", values=metric)
    fig, ax = plt.subplots(figsize=(7, 4.8), layout="constrained")
    mesh = ax.pcolormesh(pivot.columns, pivot.index, pivot, shading="nearest", cmap=cmap)
    fig.colorbar(mesh, ax=ax, label=unit)
    ax.scatter([BETA], [GAMMA], marker="*", s=120, color="white",
               edgecolors="black", label="Baseline")
    ax.set(title=title, xlabel="Transmission rate β (per day)\n★  Baseline (β = 0.35, γ = 0.10)",
           ylabel="Removal rate γ (per day)")
    save(fig, filename)


def main():
    reference = epidemic(BETA, GAMMA, REFERENCE_DT)
    ref_t, ref_i = peak(reference)
    curves = {dt: epidemic(BETA, GAMMA, dt) for dt in STEPS}
    rows = []
    for dt, curve in curves.items():
        t, i = peak(curve)
        common = reference[reference.t <= curve.t.iloc[-1]]
        error = np.abs(np.interp(common.t, curve.t, curve.I) - common.I).max()
        rows.append(dict(dt=dt, peak_day=t, peak_infectious=i, clearance_day=curve.t.iloc[-1],
                         time_error_days=abs(t-ref_t), relative_peak_error=abs(i-ref_i)/ref_i,
                         max_curve_error_over_ref_peak=error/ref_i))
    checks = pd.DataFrame(rows)
    checks.to_csv(ROOT / "step-validation.csv", index=False)
    eligible = checks[(checks.time_error_days <= .25) & (checks.relative_peak_error <= .005)
                      & (checks.max_curve_error_over_ref_peak <= .01)]
    step = eligible.dt.max()
    if pd.isna(step):
        raise ValueError("No candidate step passed the baseline tolerances.")
    baseline = curves[step]
    # Keep a compact table of full days plus the model peak and clearance.
    daily = np.isclose(baseline.t % 1, 0, rtol=0, atol=1e-10)
    keep = daily | (baseline.index == baseline.I.idxmax()) | (baseline.index == baseline.index[-1])
    baseline.loc[keep].to_csv(ROOT / "baseline.csv", index=False)
    curve_figure(curves, baseline, step)

    rows = []
    for beta in np.round(np.linspace(.20, .50, 13), 4):
        for gamma in np.round(np.linspace(.06, .14, 9), 4):
            result = epidemic(beta, gamma, step)
            t, i = peak(result)
            rows.append(dict(beta=beta, gamma=gamma, dt=step, peak_day=t, peak_infectious=i))
    grid = pd.DataFrame(rows)
    grid.to_csv(ROOT / "sensitivity.csv", index=False)
    heatmap(grid, "peak_day", "Time to peak infection", "Day of peak", "peak-day.png", "viridis")
    heatmap(grid, "peak_infectious", "Infectious population at peak", "Concurrent infectious people",
            "peak-size.png", "magma")
    print(checks.to_string(index=False))
    print("Reference peak:", ref_t, ref_i, "Selected step:", step)
    print("Baseline clearance:", baseline.iloc[-1].to_dict())
    print("Grid extrema:", grid[["peak_day", "peak_infectious"]].agg(["min", "max"]))


if __name__ == "__main__":
    main()
