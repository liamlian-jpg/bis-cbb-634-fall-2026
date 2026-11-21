"""Diagnostic timings; preserve parallel_sort.py and the published benchmark.

Worker timestamps bracket alg2 after input deserialization and before result
serialization. perf_counter uses a common monotonic clock across processes on
this machine. A map interval is not separable into additive compute and IPC:
sorting and IPC overlap. The union of worker intervals measures wall time with
at least one worker inside alg2; its complement is exposed non-sort delay, not
pure IPC. Echo controls measure fresh-pool round trips without sorting.
"""

import argparse
import csv
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import platform
import random
import statistics
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from parallel_sort import alg2, merge_sorted, parallel_alg2

HERE = Path(__file__).resolve().parent
CLOCK = time.perf_counter


def worker_sort(block):
    start = CLOCK()
    cpu = time.process_time()
    result = alg2(block)
    cpu_seconds = time.process_time() - cpu
    end = CLOCK()
    return result, dict(pid=os.getpid(), n=len(block), start=start, end=end,
                        wall_seconds=end-start, cpu_seconds=cpu_seconds)


def echo(block):
    return block


def interval_union(intervals):
    start, end = sorted(intervals)[0]
    total = 0.0
    for a, b in sorted(intervals)[1:]:
        if a > end:
            total += end-start
            start, end = a, b
        else:
            end = max(end, b)
    return total + end-start


def profiled(data, workers, echo_only=False):
    start = CLOCK()
    block, extra = divmod(len(data), workers)
    chunks, offset = [], 0
    for i in range(workers):
        end = offset + block + (i < extra)
        chunks.append(data[offset:end])
        offset = end
    split_end = CLOCK()
    # Match the original context-manager lifecycle (including terminate on exit).
    with mp.get_context('spawn').Pool(processes=workers) as pool:
        pool_end = CLOCK()
        received = pool.map(echo if echo_only else worker_sort, chunks, chunksize=1)
        map_end = CLOCK()
    cleanup_end = CLOCK()
    if echo_only:
        result, tasks, rounds = received, [], []
    else:
        tasks = [item[1] for item in received]
        runs = [item[0] for item in received]
        del received
        merge_start = CLOCK()
        rounds = []
        while len(runs) > 1:
            round_start = CLOCK()
            count, elements = len(runs), 0
            next_runs = []
            for i in range(0, len(runs), 2):
                if i + 1 == len(runs):
                    next_runs.append(runs[i])
                else:
                    elements += len(runs[i]) + len(runs[i+1])
                    next_runs.append(merge_sorted(runs[i], runs[i+1]))
            runs = next_runs
            rounds.append(dict(input_runs=count, merged_elements=elements,
                               seconds=CLOCK()-round_start))
        result = runs[0]
    end = CLOCK()
    metrics = dict(split_seconds=split_end-start,
                   pool_construct_seconds=pool_end-split_end,
                   map_seconds=map_end-pool_end,
                   pool_cleanup_seconds=cleanup_end-map_end)
    if not echo_only:
        union = interval_union([(t['start'], t['end']) for t in tasks])
        first = min(t['start'] for t in tasks)
        last = max(t['end'] for t in tasks)
        assert pool_end <= first <= last <= map_end
        metrics.update(merge_seconds=end-merge_start,
                       unpack_seconds=merge_start-cleanup_end,
                       sort_union_seconds=union,
                       map_non_sort_seconds=(map_end-pool_end)-union,
                       initial_delay_seconds=first-pool_end,
                       final_return_seconds=map_end-last,
                       worker_max_seconds=max(t['wall_seconds'] for t in tasks),
                       worker_mean_seconds=statistics.mean(t['wall_seconds'] for t in tasks),
                       worker_sum_seconds=sum(t['wall_seconds'] for t in tasks))
    return result, metrics, tasks, rounds


def write_summary(prefix, rows):
    summary = []
    for mode in ('original', 'profile', 'echo'):
        for workers in (6, 8):
            group = [r for r in rows if r['mode'] == mode and r['workers'] == workers]
            for metric in group[0]['metrics']:
                values = [r['metrics'][metric] for r in group]
                q1, _, q3 = statistics.quantiles(values, n=4, method='inclusive')
                summary.append(dict(mode=mode, workers=workers, metric=metric,
                                    median=statistics.median(values), mean=statistics.mean(values),
                                    q1=q1, q3=q3, minimum=min(values), maximum=max(values)))
    with Path(str(prefix)+'-summary.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(summary)


def run(args):
    prefix = HERE / args.prefix
    output = Path(str(prefix)+'-runs.json')
    if output.exists() or Path(str(prefix)+'-summary.csv').exists():
        raise FileExistsError('Choose a new prefix to preserve previous measurements.')
    sources = {name: hashlib.sha256((HERE/name).read_bytes()).hexdigest()
               for name in ('parallel_sort.py', 'profile_phases.py')}
    meta = dict(started=datetime.now(ZoneInfo('America/New_York')).isoformat(),
                n=args.n, repeats=args.repeats, seed=args.seed, workers=[6,8],
                python=sys.version, platform=platform.platform(), cpu_count=os.cpu_count(),
                clock=str(time.get_clock_info('perf_counter')), source_sha256=sources,
                method='Paired inputs, randomized six-configuration order; fresh spawn pools; '
                'generation, copy, reference sorting and checks outside timers. '
                'Echo includes input/output serialization, IPC, scheduling and worker readiness; '
                'it is a control, not an additive phase of the sort. '
                'Pool construction returning does not imply all workers are ready. '
                'Instrumented stages are diagnostic; original calls control for instrumentation.')
    rows = []
    def save():
        output.write_text(json.dumps(dict(environment=meta, runs=rows), indent=2)+'\n')
    save()
    warm = [7, 2, 2, -1, 9, 0, 5, 4] * 1250
    for workers in (6, 8):
        assert parallel_alg2(warm, workers) == sorted(warm)
        result, _, _, _ = profiled(warm, workers)
        assert result == sorted(warm)
        returned, _, _, _ = profiled(warm, workers, True)
        assert [x for chunk in returned for x in chunk] == warm
    del result, returned, warm
    for repeat in range(1, args.repeats+1):
        seed = args.seed + args.n*1009 + repeat
        rng = random.Random(seed)
        data = [rng.randrange(-10**9, 10**9+1) for _ in range(args.n)]
        expected = sorted(data)
        configs = [(m, p) for m in ('original', 'profile', 'echo') for p in (6, 8)]
        random.Random(seed+7919).shuffle(configs)
        for order, (mode, workers) in enumerate(configs, 1):
            copied = data.copy()
            start = CLOCK()
            if mode == 'original':
                result = parallel_alg2(copied, workers)
                metrics, tasks, rounds = {}, [], []
            else:
                result, metrics, tasks, rounds = profiled(copied, workers, mode=='echo')
            metrics['total_seconds'] = CLOCK()-start
            if mode == 'echo':
                offset = 0
                for chunk in result:
                    assert chunk == data[offset:offset+len(chunk)]
                    offset += len(chunk)
                assert offset == args.n
            else:
                assert result == expected
            assert copied == data
            if mode == 'profile':
                keys = ['split_seconds','pool_construct_seconds','map_seconds',
                        'pool_cleanup_seconds','merge_seconds','unpack_seconds']
                metrics['other_seconds'] = metrics['total_seconds'] - sum(metrics[k] for k in keys)
                assert metrics['other_seconds'] >= 0
            rows.append(dict(repeat=repeat, seed=seed, order=order, mode=mode, workers=workers,
                             correct=True, metrics=metrics, tasks=tasks, merge_rounds=rounds))
            print(f"repeat={repeat} {mode} p={workers}: {metrics['total_seconds']:.3f}s", flush=True)
            del result, copied
            save()
        del data, expected
    for name, digest in sources.items():
        assert hashlib.sha256((HERE/name).read_bytes()).hexdigest() == digest
    meta.update(finished=datetime.now(ZoneInfo('America/New_York')).isoformat(),
                verified_runs=len(rows))
    save()
    write_summary(prefix, rows)


def plot(args):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    prefix = HERE / args.prefix
    payload = json.loads(Path(str(prefix)+'-runs.json').read_text())
    rows = payload['runs']
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5), layout='constrained')
    colors = ['#94a3b8','#d97706','#7c3aed','#0891b2','#64748b']
    labels = ['Split + pool construction', 'Map: exposed non-sort delay',
              'Map: at least one worker sorting', 'Coordinator merge', 'Cleanup + other']
    for x, p in enumerate((6,8)):
        group = [r['metrics'] for r in rows if r['mode']=='profile' and r['workers']==p]
        components = [statistics.mean(m['split_seconds']+m['pool_construct_seconds'] for m in group),
                      statistics.mean(m['map_non_sort_seconds'] for m in group),
                      statistics.mean(m['sort_union_seconds'] for m in group),
                      statistics.mean(m['merge_seconds'] for m in group),
                      statistics.mean(m['pool_cleanup_seconds']+m['unpack_seconds']+m['other_seconds'] for m in group)]
        bottom = 0
        for value, color, label in zip(components, colors, labels):
            axes[0].bar(x, value, bottom=bottom, color=color, label=label if x==0 else None)
            if value > .35:
                axes[0].text(x, bottom+value/2, f'{value:.2f}', ha='center', va='center', color='white')
            bottom += value
        axes[0].text(x, bottom+.12, f'{bottom:.2f}s', ha='center')
        for i, mode in enumerate(('original','profile','echo')):
            values = [r['metrics']['total_seconds' if mode!='echo' else 'map_seconds']
                      for r in rows if r['mode']==mode and r['workers']==p]
            pos = x + (i-1)*.22
            axes[1].scatter([pos]*len(values), values, color=colors[i+1], alpha=.5, s=25)
            axes[1].plot([pos-.07,pos+.07], [statistics.median(values)]*2, color=colors[i+1], lw=3,
                         label=('Original total','Profile total','Echo map control')[i] if x==0 else None)
    for ax in axes:
        ax.set_xticks([0,1], ['6 workers','8 workers'])
        ax.set_ylabel('Wall-clock seconds')
        ax.set_ylim(bottom=0)
        ax.spines[['top','right']].set_visible(False)
    axes[0].set_title('Instrumented phases (means; additive)')
    axes[1].set_title('Five trials and medians')
    axes[0].legend(loc='upper center', bbox_to_anchor=(.5,-.12), fontsize=8, frameon=False)
    axes[1].legend(loc='upper center', bbox_to_anchor=(.5,-.12), fontsize=9, frameon=False)
    fig.suptitle(f"Merge Sort phase diagnostics | n = {payload['environment']['n']:,}")
    for ext in ('png','svg'):
        fig.savefig(str(prefix)+'-phases.'+ext, dpi=180)
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--n', type=int, default=10_000_000)
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--seed', type=int, default=634)
    parser.add_argument('--prefix', default='profile-10m-68')
    parser.add_argument('--plot-only', action='store_true')
    args = parser.parse_args()
    if args.n < 8 or args.repeats < 2:
        parser.error('Use n >= 8 and repeats >= 2.')
    plot(args) if args.plot_only else run(args)
