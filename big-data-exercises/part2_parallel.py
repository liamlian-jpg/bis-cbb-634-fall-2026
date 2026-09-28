"""Process-based Part 2 sweep. Import run_parallel from a Jupyter cell.

The Bloom filter and evaluation functions match the notebook implementation.
Each worker loads the inputs once. Only the parent writes result files.
"""
import csv
import hashlib
import io
import json
import multiprocessing as mp
import os
import string
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from hashlib import blake2b, sha256, sha3_256
from bitarray import bitarray


class BloomFilter:

  def __init__(self, size: int, hash_count: int = 3):
    self.size = size
    self.hash_count = hash_count
    self.bit_array = bitarray(size)
    self.bit_array.setall(0)

  def _get_hashes(self, item: str):
    s = item.lower().encode()
    hashes = [
        int(sha256(s).hexdigest(), 16) % self.size,
        int(blake2b(s).hexdigest(), 16) % self.size,
        int(sha3_256(s).hexdigest(), 16) % self.size,
    ]
    return hashes[: self.hash_count]

  def add(self, item: str):
    for h in self._get_hashes(item):
      self.bit_array[h] = True

  def __contains__(self, item: str) -> bool:
    return all(self.bit_array[h] for h in self._get_hashes(item))

def misidentified_percent(typo_pairs, bloom_filter):
    if len(typo_pairs) == 0:
        return None

    false_positive_count = 0

    for typed_word, correct_word in typo_pairs:
        if typed_word in bloom_filter:
            false_positive_count += 1

    return false_positive_count / len(typo_pairs) * 100

def suggest_corrections_part2(
    typed_word: str,
    bloom_filter: BloomFilter
) -> list[str]:
    word = typed_word.lower()
    suggestions = []

    for i in range(len(word)):
        for letter in string.ascii_lowercase:
            if letter == word[i]:
                continue

            candidate = word[:i] + letter + word[i + 1:]

            if candidate in bloom_filter:
                suggestions.append(candidate)

    if word in bloom_filter:
        suggestions.append(word)

    return suggestions

def good_suggestion_percent(typos, bloom_filter):
    if len(typos) == 0:
        return None

    good_count = 0

    for typed_word, correct_word in typos:
        suggestions = suggest_corrections_part2(
            typed_word, bloom_filter
        )

        if len(suggestions) <= 3 and correct_word in suggestions:
            good_count += 1

    return good_count / len(typos) * 100

_WORDS = None
_TYPOS = None
_TYPO_PAIRS = None
FIELDS = ["filter_size_bits", "hash_count", "misidentified_percent", "good_suggestion_percent"]
DEFAULT_SIZES = [100_000, 300_000, 1_000_000, 3_000_000,
                 10_000_000, 30_000_000, 100_000_000]


def _load_inputs(words_path, typos_path):
    # Load the data once per worker, rather than once per configuration.
    global _WORDS, _TYPOS, _TYPO_PAIRS
    with open(words_path, encoding="utf-8") as f:
        _WORDS = [line.strip().lower() for line in f if line.strip()]
    with open(typos_path, encoding="utf-8") as f:
        _TYPOS = json.load(f)
    if not _WORDS or not _TYPOS:
        raise ValueError("The word list and evaluation data must be nonempty.")
    if any(not isinstance(pair, list) or len(pair) != 2
           or any(not isinstance(word, str) for word in pair) for pair in _TYPOS):
        raise ValueError("Each evaluation case must be a pair of strings.")
    _TYPO_PAIRS = [(typed, correct) for typed, correct in _TYPOS if typed != correct]


def _evaluate_configuration(size, k):
    # Each task owns a separate Bloom filter.
    start = time.perf_counter()
    bf = BloomFilter(size=size, hash_count=k)
    for word in _WORDS:
        bf.add(word)
    row = {
        "filter_size_bits": size,
        "hash_count": k,
        "misidentified_percent": misidentified_percent(_TYPO_PAIRS, bf),
        "good_suggestion_percent": good_suggestion_percent(_TYPOS, bf),
    }
    return row, time.perf_counter() - start


def _atomic_write(path, content):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def _save_results(output, checkpoint, signature, rows):
    # The checkpoint is authoritative; CSV can be regenerated on resume.
    ordered = sorted(rows, key=lambda row: (row["filter_size_bits"], row["hash_count"]))
    _atomic_write(checkpoint, json.dumps({"signature": signature, "results": ordered}, indent=2))
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(ordered)
    _atomic_write(output, stream.getvalue())


def run_parallel(filter_sizes=None, hash_counts=(1, 2, 3), max_workers=3,
                 words_path="words.txt", typos_path="typos.json",
                 output_path="part2-results-parallel.csv", resume=True):
    """Evaluate independent configurations using spawn-safe worker processes.

    Results use the same column names as the sequential plotting cell.
    Resume requires identical inputs and module code. Existing sequential results
    are not reused. Use a distinct output path for simultaneous experiments.
    On interruption, completed saved tasks survive; active tasks may finish
    before the process pool shuts down.
    """
    sizes = list(DEFAULT_SIZES if filter_sizes is None else filter_sizes)
    counts = list(hash_counts)
    if not sizes or any(type(size) is not int or size <= 0 for size in sizes):
        raise ValueError("Filter sizes must be positive integers.")
    if not counts or any(type(k) is not int or k not in (1, 2, 3) for k in counts):
        raise ValueError("Hash counts must be 1, 2, or 3.")
    if type(max_workers) is not int or max_workers < 1:
        raise ValueError("max_workers must be a positive integer.")
    words_path, typos_path = Path(words_path).resolve(), Path(typos_path).resolve()
    output = Path(output_path).resolve()
    checkpoint = output.with_suffix(".checkpoint.json")
    signature = {
        "words_sha256": hashlib.sha256(words_path.read_bytes()).hexdigest(),
        "typos_sha256": hashlib.sha256(typos_path.read_bytes()).hexdigest(),
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    configurations = list(dict.fromkeys((size, k) for size in sizes for k in counts))
    rows = []
    if resume and checkpoint.exists():
        saved = json.loads(checkpoint.read_text(encoding="utf-8"))
        if saved["signature"] != signature:
            raise ValueError("Inputs or code changed. Use a new output_path or resume=False.")
        rows = [row for row in saved["results"]
                if (row["filter_size_bits"], row["hash_count"]) in configurations]
    elif resume and output.exists():
        raise ValueError("CSV exists without a checkpoint. Use a new output_path or resume=False.")
    done = {(row["filter_size_bits"], row["hash_count"]) for row in rows}
    pending = [configuration for configuration in configurations if configuration not in done]
    output.parent.mkdir(parents=True, exist_ok=True)
    _save_results(output, checkpoint, signature, rows)
    print(f"Completed: {len(rows)}/{len(configurations)}; remaining: {len(pending)}", flush=True)
    if pending:
        workers = min(max_workers, os.cpu_count() or 1, len(pending))
        print(f"Running with {workers} worker processes", flush=True)
        with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn"),
                                 initializer=_load_inputs,
                                 initargs=(str(words_path), str(typos_path))) as pool:
            futures = [pool.submit(_evaluate_configuration, size, k) for size, k in pending]
            try:
                for future in as_completed(futures):
                    row, seconds = future.result()
                    rows.append(row)
                    _save_results(output, checkpoint, signature, rows)
                    print(f"[{len(rows)}/{len(configurations)}] "
                          f"size={row['filter_size_bits']:,}, k={row['hash_count']} | "
                          f"Misidentified={row['misidentified_percent']}% | "
                          f"Good Suggestion={row['good_suggestion_percent']:.2f}% | "
                          f"{seconds:.1f}s", flush=True)
            except BaseException:
                for future in futures:
                    future.cancel()
                print("Completed results saved; active workers may finish before shutdown.", flush=True)
                raise
    return sorted(rows, key=lambda row: (row["filter_size_bits"], row["hash_count"]))
