# Studio 3 — Big Data

## Part 1: Algorithmic Mechanics & Data Reconstruction Leakage

Implementation: [big-data-exercises.ipynb](big-data-exercises.ipynb).

The function `suggest_corrections(typed_word: str, bloom_filter: BloomFilter) -> list[str]` generates all single-character substitutions using lowercase letters a–z, excluding the original character at each position. It queries each candidate in the Bloom filter and returns those that test positive. For `floeer`, this produces 150 candidates before filtering.

### 1. Reconstruction Analysis

The Bloom filter's bit vector stores no raw text, ASCII values, or string pointers, but it still reveals information about membership in the protected vocabulary. An adversary can generate candidate mutations of known or suspected words and query the filter. The same hash functions map each candidate to positions in the bit array. If any corresponding bit is zero, the candidate is definitely absent; if all are one, it is possibly present. By repeating this process, an adversary can eliminate candidates and narrow down which words may be in the database without directly reading its contents.

This is a form of data leakage because membership information itself reveals something about the protected data. The filter acts as a membership oracle: combined with linguistic patterns or domain knowledge, its responses can help reconstruct portions of the protected vocabulary. This does not require reversing the hashes or extracting strings from the bit vector. However, reconstruction may be incomplete or inaccurate because false positives can admit absent words, and words outside the generated candidate set remain undiscovered. Not storing raw text therefore does not eliminate the possibility of inference through queries.

### 2. Execution Test

I loaded `words.txt` into three Bloom filters, each with `size=10**7` bits (approximately 1.25 MB of bit storage). The filters use the first hash function, the first two, and all three, respectively. Each filter uses one shared bit array and the same input word list. I tested the correction function with `"floeer"`.

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

These results match the exercise examples. Checking the suggestions against the supplied word list confirms that `floter` and `flower` are present, while the other returned candidates are absent. Thus, this test produced six false positives with one hash function, one with two, and none with three. As the exercise explains, `floter` is a valid Middle English suggestion, while `flower` is the intended correction. The Bloom filter alone cannot determine which valid suggestion the user intended.

Increasing the hash count reduced false positives in this experiment because a candidate must pass every selected bit check. With one hash function, an absent word such as `bloeer` can pass when its position was set by another word. Additional hash functions require more corresponding positions to be one: `bloeer` is eliminated with two hashes, and `fyoeer` is eliminated with three. Inserted words still pass because their corresponding bits were set during insertion. A positive result remains probabilistic; zero false positives for this test does not guarantee zero false positives for other inputs. More hashes are not always better, since they also set more bits during insertion and can eventually make a fixed-size array too full.

---

### Reproduction and AI assistance

Place the course-provided `words.txt` beside the notebook, install `bitarray` if needed, and run the cells from top to bottom. The reported outputs were independently rerun and checked against the local word list on September 27, 2026. The exact word list was used to validate results, not to filter candidates inside `suggest_corrections`.

ChatGPT/Codex assisted with the correction function, explanations, and README drafting. The student discussed the algorithm and examined its outputs; Codex also reran the code to verify the reported results.
