# Studio 3 — Big Data

## Part 1: Algorithmic Mechanics & Data Reconstruction Leakage

Implementation: [big-data-exercises.ipynb](big-data-exercises.ipynb).

The function `suggest_corrections(typed_word: str, bloom_filter: BloomFilter) -> list[str]` generates all single-character substitutions using lowercase letters a–z, excluding the original character at each position. It queries each candidate in the Bloom filter and returns those that test positive. For `floeer`, this produces 150 candidates before filtering.

### 1. Reconstruction Analysis

The Bloom filter's bit vector stores no raw text, ASCII values, or string pointers, but it still reveals information about membership in the protected vocabulary. An adversary can generate candidate mutations of known or suspected words and query the filter. The same hash functions map each candidate to positions in the bit array. If any corresponding bit is zero, the candidate is definitely absent; if all are one, it is possibly present. By repeating this process, an adversary can eliminate candidates and narrow down which words may be in the database without directly reading its contents.

This is a form of data leakage because membership information itself reveals something about the protected data. The filter acts as a membership oracle: combined with linguistic patterns or domain knowledge, its responses can help reconstruct portions of the protected vocabulary. This does not require reversing the hashes or extracting strings from the bit vector. However, reconstruction may be incomplete or inaccurate because false positives can admit absent words, and words outside the generated candidate set remain undiscovered. Not storing raw text therefore does not eliminate the possibility of inference through queries.

### 2. Execution Test

I loaded `words.txt` into three Bloom filters, each with `size=10**7` bits (approximately 1.25 MB of bit storage). The filters use the first hash function, the first two, and all three, respectively. Each filter uses one shared bit array and the same input word list. I tested the correction function with `"floeer"`.

The following code uses the supplied `BloomFilter` class and the `words` list loaded from `words.txt`:

```python
bf1 = BloomFilter(size=10**7, hash_count=1)
bf2 = BloomFilter(size=10**7, hash_count=2)
bf3 = BloomFilter(size=10**7, hash_count=3)

for word in words:
    bf1.add(word)
    bf2.add(word)
    bf3.add(word)

import string

def suggest_corrections(
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

    return suggestions

print(suggest_corrections("floeer", bf1))
print(suggest_corrections("floeer", bf2))
print(suggest_corrections("floeer", bf3))
```

The verified notebook outputs are:

**First hash function — SHA-256:**

```python
['bloeer', 'qloeer', 'fyoeer', 'flofer', 'floter', 'flower', 'floeqr', 'floees']
```

**First and second hash functions — SHA-256 and BLAKE2b:**

```python
['fyoeer', 'floter', 'flower']
```

**All three hash functions — SHA-256, BLAKE2b, and SHA3-256:**

```python
['floter', 'flower']
```

Increasing the hash count reduced false positives in this experiment because a candidate must pass every selected bit check. With one hash function, an absent word such as `bloeer` can pass when its position was set by another word. Additional hash functions require more corresponding positions to be one: `bloeer` is eliminated with two hashes, and `fyoeer` is eliminated with three. Inserted words still pass because their corresponding bits were set during insertion. A positive result remains probabilistic; zero false positives for this test does not guarantee zero false positives for other inputs. More hashes are not always better, since they also set more bits during insertion and can eventually make a fixed-size array too full.


## Part 2: Empirical Evaluation & Plotting

### 1. Metrics Definition

The evaluation dataset contains 50,000 pairs of `[typed_word, correct_word]`, including 25,000 pairs with different input and target strings. Both metrics reuse the same vocabulary from `words.txt`.

- **Misidentified Percent:** 100 times the number of typo inputs accepted by the Bloom filter, divided by the 25,000 typo cases. Correctly spelled inputs are excluded from this denominator. This follows the assignment's typo-based definition.
- **Good Suggestion Percent:** 100 times the number of cases whose suggestion list contains at most three entries and includes `correct_word`, divided by all 50,000 cases. The other suggestions need not all be real words to satisfy this definition. Lists are not truncated to three before scoring.

Part 1's function remains unchanged. For Part 2, `suggest_corrections_part2` generates the same substitutions and adds the original lowercased word once if it passes the Bloom filter. This handles correctly spelled inputs without using the answer to generate suggestions. `correct_word` is used only for scoring. A mistyped original word that passes as a false positive is also included. This is our explicit evaluation convention for the full dataset.

The additional block in `suggest_corrections_part2` appears after the substitution loops and immediately before `return suggestions`:

```python
    # Include the original word once if it passes the Bloom filter.
    if word in bloom_filter:
        suggestions.append(word)

    return suggestions
```


### 2. Parametric Plotting and Parallel Architecture

The final sweep evaluates 23 filter sizes from 1,000 to 1,000,000,000 bits with hash counts 1, 2, and 3: **69 independent configurations**. Each configuration rebuilds its filter from the same word list and computes both metrics on the same evaluation data.

The main design decision was to parallelize **whole configurations**, rather than have workers modify a shared filter or counter. The implementation is in [part2_parallel.py](part2_parallel.py):

1. `ProcessPoolExecutor` creates up to three reusable worker processes using the `spawn` context. Each worker loads the vocabulary and test pairs once through an initializer.
2. Each task owns one `(filter_size, hash_count)` configuration, builds its own Bloom filter, and returns a small result record. No shared mutable counters, `Manager`, or shared bit array are needed.
3. The main process receives finished tasks through `as_completed()`, prints progress, and writes the accumulated results. Workers do not write the CSV, avoiding concurrent file writes.
4. After every completed configuration, the main process atomically replaces the checkpoint and CSV files. The checkpoint records input-file and module-code hashes. On a subsequent run with matching inputs and code, completed configurations present in the checkpoint and still requested are skipped; only missing configurations run.

This checkpoint design made iterative refinement practical: we kept the earlier size values, added new points around the transition regions, and later extended the range to 500 million and one billion bits without repeating the retained completed configurations. It is not a permanent cache of every past experiment: narrowing a requested grid rewrites the checkpoint with only retained configurations. If input data or module code changes, the program rejects reuse; a new output path or `resume=False` starts a fresh run.

`ProcessPoolExecutor` is a Python standard-library interface built on multiprocessing. We chose its futures interface for convenient completion-order collection and error reporting. Lecture 4's `multiprocessing.Pool` with `imap_unordered()` could implement the same workflow; no claim is made that our interface is inherently faster. The design follows the lecture's principles of reusing workers, sharing less state, and centralizing output. [Python documentation](https://docs.python.org/3/library/concurrent.futures.html#processpoolexecutor)

The trade-off is additional memory for worker-local data and filters, plus process startup and communication overhead. At the largest size, each bit array alone requires about 125 MB, before vocabulary and interpreter overhead. We used three workers rather than launching all 69 configurations at once. We did not measure a serial-versus-parallel speedup. The supplied `_get_hashes` computes all three digests before slicing, so fewer selected hashes do not eliminate those digest computations.

**Final experimental results:** [CSV](part2-results-parallel.csv). The notebook contains the exact parameter grid and plotting code; the [checkpoint](part2-results-parallel.checkpoint.json) supports resuming with matching local inputs and code.

![Misidentified and Good Suggestion percentages versus Bloom filter size for one, two, and three hash functions](part2-filter-size-combined.png)

The six lines connect measured values on a logarithmic horizontal axis; no smoothing or fitted curve was applied. Larger filters generally reduce misidentification and improve the Good Suggestion percentage. Two and three hashes reach high suggestion quality with much less space than one hash. At one billion bits, the Good Suggestion percentages are 88.408%, 88.964%, and 88.966% for one, two, and three hashes. The plateau is an observed result; a case-level failure analysis has not been performed, so its exact causes are not established here.

## Part 3: Deep Dive & Critical Analysis

### 1. Filter Capacity Threshold

The saved empirical results bracket the 85% Good Suggestion threshold as follows:

| Hash count | Last tested point below 85% | First tested point at or above 85% | Observed crossing interval (bits) |
| --- | --- | --- | --- |
| 1 | 100,000,000 bits: 73.412% | 500,000,000 bits: 87.670% | 100,000,000–500,000,000 |
| 2 | 20,000,000 bits: 84.784% | 23,000,000 bits: 86.160% | 20,000,000–23,000,000 |
| 3 | 9,000,000 bits: 81.496% | 11,000,000 bits: 85.932% | 9,000,000–11,000,000 |

Among the tested configurations, the smallest sizes achieving at least 85% are therefore **500 million, 23 million, and 11 million bits** for one, two, and three hashes, respectively. These are measured sufficient sizes, not exact minimum thresholds. The one-hash interval is especially wide because of sparse sampling there; additional points would be needed for a tighter estimate. The comparison shows that, in this experiment, extra hash checks substantially reduce the storage needed to reach the target.

### 2. Combinatorial Explosion & Mutation Spaces (Edit Distance vs. K-mers)

Our single-character substitution implementation generates `25L` candidates for a lowercase word of length `L`, since it excludes replacing a character with itself. Part 2 separately considers the unchanged word once. Allowing two edits greatly expands the search: even exactly two substitutions at different positions produce `C(L, 2) * 25**2` distinct strings. For a six-letter word, this is 9,375 candidates, compared with 150 for one substitution. Insertions, deletions, and adjacent transpositions add further possibilities, and different edit paths can generate the same string, requiring deduplication. With edit distance fixed at two, the naive candidate-generation scale is roughly quadratic in word length for a fixed alphabet, rather than exponential in length. The branching search grows rapidly, approximately exponentially in permitted edit depth before accounting for duplicate paths, when the allowed number of edits increases.

More absent candidates mean more opportunities for false positives. If `Q` queried candidates are absent and each has approximately false-positive probability `p`, the expected number of false-positive candidates is about `Qp`. More queries do not by themselves increase the filter's per-query false-positive probability, but they increase total false-positive overhead and computational work. A separate issue is genuine vocabulary ambiguity: many English words are only one or two edits apart. Even a perfect membership test can return more than three real words, failing the Good Suggestion criterion without any Bloom filter false positives. Expanding the edit radius can also recover previously unreachable correct answers, so the net effect on Good Suggestion Rate is not guaranteed to be negative; it balances better coverage against longer, more ambiguous lists.

The same reasoning applies to sequence reads and k-mers. A read is a sequenced DNA fragment; a k-mer is a contiguous substring of length k. For example, `ACGTAC` contains the 3-mers `ACG`, `CGT`, `GTA`, and `TAC`. Here k denotes substring length, not the number of Bloom filter hashes. A filter containing trusted reference k-mers can screen candidate variants of a potentially erroneous sequence fragment. With the four-letter DNA alphabet, one substitution generates `3L` candidates, but permitting multiple edits or insertions/deletions still expands the search substantially. A single substitution within a read can affect several overlapping k-mers. Repeats and similar genomic regions create genuine matching ambiguity in addition to probabilistic false positives. Thus a Bloom filter can act as an efficient preliminary screen, while alignment, base-quality information, or neighboring sequence context may be needed to resolve candidates. [Background on k-mers](https://pmc.ncbi.nlm.nih.gov/articles/PMC11874746/)

Sequencing errors should be distinguished from true biological variants, and their relative frequencies depend on sequencing technology. Insertions and deletions are often called indels. The adjacent-character transpositions considered in edit-distance search should not be equated with large chromosomal translocations or rearrangements. [NHGRI: Human Genomic Variation](https://www.genome.gov/about-genomics/educational-resources/fact-sheets/human-genomic-variation)

### 3. Cryptographic vs. Non-Cryptographic Hash Efficiency

In this non-adversarial evaluation, cryptographic hashes may provide poor performance value relative to the properties we need: deterministic, fast computation with well-distributed positions and sufficiently low correlation between hash outputs. SHA-256, BLAKE2b, and SHA3-256 also target security properties such as preimage resistance (difficulty finding an input for a specified digest) and collision resistance (difficulty deliberately finding two different inputs with the same digest). Their cryptographic processing can add overhead to the very large number of short-string queries performed here. Non-cryptographic alternatives such as MurmurHash3, xxHash, and FNV-1a do not provide those security guarantees and may be better suited to fast membership filtering, but they are not interchangeable in quality or speed. A particular replacement should be assessed for both distribution and runtime; we did not benchmark alternatives. [NIST hash properties](https://csrc.nist.gov/glossary/term/Cryptographic_hash_function), [xxHash design](https://xxhash.com/)

Cryptographic collision resistance does not remove Bloom filter collisions: the full digest is reduced modulo the finite bit-array size, so distinct digests can still map to the same position. False positives can also result from different inserted words collectively setting all queried positions. Cryptographic hashes therefore provide no automatic structural advantage over suitably distributed non-cryptographic hashes for ordinary Bloom filter membership checks. Accuracy depends on capacity, inserted-item count, hash count, and the quality and dependence of the resulting positions, not simply on whether the algorithm is cryptographic.

They also do not make this vocabulary confidential. As discussed in Part 1, an adversary can compute hashes of candidate words and test membership without inverting any digest. The current public, unkeyed implementation therefore does not prevent reconstruction leakage merely by using cryptographic hashes. Cryptographic or keyed designs can matter under adversarial threat models, but that is a separate security design question; even keying alone does not eliminate leakage if unrestricted membership queries remain available. For this exercise, fast non-cryptographic hashing is a reasonable alternative to investigate rather than assuming cryptographic strength is necessary.

---

## Studio 3 — Code evolution and design choices

I began with the supplied Bloom filter and used nested loops to generate single-character substitutions. I excluded the original letter at each position and queried candidates as they were generated, keeping only those that passed. This avoided storing the full candidate set, at the cost of regenerating it for each filter configuration. An initial test used `floter` instead of `floeer`; correcting the input resolved the mismatch with the exercise's example outputs.

For Part 2, I separated the two metric denominators: misidentification uses only typo cases, while Good Suggestion uses all evaluation cases. I kept Part 1 unchanged and created `suggest_corrections_part2`, which includes the original word once only if it passes the filter. This avoids duplicate original words and handles correctly spelled inputs without consulting the ground-truth answer. I used counters rather than retaining every case's result, and scored the full suggestion list without truncating it to three.

After running the metrics for a fixed filter size, I expanded the experiment to compare filter sizes and hash counts. With Codex's help, I used a three-worker process pool to evaluate independent configurations. Each worker builds its own filter, while the main process collects results and saves progress. I retained completed configurations through a checkpoint, so adding parameter points did not require restarting the entire sweep. This made repeated refinement practical, although each worker needs its own memory and no serial-versus-parallel speedup was measured.

I increased the grid to 23 filter sizes, adding points around the transitions and extending it to 500 million and one billion bits to observe the one-hash curve approaching its plateau. I combined both metrics into one graph with six lines and widened the figure for readability. The logarithmic axis accommodates the large size range, and the lines connect actual observations without smoothing. Saved CSV results let me revise the graph without rerunning the experiment. I reported the 85% crossing intervals and first qualifying measured sizes rather than claiming exact thresholds between sampled points.

In interpreting the results, I distinguished Bloom filter false positives from genuine ambiguity among similar words. More real-word candidates can violate the three-suggestion limit even when membership checks are accurate. I also separated the performance requirements of ordinary membership filtering from the security properties of cryptographic hashing. The final graph's plateau is observed, but I have not performed a case-by-case analysis to establish its exact causes or benchmarked replacement hash algorithms.

## Studio 3 — AI assistance

I used OpenAI Codex to assist with code generation, README writing, debugging, and code maintenance. We discussed candidate generation, metric denominators, handling correctly spelled inputs without using the answer, parallel execution, checkpoint reuse, graph design, and the interpretation of capacity thresholds. I ran the full experiment, expanded the parameter grid, and reviewed the outputs. I contributed the reasoning about genuine-word ambiguity and hashing trade-offs; Codex helped refine the complexity terminology and explain k-mers and cryptographic hash properties where I needed guidance.

Codex implemented the process-pool and checkpoint structure, helped express the analysis, and checked the 69 saved records against the checkpoint, input and code hashes, and reported threshold values. Small synthetic tests checked agreement between the parallel implementation and notebook calculations; the complete sweep was not independently rerun during the documentation update. I made the overall decisions through this discussion and retained responsibility for understanding and verifying the final work.
