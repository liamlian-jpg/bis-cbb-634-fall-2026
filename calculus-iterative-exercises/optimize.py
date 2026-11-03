"""Bounded two-dose gradient descent. Default execution replays the saved API scores."""
import argparse
import csv
import json
import math
import time
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parent
ENDPOINT = "https://ramcdougal.com/cgi-bin/error_function.py"
LEDGER = ROOT / "api_scores.csv"
STARTS = [(0.4, 0.2), (0.8, 0.8), (0.15, 0.85), (0.85, 0.15)]
BUDGET = 150
H = 0.00001
TOL = 0.0001


class Scores:
    def __init__(self, live):
        self.live = live
        self.values = {}
        self.attempts = 0
        if LEDGER.exists():
            with LEDGER.open() as stream:
                for row in csv.DictReader(stream):
                    self.attempts += 1
                    if row["score"]:
                        self.values[float(row["a"]), float(row["b"])] = float(row["score"])
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "CBB634-Studio6/1.0 (educational optimization)"
        self.last_request = 0.0
        self.used = set()

    def __call__(self, point):
        key = tuple(round(float(x), 10) for x in point)
        if any(not (0 <= x <= 1) for x in key):
            raise ValueError("Dose outside [0, 1]")
        self.used.add(key)
        if key in self.values:
            return self.values[key]
        if not self.live:
            raise RuntimeError(f"No recorded score at {key}. Use --live to query.")
        if self.attempts >= BUDGET:
            raise RuntimeError("Shared query budget reached. Scores saved for inspection.")
        time.sleep(max(0.0, 1.0 - (time.monotonic() - self.last_request)))
        self.attempts += 1
        self.last_request = time.monotonic()
        value = None
        try:
            response = self.session.get(ENDPOINT, params=dict(zip(("a", "b"), key)),
                                        timeout=15, allow_redirects=False)
            response.raise_for_status()
            candidate = float(response.text.strip())
            if not math.isfinite(candidate):
                raise ValueError("Nonfinite API score")
            value = candidate
        finally:
            # A failed attempt also consumes budget. An empty score can be retried.
            with LEDGER.open("a", newline="") as stream:
                writer = csv.writer(stream, lineterminator="\n")
                if stream.tell() == 0:
                    writer.writerow(["a", "b", "score"])
                writer.writerow([*key, value])
        self.values[key] = value
        return value


def gradient(score, x, value):
    derivatives = []
    for axis in range(2):
        probe = x.copy()
        delta = H if x[axis] + H <= 1 else -H
        probe[axis] += delta
        derivatives.append((score(probe) - value) / delta)
    return np.array(derivatives)


def descend(score, start):
    x = np.array(start, dtype=float)
    value = score(x)
    path = [[*x, value]]
    step = 0.15
    previous_x = previous_grad = None
    for _ in range(40):
        grad = gradient(score, x, value)
        residual = np.linalg.norm(x - np.clip(x - grad, 0, 1))
        if residual <= TOL:
            reason = "projected gradient tolerance"
            break
        if previous_x is not None:
            dx, dg = x - previous_x, grad - previous_grad
            curvature = dx @ dg
            if curvature > 0:
                step = np.clip((dx @ dx) / curvature, 0.005, 2.0)
        for _ in range(18):
            trial = np.clip(x - step * grad, 0, 1)
            trial_value = score(trial)
            if trial_value < value and trial_value <= value + 0.0001 * (grad @ (trial - x)):
                break
            step *= 0.5
        else:
            reason = "line search stalled"
            break
        previous_x, previous_grad = x, grad
        x, value = trial, trial_value
        path.append([*x, value])
    else:
        reason = "iteration cap"
        grad = gradient(score, x, value)
        residual = np.linalg.norm(x - np.clip(x - grad, 0, 1))
    return {"start": list(start), "end": x.tolist(), "score": value,
            "projected_gradient_norm": float(residual), "stop": reason, "path": path}


def main(live):
    scores = Scores(live)
    runs = []
    for start in STARTS:
        before = len(scores.used)
        run = descend(scores, start)
        run["additional_distinct_points"] = len(scores.used) - before
        runs.append(run)
        print(start, run["end"], run["score"], run["stop"], len(scores.used), flush=True)
    report = {"endpoint": ENDPOINT, "budget": BUDGET, "distinct_points": len(scores.used),
              "recorded_request_attempts": scores.attempts,
              "finite_difference_step": H, "tolerance": TOL, "runs": runs}
    (ROOT / "optimization.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="fetch missing scores with a 1 s delay")
    main(parser.parse_args().live)
