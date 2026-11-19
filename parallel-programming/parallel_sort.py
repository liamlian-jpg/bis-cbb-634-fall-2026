"""Parallel Merge Sort using a fixed spawn pool and coordinator-side merging."""

import multiprocessing as mp


def alg2(data):
    if len(data) <= 1:
        return data
    else:
        split = len(data) // 2
        left = iter(alg2(data[:split]))
        right = iter(alg2(data[split:]))
        result = []
        left_top = next(left)
        right_top = next(right)
        while True:
            if left_top < right_top:
                result.append(left_top)
                try:
                    left_top = next(left)
                except StopIteration:
                    return result + [right_top] + list(right)
            else:
                result.append(right_top)
                try:
                    right_top = next(right)
                except StopIteration:
                    return result + [left_top] + list(left)


def merge_sorted(left_data, right_data):
    """Merge two sorted lists using alg2's comparison and exhaustion logic."""
    if not left_data:
        return list(right_data)
    if not right_data:
        return list(left_data)
    left = iter(left_data)
    right = iter(right_data)
    result = []
    left_top = next(left)
    right_top = next(right)
    while True:
        if left_top < right_top:
            result.append(left_top)
            try:
                left_top = next(left)
            except StopIteration:
                return result + [right_top] + list(right)
        else:
            result.append(right_top)
            try:
                right_top = next(right)
            except StopIteration:
                return result + [left_top] + list(left)


def parallel_alg2(data, num_workers=2, *, min_parallel_size=2):
    """Sort a list of mutually comparable, picklable values without mutating it.

    Inputs shorter than min_parallel_size, trivial inputs, and one-worker
    requests use alg2 directly. The default cutoff only excludes trivial
    inputs; it is not a measured performance threshold. Each parallel call
    creates and closes its own pool. Call from a guarded script entry point.
    """
    if isinstance(num_workers, bool) or not isinstance(num_workers, int):
        raise TypeError("num_workers must be an integer")
    if num_workers < 1:
        raise ValueError("num_workers must be positive")
    if isinstance(min_parallel_size, bool) or not isinstance(min_parallel_size, int):
        raise TypeError("min_parallel_size must be an integer")
    if min_parallel_size < 0:
        raise ValueError("min_parallel_size must be nonnegative")

    n = len(data)
    if n <= 1 or num_workers == 1 or n < min_parallel_size:
        return alg2(data)

    workers = min(num_workers, n)
    block_size, extra = divmod(n, workers)
    chunks = []
    start = 0
    for i in range(workers):
        end = start + block_size + (i < extra)
        chunks.append(data[start:end])
        start = end

    # Top-level alg2 is importable by spawned workers; it never creates a pool.
    with mp.get_context("spawn").Pool(processes=workers) as pool:
        runs = pool.map(alg2, chunks, chunksize=1)

    # An unmatched run is carried forward when a round has an odd run count.
    while len(runs) > 1:
        next_runs = []
        for i in range(0, len(runs), 2):
            if i + 1 == len(runs):
                next_runs.append(runs[i])
            else:
                next_runs.append(merge_sorted(runs[i], runs[i + 1]))
        runs = next_runs
    return runs[0]


if __name__ == "__main__":
    sample = [8, 3, 7, 1, 6, 2, 5, 4]
    print(parallel_alg2(sample, num_workers=2))
