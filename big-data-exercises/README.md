# Studio 3 — Big Data: Bloom Filter Spell Correction

## Status and files

Part 1 is implemented and verified. Parts 2 and later are not covered by this update.

- [Notebook](big-data-exercises.ipynb): supplied BloomFilter class, word loading, three filter configurations, candidate generation, and saved results.
- Input: place the assignment's `words.txt` beside the notebook. Input files remain local; obtain them from the course source.
- Dependency: Python 3.9+ and `bitarray` (validation used version 3.11.0). In Jupyter, run `%pip install bitarray` if needed, then run the notebook from top to bottom with this folder as the working directory.

## Part 1 implementation

`suggest_corrections(typed_word, bloom_filter)` lowercases the input and uses two nested loops. The outer loop visits each character position, and the inner loop tries each lowercase ASCII letter except the current one. Each candidate differs by exactly one substitution. Candidates are queried immediately and only positive results are appended. For an input of n lowercase ASCII letters, this makes 25n queries; `floeer` has 150 candidates. The function never inserts candidates into the filter.

Three separate filters each contain 10**7 bits (about 1.25 MB of bit storage), using the first one, first two, or all three supplied hash functions. Within each filter, the hash functions share one bit array. All filters load the same word list.

## Reconstruction analysis

Although the bit vector stores no raw text, it still reveals information about which words may belong to the protected vocabulary. An adversary can generate candidate mutations of known or suspected words and query the Bloom filter. Each candidate is mapped to bit positions using the same hash functions. If any corresponding bit is zero, the candidate is definitely absent; if all are one, it is possibly present. Repeating this process allows the adversary to eliminate candidates and identify plausible vocabulary without directly reading the underlying database.

This constitutes data leakage because membership information is itself information about the protected data. The Bloom filter acts as a membership oracle, allowing an adversary to test guesses and combine the results with linguistic patterns or domain knowledge to infer protected words. Reconstruction is not guaranteed to be exact or complete: false positives can make absent words appear present, and words outside the generated candidate set remain undiscovered. Omitting raw strings prevents direct reading but does not prevent inference through repeated queries.

## Execution results

Verified on September 27, 2026 by executing the saved notebook code in a fresh Python namespace. The local input contains 466,550 nonblank entries and 466,546 distinct lowercased words.

Input SHA-256: `39a4ead879cc8283de87f2ec58e7b4b340d6caa724db1b52a91dccf2f273c5e7`

Test input: `floeer`.

| Hash count | Suggestions | False positives checked against the input word set |
| --- | --- | --- |
| 1 | `bloeer`, `qloeer`, `fyoeer`, `flofer`, `floter`, `flower`, `floeqr`, `floees` | 6 |
| 2 | `fyoeer`, `floter`, `flower` | 1 |
| 3 | `floter`, `flower` | 0 |

These outputs match the assignment examples. Both `floter` and `flower` occur in the supplied word list. The filter cannot determine which is the intended word. All distinct inserted words were also checked against the three-hash filter and returned positive. The exact word set was used only for validation, not inside the correction function. These counts describe this one candidate set, not an overall false-positive rate.

Increasing the number of checked hash positions reduced false positives in this experiment: an absent word must encounter a one at every checked position to pass. However, additional hashes also set more bits during insertion. With fixed array size, excessive hash counts can increase occupancy and eventually worsen false positives. The approximate optimum is k = (m/n) ln(2), where m is the bit count and n is the distinct inserted-word count; this implementation supplies only three hash functions.

Implementation detail: `_get_hashes` computes all three digests before slicing the list. Thus `hash_count=1` does not perform only one digest calculation in the supplied code. The configurations differ in positions set and checked, not in the number of digests computed. No runtime speedup is claimed.

## Design decision and debugging

We generate and query candidates on the fly to avoid storing the full candidate list. This reduces temporary memory usage, but candidates are regenerated for each filter comparison. We accepted this repeated work to keep the function simple and consistent with the required interface. Single-character substitutions, the filter size, and the hash-count comparison are assignment constraints rather than our independent design choices.

An initial comparison used `floter` instead of the required `floeer`, so it generated a different candidate set. Correcting the test input produced the expected outputs. The key lesson is to check the input and configuration before assuming the algorithm is wrong, and to interpret a positive Bloom filter result as possible membership rather than proof.

## AI assistance and verification

ChatGPT/Codex assisted with explaining the supplied code, drafting the correction function and analysis, and distinguishing assignment constraints from implementation trade-offs. The student discussed the logic and examined notebook outputs. Codex reran the code against the local word list and checked the results reported above. This update does not claim completion of later parts.
