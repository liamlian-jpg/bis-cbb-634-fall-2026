"""Plot a saved benchmark's speedup curve and paired-trial variability."""

import argparse
import csv
from pathlib import Path

from benchmark import summarize


def main(prefix):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path = Path(__file__).resolve().parent / prefix
    with Path(str(path) + "-runs.csv").open() as handle:
        raw = list(csv.DictReader(handle))
    summary = summarize(raw)
    sizes = sorted({int(row["n"]) for row in raw})
    workers = sorted({int(row["workers"]) for row in raw} - {1})
    repeats = sorted({int(row["repeats"]) for row in summary})
    serial_trials = {(int(row["n"]), int(row["repeat"])): float(row["seconds"])
                     for row in raw if row["algorithm"] == "serial"}
    colors = ["#007f86", "#b45309", "#7c3aed", "#be185d"]
    markers = ["o", "s", "^", "D"]
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False,
                         "axes.spines.right": False, "svg.fonttype": "none"})
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.7))
    for index, worker in enumerate(workers):
        color = colors[index % len(colors)]
        marker = markers[index % len(markers)]
        group = sorted((r for r in summary if r["workers"] == worker),
                       key=lambda r: r["n"])
        trials = [r for r in raw if int(r["workers"]) == worker]
        x = [r["n"] for r in group]
        y = [r["speedup"] for r in group]
        trial_x = [int(r["n"]) for r in trials]
        trial_y = [serial_trials[(int(r["n"]), int(r["repeat"]))] /
                   float(r["seconds"]) for r in trials]
        for ax in axes:
            ax.scatter(trial_x, trial_y, s=20, color=color, alpha=0.18,
                       edgecolors="none", zorder=2)
            ax.plot(x, y, marker=marker, markersize=5, linewidth=1.8,
                    color=color, label=f"{worker} workers", zorder=3)

    for ax in axes:
        ax.set_xscale("log")
        ax.set_ylim(bottom=0)
        ax.set_xlabel("Input size n (elements, log scale)")
        ax.set_ylabel("Speedup (serial / parallel time)")
        ax.axhline(1, color="#64748b", linestyle="--", linewidth=1)
        ax.grid(True, which="major", alpha=0.22)
    axes[0].set_title("Full input range")
    axes[0].set_xlim(sizes[0] / 1.2, sizes[-1] * 1.2)
    zoom_min = max(sizes[0], sizes[-1] / 100)
    axes[1].set_title("Larger inputs (last two decades)")
    axes[1].set_xlim(zoom_min / 1.2, sizes[-1] * 1.2)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.suptitle(f"Merge Sort speedup | up to {sizes[-1]:,} elements", fontsize=16, y=0.98)
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.925),
               ncol=len(workers), frameon=False)
    fig.subplots_adjust(left=0.07, right=0.985, bottom=0.22, top=0.79, wspace=0.23)
    repeat_label = ", ".join(map(str, repeats))
    fig.text(0.5, 0.075,
             f"Lines: ratio of medians ({repeat_label} runs per size/configuration). "
             "Faint dots: paired trial speedups. Dashed line: break-even (1x).\n"
             "All points from one new experiment; process startup, transfer, and final merge are included.",
             ha="center", va="center", fontsize=10, color="#475569", linespacing=1.6)
    for extension in ("png", "svg"):
        fig.savefig(str(path) + "-speedup." + extension, dpi=180)
    plt.close(fig)
    print(f"Saved {path.name}-speedup.png and .svg")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", default="benchmark-large-2468")
    main(parser.parse_args().prefix)
