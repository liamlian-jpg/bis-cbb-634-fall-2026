"""Reproducible end-to-end sorting timings; plotting is a separate command."""

import argparse
import csv
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import statistics
import sys
import time
from zoneinfo import ZoneInfo

from parallel_sort import alg2, parallel_alg2


HERE = Path(__file__).resolve().parent
DEFAULT_SIZES = [round(10 ** (2 + i / 2)) for i in range(9)]
def configurations(workers):
    return [("serial", 1)] + [(f"parallel_{p}", p) for p in sorted(workers)]


def timestamp():
    return datetime.now(ZoneInfo("America/New_York")).isoformat()


def source_hash():
    return hashlib.sha256((HERE / "parallel_sort.py").read_bytes()).hexdigest()


def sort(data, workers):
    return alg2(data) if workers == 1 else parallel_alg2(data, workers)


def summarize(rows):
    summary = []
    configs = sorted({(row["algorithm"], int(row["workers"])) for row in rows},
                     key=lambda item: item[1])
    for n in sorted({int(row["n"]) for row in rows}):
        groups = {}
        for name, workers in configs:
            times = [float(row["seconds"]) for row in rows
                     if int(row["n"]) == n and row["algorithm"] == name]
            q1, _, q3 = statistics.quantiles(times, n=4, method="inclusive")
            groups[name] = (workers, times, statistics.median(times), q1, q3)
        serial = groups["serial"][2]
        for name, (workers, times, median, q1, q3) in groups.items():
            summary.append(dict(n=n, algorithm=name, workers=workers,
                                repeats=len(times), median_seconds=median,
                                q1_seconds=q1, q3_seconds=q3,
                                min_seconds=min(times), max_seconds=max(times),
                                time_ratio=median / serial, speedup=serial / median))
    return summary


def write_csv(path, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run(args):
    all_configs = configurations(args.workers)
    prefix = HERE / args.prefix
    outputs = [Path(str(prefix) + suffix) for suffix in
               ("-runs.csv", "-summary.csv", "-environment.json")]
    if any(path.exists() for path in outputs):
        raise FileExistsError("Use a new --prefix to preserve existing measurements.")
    meta = dict(started=timestamp(), python=sys.version, executable=sys.executable,
                platform=platform.platform(), machine=platform.machine(),
                logical_cpu_count=os.cpu_count(), start_method="spawn",
                sizes=args.sizes, repeats=args.repeats, seed=args.seed,
                worker_counts=sorted(args.workers), cutoff=2,
                input_distribution="uniform integers from -1,000,000,000 to 1,000,000,000 inclusive",
                timed_scope="entire sorting call including pool creation/cleanup, splitting, IPC and merging",
                excluded="input generation/copying, sorted reference, validation, output and plotting",
                summary="median and inclusive sample quartiles; speedup is ratio of medians",
                parallel_sort_sha256=source_hash(),
                benchmark_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    outputs[2].write_text(json.dumps(meta, indent=2) + "\n")

    warmup = [random.Random(args.seed + i).randrange(-10000, 10001)
              for i in range(10000)]
    expected = sorted(warmup)
    for _, workers in all_configs:
        assert sort(warmup.copy(), workers) == expected
    del warmup, expected

    rows = []
    with outputs[0].open("w", newline="") as handle:
        fields = ["n", "repeat", "data_seed", "order", "algorithm", "workers",
                  "seconds", "correct"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for n in args.sizes:
            for repeat in range(1, args.repeats + 1):
                data_seed = args.seed + n * 1009 + repeat
                rng = random.Random(data_seed)
                data = [rng.randrange(-10**9, 10**9 + 1) for _ in range(n)]
                expected = sorted(data)
                configs = all_configs.copy()
                random.Random(data_seed + 7919).shuffle(configs)
                for order, (name, workers) in enumerate(configs, start=1):
                    input_copy = data.copy()
                    start = time.perf_counter()
                    result = sort(input_copy, workers)
                    elapsed = time.perf_counter() - start
                    # Validation is mandatory and outside the timer.
                    if result != expected or input_copy != data:
                        raise AssertionError(f"Incorrect result or mutation: {n}, {name}")
                    row = dict(n=n, repeat=repeat, data_seed=data_seed, order=order,
                               algorithm=name, workers=workers,
                               seconds=elapsed, correct=True)
                    writer.writerow(row)
                    handle.flush()
                    rows.append(row)
                    del result, input_copy
                del data, expected
            recent = summarize([row for row in rows if row["n"] == n])
            print(f"n={n:,}: " + "; ".join(
                f"{r['algorithm']} {r['median_seconds']:.6f}s ({r['speedup']:.3f}x)"
                for r in recent), flush=True)
    write_csv(outputs[1], summarize(rows))
    assert source_hash() == meta["parallel_sort_sha256"]
    meta.update(finished=timestamp(), verified_timed_results=len(rows),
                algorithm_source_unchanged=True)
    outputs[2].write_text(json.dumps(meta, indent=2) + "\n")


def plot(args):
    # Imported only here: spawned timing workers never load plotting libraries.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import ScalarFormatter

    prefix = HERE / args.prefix
    with Path(str(prefix) + "-runs.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    summary = summarize(rows)
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False,
                         "axes.spines.right": False, "svg.fonttype": "none"})
    configs = sorted({(r["algorithm"], r["workers"]) for r in summary},
                     key=lambda item: item[1])
    palette = ["#334155", "#007f86", "#b45309", "#7c3aed", "#be185d"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), layout="constrained")
    for index, (name, workers) in enumerate(configs):
        color = palette[index % len(palette)]
        label = "Serial alg2 (1 process)" if workers == 1 else f"Parallel ({workers} workers)"
        group = [r for r in summary if r["algorithm"] == name]
        x = [r["n"] for r in group]
        y = [r["median_seconds"] for r in group]
        err = [[r["median_seconds"] - r["q1_seconds"] for r in group],
               [r["q3_seconds"] - r["median_seconds"] for r in group]]
        axes[0].errorbar(x, y, yerr=err, marker="o", markersize=4,
                         capsize=3, color=color, label=label)
        if name != "serial":
            axes[1].plot(x, [r["speedup"] for r in group], marker="o",
                         markersize=4, color=color, label=label)
    axes[0].set(xscale="log", yscale="log", xlabel="Input size n (elements)",
                ylabel="Wall-clock sorting time (seconds)", title="End-to-end runtime (log-log)")
    axes[0].legend(loc="upper left", fontsize=9)
    for level, label, style in [(1, "Break-even (1x)", ":"),
                               (1 / 0.7, "70% time target (1.43x)", "--"),
                               (2, "Extra credit requires >2x", "-.")]:
        axes[1].axhline(level, color="#64748b", linestyle=style, linewidth=1)
        axes[1].text(0.02, level, label, transform=axes[1].get_yaxis_transform(),
                     va="bottom", fontsize=9, color="#475569")
    axes[1].set(xscale="log", xlabel="Input size n (elements)",
                ylabel="Speedup = serial median / parallel median",
                title="Observed speedup", ylim=(0, max(2.3, max(r['speedup'] for r in summary)*1.12)))
    axes[1].yaxis.set_major_formatter(ScalarFormatter())
    for ax in axes:
        ax.grid(True, which="major", alpha=0.2)
    repeat_counts = sorted({r["repeats"] for r in summary})
    repeats_label = ", ".join(map(str, repeat_counts))
    fig.suptitle(f"Parallel Merge Sort | {repeats_label} repeats per size and configuration", fontsize=15)
    fig.get_layout_engine().set(rect=(0, 0.07, 1, 0.95))
    fig.text(0.5, 0.02,
             "Medians; runtime error bars show the interquartile range. "
             "Fresh spawn pool per call; generation and checks excluded.",
             ha="center", fontsize=10, color="#475569")
    for extension in ("png", "svg"):
        fig.savefig(str(prefix) + "-scaling." + extension, dpi=180)
    plt.close(fig)
    print(f"Saved {prefix.name}-scaling.png and .svg")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plot-only", action="store_true")
    parser.add_argument("--prefix", default="benchmark")
    parser.add_argument("--sizes", nargs="+", type=int, default=DEFAULT_SIZES)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--seed", type=int, default=634)
    parser.add_argument("--workers", nargs="+", type=int, default=[2, 4])
    args = parser.parse_args()
    if args.repeats < 2 or any(n < 2 for n in args.sizes):
        parser.error("Use at least two repeats and sizes >= 2.")
    if len(set(args.sizes)) != len(args.sizes):
        parser.error("Sizes must be unique.")
    if any(p < 2 for p in args.workers) or len(set(args.workers)) != len(args.workers):
        parser.error("Worker counts must be unique integers >= 2; serial is always included.")
    plot(args) if args.plot_only else run(args)
