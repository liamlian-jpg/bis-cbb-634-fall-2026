# Studio 2 — Exercise 2: Algorithm Analysis and Performance Measurement

[Back to course portfolio](../README.md)

## Code and reproduction

[Exercise 2 notebook](Untitled.ipynb) contains the supplied algorithms, data generators, and the 2a output analysis. With NumPy and Jupyter installed, open the notebook, restart the kernel, and run all cells in order. No patient dataset is required.

## 2a — Output analysis

I used all three provided generators with `n = 8`. Each algorithm receives a copy of the same input, and I compare both outputs with Python's `sorted()` result. These are small functionality checks, not performance measurements.

```python
n = 8

test_cases = [
    ("data1", data1(n)),
    ("data2", data2(n)),
    ("data3", data3(n)),
]

for case_name, test_input in test_cases:
    output1 = alg1(test_input.copy())
    output2 = alg2(test_input.copy())
    expected = sorted(test_input)

    print(f"Case: {case_name}")
    print("Input:   ", test_input)
    print("alg1:    ", output1)
    print("alg2:    ", output2)
    print("Both correct:", output1 == expected and output2 == expected)
    print("-" * 50)
```

### Actual inputs and outputs

```text
Case: data1
Input:    [31.0, 31.026, 31.07515666666667, 31.1456131764, 31.236317170692352, 31.346883543428103, 31.477492347868477, 31.628814213217787]
alg1:     [31.0, 31.026, 31.07515666666667, 31.1456131764, 31.236317170692352, 31.346883543428103, 31.477492347868477, 31.628814213217787]
alg2:     [31.0, 31.026, 31.07515666666667, 31.1456131764, 31.236317170692352, 31.346883543428103, 31.477492347868477, 31.628814213217787]
Both correct: True
--------------------------------------------------
Case: data2
Input:    [0, 1, 2, 3, 4, 5, 6, 7]
alg1:     [0, 1, 2, 3, 4, 5, 6, 7]
alg2:     [0, 1, 2, 3, 4, 5, 6, 7]
Both correct: True
--------------------------------------------------
Case: data3
Input:    [8, 7, 6, 5, 4, 3, 2, 1]
alg1:     [1, 2, 3, 4, 5, 6, 7, 8]
alg2:     [1, 2, 3, 4, 5, 6, 7, 8]
Both correct: True
--------------------------------------------------
```

Both functions return ascending sequences for all three inputs. The first eight default `data1` values happen to be increasing, so their order remains unchanged; this short sample does not establish that longer outputs are always sorted. `data2` is already ascending. `data3` is descending and is reversed into ascending order by both algorithms. All three comparisons with `sorted()` return `True`.

### Conceptual mechanics

**alg1:** The function repeatedly scans adjacent pairs and swaps them when the right value is smaller than the left. A large value can move right through successive swaps during one scan. If any swap occurs, `changes` becomes `True` and another scan follows. A complete scan with no swaps establishes that the list is ordered and ends the loop. This is bubble sort with an early-exit check. Already ordered input needs one scan, O(n); reverse-ordered input needs O(n) scans of O(n) comparisons, giving O(n²).

**alg2:** The function recursively divides the list into two parts until each part contains at most one element. Those parts are already sorted. It then merges sorted halves by comparing their current first remaining elements, appending the smaller one, and advancing that side's iterator. `alg2(...)` performs the sorting; `iter(...)` only allows sequential access to the sorted result. When `next()` raises `StopIteration`, that side is exhausted, so the function returns the accumulated result plus the other side's current element and remaining iterator values. The current element must be included separately because it has already been removed from the iterator. This is merge sort.

For n = 4, the recursion has 1 + 2 + 4 = 7 calls, but a call's cost depends on the size of its list. Combining two sorted halves of total length m takes O(m) work. Each merge level processes O(n) elements in total, and there are O(log n) levels, giving O(n log n). List slicing also costs O(n) per level in total and does not change this order. Execution processes the left subtree, then the right subtree, before merging; it does not execute all tree nodes simultaneously.

## Code evolution and design choices

I traced alg1's swap flag and recognized that any swap triggers another full scan, leading to quadratic worst-case behavior. For alg2, I worked through splitting, recursion, iterator advancement, and exhaustion handling. I drew the decomposition of `[4, 1, 3, 2]`, followed by merging into `[1, 4]`, `[2, 3]`, and finally `[1, 2, 3, 4]`. I distinguished the geometric growth in function-call counts from the work performed per call, which explains the O(n log n) total.

For output analysis, I chose small inputs from the supplied generators to connect the functionality checks with the later benchmarking tasks. The generator definitions were added to the saved notebook so it can run after a kernel restart without relying on previous session state.

## Validation and AI assistance

All three saved code cells executed in order in a fresh Python namespace. Both algorithms matched `sorted()` for each of the three generated inputs; the output above is captured from that execution. These examples demonstrate functionality on the tested inputs, not a timing comparison.

I used OpenAI Codex to help explain the algorithms, prepare the output-analysis code, verify execution, and document my reasoning. My discussion and hand-drawn recursion trace informed the conceptual explanation.
