"""Check DAG DP against exhaustive, exact-decimal path enumeration.

The enumerator is an independent small-graph oracle, not the production solver.
OpenAI Codex assisted with this validation code.
"""

from collections import defaultdict
from decimal import Decimal
from io import StringIO
from pathlib import Path
import csv
import math
import random
import unittest

from dp_intro import analyze_network, forward_dp, minimum_latencies, network_details

DATASET = Path(__file__).with_name("egfr_myc_large_network.csv")


def edge_csv(rows):
    return "source,target,weight\n" + "".join(f"{u},{v},{w}\n" for u, v, w in rows)


def enumerate_paths(text, source="EGFR", target="MYC"):
    """Enumerate simple paths with exact decimal sums on small inputs."""
    adjacency = defaultdict(list)
    for row in csv.DictReader(StringIO(text)):
        adjacency[row["source"]].append((row["target"], Decimal(row["weight"])))
    paths = []

    def visit(u, path, latency):
        if u == target:
            paths.append((latency, path))
            return
        for v, weight in adjacency[u]:
            if v not in path:
                visit(v, path + [v], latency + weight)

    visit(source, [source], Decimal(0))
    return paths


def check_against_enumeration(test, text):
    result = network_details(StringIO(text))
    paths = enumerate_paths(text)
    if not paths:
        test.assertTrue(math.isinf(result["min_latency"]))
        test.assertEqual(result["co_optimal_path_count"], 0)
        test.assertEqual(result["bottlenecks"], [])
        test.assertTrue(all(v == 0 for v in result["F"].values()))
        return
    best = min(latency for latency, _ in paths)
    optimal = [path for latency, path in paths if latency == best]
    test.assertAlmostEqual(result["min_latency"], float(best), places=10)
    test.assertEqual(result["co_optimal_path_count"], len(optimal))
    common = set.intersection(*(set(path) for path in optimal)) - {"EGFR", "MYC"}
    test.assertEqual(result["bottlenecks"], sorted(common))
    for node, frequency in result["F"].items():
        test.assertEqual(frequency, sum(node in path for path in optimal), node)
    test.assertEqual(result["R"]["EGFR"], result["C"]["MYC"])


class DPTests(unittest.TestCase):
    def test_unique_path_and_endpoints(self):
        text = edge_csv([("EGFR", "A", 1), ("A", "MYC", 2)])
        self.assertEqual(analyze_network(StringIO(text)), (3, 1, ["A"]))
        check_against_enumeration(self, text)

    def test_branch_merge_and_dead_end(self):
        text = edge_csv([
            ("EGFR", "A", 1), ("EGFR", "B", 1),
            ("A", "H", 1), ("B", "H", 1),
            ("H", "X", 1), ("H", "Y", 1),
            ("X", "MYC", 1), ("Y", "MYC", 1),
            ("EGFR", "DEAD", 1),
        ])
        self.assertEqual(analyze_network(StringIO(text)), (4, 4, ["H"]))
        check_against_enumeration(self, text)

    def test_shorter_route_replaces_counts(self):
        text = edge_csv([
            ("EGFR", "MYC", 10), ("EGFR", "A", 1), ("EGFR", "B", 1),
            ("A", "X", 1), ("B", "X", 1), ("X", "MYC", 1),
        ])
        self.assertEqual(analyze_network(StringIO(text)), (3, 2, ["X"]))
        check_against_enumeration(self, text)

    def test_floating_point_tie(self):
        text = edge_csv([("EGFR", "MYC", "0.3"), ("EGFR", "A", "0.1"), ("A", "MYC", "0.2")])
        check_against_enumeration(self, text)

    def test_unreachable_target(self):
        text = edge_csv([("EGFR", "A", 1), ("X", "MYC", 1)])
        check_against_enumeration(self, text)

    def test_cycle_rejected(self):
        text = edge_csv([("EGFR", "A", 1), ("A", "EGFR", 1), ("A", "MYC", 1)])
        with self.assertRaisesRegex(ValueError, "cycle"):
            analyze_network(StringIO(text))

    def test_invalid_inputs(self):
        for weight in ["0", "-1", "inf", "nan"]:
            with self.subTest(weight=weight), self.assertRaises(ValueError):
                analyze_network(StringIO(edge_csv([("EGFR", "MYC", weight)])))
        for text in [
            "source,target\nEGFR,MYC\n",
            edge_csv([]),
            edge_csv([("EGFR", "A", 1)]),
            edge_csv([("EGFR", "MYC", 1), ("EGFR", "MYC", 1)]),
        ]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                analyze_network(StringIO(text))

    def test_source_equals_target(self):
        text = edge_csv([("EGFR", "MYC", 1)])
        self.assertEqual(analyze_network(StringIO(text), target="EGFR"), (0, 1, []))

    def test_seeded_small_dags(self):
        rng = random.Random(634)
        nodes = ["EGFR", "A", "B", "C", "D", "MYC"]
        for index in range(40):
            rows = [("EGFR", "MYC", "5.00")]
            for i, u in enumerate(nodes):
                for v in nodes[i + 1:]:
                    if (u, v) != ("EGFR", "MYC") and rng.random() < 0.45:
                        rows.append((u, v, str(Decimal(rng.randint(1, 10)) / 10)))
            with self.subTest(graph=index):
                check_against_enumeration(self, edge_csv(rows))

    def test_legacy_interface(self):
        text = edge_csv([("EGFR", "MYC", 1)])
        D, C = forward_dp(StringIO(text))
        self.assertEqual(minimum_latencies(StringIO(text)), D)
        self.assertEqual(C["MYC"], 1)

    @unittest.skipUnless(DATASET.exists(), "Download the course CSV to run this check.")
    def test_course_dataset_and_row_order(self):
        text = DATASET.read_text()
        check_against_enumeration(self, text)
        expected = (7.5, 4, ["AKT1", "PDK1", "PIK3CA"])
        self.assertEqual(analyze_network(StringIO(text)), expected)
        rows = list(csv.DictReader(StringIO(text)))
        rng = random.Random(634)
        for _ in range(5):
            rng.shuffle(rows)
            shuffled = edge_csv([(r["source"], r["target"], r["weight"]) for r in rows])
            self.assertEqual(analyze_network(StringIO(shuffled)), expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
