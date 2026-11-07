"""DAG DP: minimum latency, co-optimal path counts, and bottlenecks.

Source: Dynamic programming.pdf, pages 1 and 3-4.
load_graph() and get_topological_sort() follow the supplied starter code.
The supplied loader and Kahn algorithm are retained with input checks.
OpenAI Codex assisted with implementation, explanations, and validation.
"""

from collections import defaultdict, deque
from pathlib import Path
import math

import pandas as pd

EPSILON = 1e-6


def load_graph(csv_path):
    """Load the supplied CSV edge list into adjacency data structures."""
    df = pd.read_csv(csv_path)
    required = {"source", "target", "weight"}
    if not required.issubset(df.columns):
        raise ValueError("CSV must contain source, target, and weight columns.")
    if df.empty or df[list(required)].isna().any().any():
        raise ValueError("The edge list must be nonempty and contain no missing values.")
    if df.duplicated(["source", "target"]).any():
        raise ValueError("Duplicate edges are not supported; each ordered pair must be unique.")
    adj = defaultdict(list)
    in_degree = defaultdict(int)
    nodes = set()

    for _, row in df.iterrows():
        u, v, w = str(row["source"]), str(row["target"]), float(row["weight"])
        if not math.isfinite(w) or w <= 0:
            raise ValueError("Edge weights must be finite and strictly positive.")
        adj[u].append((v, w))
        in_degree[v] += 1
        nodes.add(u)
        nodes.add(v)
        if u not in in_degree:
            in_degree[u] = 0

    return adj, in_degree, nodes


def get_topological_sort(nodes, adj, in_degree):
    """Order nodes using the starter code's Kahn algorithm."""
    in_deg = dict(in_degree)
    queue = deque([v for v in nodes if in_deg[v] == 0])
    topo_order = []

    while queue:
        u = queue.popleft()
        topo_order.append(u)
        for v, weight in adj[u]:
            in_deg[v] -= 1
            if in_deg[v] == 0:
                queue.append(v)

    if len(topo_order) != len(nodes):
        raise ValueError("Graph contains a cycle! Dynamic Programming requires a DAG.")

    return topo_order


def _forward_sweep(adj, nodes, topo_order, source):
    """Compute minimum distances and counts on an already ordered DAG."""
    # Base case: one empty path reaches the source with zero latency.
    D = {node: float("inf") for node in nodes}
    C = {node: 0 for node in nodes}
    D[source] = 0.0
    C[source] = 1

    # Extend optimal routes from each reachable node to its children.
    for u in topo_order:
        if D[u] == float("inf"):
            continue

        for v, weight in adj[u]:
            candidate = D[u] + weight

            if candidate < D[v] - EPSILON:
                # A better route replaces all previously counted routes.
                D[v] = candidate
                C[v] = C[u]
            elif abs(candidate - D[v]) <= EPSILON:
                # An equally good route adds every optimal prefix reaching u.
                C[v] += C[u]

    return D, C


def forward_dp(csv_path, source="EGFR"):
    """Return (D, C), using EPSILON as an absolute precision guard in minutes."""
    adj, in_degree, nodes = load_graph(csv_path)
    if source not in nodes:
        raise ValueError(f"Source {source!r} is missing from the network.")
    topo_order = get_topological_sort(nodes, adj, in_degree)
    return _forward_sweep(adj, nodes, topo_order, source)


def minimum_latencies(csv_path, source="EGFR"):
    """Return only distances, preserving the earlier notebook interface."""
    D, _ = forward_dp(csv_path, source=source)
    return D


def network_details(csv_path, source="EGFR", target="MYC"):
    """Return both DP sweeps and per-node frequencies for inspection/export."""
    adj, in_degree, nodes = load_graph(csv_path)
    if source not in nodes or target not in nodes:
        raise ValueError("Source and target must both appear in the network.")
    topo_order = get_topological_sort(nodes, adj, in_degree)
    D, C = _forward_sweep(adj, nodes, topo_order, source)

    rev_adj = defaultdict(list)
    for u in nodes:
        for v, weight in adj[u]:
            rev_adj[v].append((u, weight))

    R = {node: 0 for node in nodes}
    if C[target] > 0:
        R[target] = 1
        for v in reversed(topo_order):
            if R[v] == 0:
                continue
            for u, weight in rev_adj[v]:
                if abs((D[u] + weight) - D[v]) <= EPSILON:
                    R[u] += R[v]

    F = {node: C[node] * R[node] for node in nodes}
    bottlenecks = sorted(
        node for node in nodes
        if node not in {source, target} and C[target] > 0
        and F[node] == C[target]
    )
    return {
        "source": source, "target": target,
        "node_count": len(nodes),
        "edge_count": sum(len(edges) for edges in adj.values()),
        "min_latency": D[target], "co_optimal_path_count": C[target],
        "bottlenecks": bottlenecks, "topo_order": topo_order,
        "D": D, "C": C, "R": R, "F": F,
    }


def analyze_network(csv_path, source="EGFR", target="MYC"):
    """Return (min_latency, co_optimal_path_count, bottlenecks), as assigned."""
    result = network_details(csv_path, source, target)
    return result["min_latency"], result["co_optimal_path_count"], result["bottlenecks"]


if __name__ == "__main__":
    csv_file = Path(__file__).with_name("egfr_myc_large_network.csv")
    if not csv_file.is_file():
        raise SystemExit(f"Place the supplied dataset beside this script: {csv_file}")

    latency, paths, bottlenecks = analyze_network(csv_file)
    if paths == 0:
        print("MYC is unreachable from EGFR.")
    else:
        print(f"Minimum EGFR-to-MYC latency: {latency:.2f} minutes")
        print(f"Co-optimal path count: {paths}")
        print(f"Bottleneck target genes: {bottlenecks}")
