"""Explicit Euler integration for Exercise 1 of BIS/CBB 634."""

import numpy as np
import pandas as pd


def simulate_sir(S0, I0, R0, beta, gamma, dt, t_max):
    """Return t, S, I, R through t_max, with a shortened final step if needed.

    Time is measured in days; beta and gamma have units of 1/day.
    R0 means the INITIAL REMOVED COUNT, not the reproduction number.
    Fractional counts are retained for this deterministic ODE model.
    This function integrates a fixed horizon; callers check I < 1 afterward.
    """
    parameters = np.asarray([S0, I0, R0, beta, gamma, dt, t_max], dtype=float)
    if not np.isfinite(parameters).all():
        raise ValueError("All inputs must be finite numbers.")
    S, I, R, beta, gamma, dt, t_max = parameters
    if min(S, I, R, beta, gamma, t_max) < 0 or dt <= 0:
        raise ValueError("Counts, rates, and t_max must be nonnegative; dt > 0.")
    N = S + I + R
    if not np.isfinite(N) or N <= 0:
        raise ValueError("Total population must be finite and positive.")

    rows = [(0.0, S, I, R)]
    n_steps = int(np.ceil(t_max / dt))
    t = 0.0
    for step in range(1, n_steps + 1):
        t_next = min(step * dt, t_max)
        h = t_next - t
        if h <= 0:
            break

        # Both flows use the same old state: this is Explicit Euler.
        new_infections = beta * S * I / N * h
        new_removals = gamma * I * h
        S_next = S - new_infections
        I_next = I + new_infections - new_removals
        R_next = R + new_removals

        if not np.isfinite([S_next, I_next, R_next]).all():
            raise ValueError("Nonfinite Euler state; try a smaller dt.")
        if min(S_next, I_next, R_next) < 0:
            raise ValueError(
                f"Negative compartment at day {t_next:g}; try a smaller dt."
            )
        S, I, R = S_next, I_next, R_next
        t = t_next
        rows.append((t, S, I, R))

    return pd.DataFrame(rows, columns=["t", "S", "I", "R"])
