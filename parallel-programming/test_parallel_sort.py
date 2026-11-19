"""Correctness tests using real spawned workers and independent sorted output."""

import random
import unittest
from unittest.mock import patch

from parallel_sort import alg2, merge_sorted, parallel_alg2


class ParallelSortTests(unittest.TestCase):
    def check_sort(self, data, workers=2, cutoff=2):
        original = data.copy()
        expected = sorted(data)
        serial = alg2(data)
        result = parallel_alg2(data, workers, min_parallel_size=cutoff)
        self.assertEqual(serial, expected)
        self.assertEqual(result, serial)
        self.assertEqual(data, original)

    def test_empty_and_singleton(self):
        for data in ([], [42]):
            with self.subTest(data=data):
                self.check_sort(data)

    def test_duplicates(self):
        for data in ([3, 1, 3, 2, 1, 3, 2], [7] * 31):
            with self.subTest(data=data):
                self.check_sort(data, workers=3)

    def test_odd_lengths_and_uneven_chunks(self):
        self.check_sort([8, -1, 4, 2, 0, 9, 3, 7, 6, 5, -2], workers=3)

    def test_sorted_and_reversed(self):
        for data in (list(range(64)), list(range(63, -1, -1))):
            with self.subTest(first=data[0]):
                self.check_sort(data, workers=4)

    def test_more_workers_than_elements(self):
        self.check_sort([3, 1, 2], workers=8)

    def test_large_seeded_random_inputs(self):
        rng = random.Random(634)
        integers = [rng.randrange(-10000, 10001) for _ in range(100001)]
        floats = [rng.uniform(-100, 100) for _ in range(10001)]
        self.check_sort(integers, workers=3)
        self.check_sort(floats, workers=2)

    def test_serial_fallbacks_do_not_create_pool(self):
        with patch("parallel_sort.mp.get_context") as context:
            self.check_sort([], workers=4)
            self.check_sort([1], workers=4)
            self.check_sort([4, 2, 3, 1], workers=1)
            self.check_sort([4, 2, 3, 1], workers=4, cutoff=5)
            context.assert_not_called()
        # Equality with the cutoff takes the parallel path.
        self.check_sort([4, 2, 3, 1], workers=2, cutoff=4)

    def test_merge_exhaustion_and_empty_inputs(self):
        for left, right in (([], []), ([], [1]), ([1], []),
                            ([1, 2], [3, 4]), ([3, 4], [1, 2]),
                            ([1, 3, 3], [1, 2, 3])):
            with self.subTest(left=left, right=right):
                self.assertEqual(merge_sorted(left, right), sorted(left + right))

    def test_invalid_configuration(self):
        for workers in (0, -1):
            with self.subTest(workers=workers), self.assertRaises(ValueError):
                parallel_alg2([], workers)
        for workers in (True, 1.5):
            with self.subTest(workers=workers), self.assertRaises(TypeError):
                parallel_alg2([], workers)
        with self.assertRaises(ValueError):
            parallel_alg2([], min_parallel_size=-1)
        with self.assertRaises(TypeError):
            parallel_alg2([], min_parallel_size=1.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
