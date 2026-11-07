"""Plot the supplied synthetic network for exploration in Jupyter.

Codex-assisted visualization; this does not implement the assignment's DP tasks.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import networkx as nx
import pandas as pd


def plot_network(csv_path, focus=True, show_weights=None, save_path=None):
    """Plot all nodes, or all nodes on any EGFR-to-MYC path.

    Edge labels show latency in minutes, not cumulative shortest distances.
    Returns the figure, axes, and displayed graph.
    """
    df = pd.read_csv(csv_path)
    graph = nx.from_pandas_edgelist(
        df, source="source", target="target", edge_attr="weight",
        create_using=nx.DiGraph(),
    )
    if not nx.is_directed_acyclic_graph(graph):
        raise ValueError("The network must be a DAG for this layered layout.")
    if not {"EGFR", "MYC"}.issubset(graph):
        raise ValueError("The network must contain EGFR and MYC.")

    if focus:
        downstream = nx.descendants(graph, "EGFR") | {"EGFR"}
        upstream = nx.ancestors(graph, "MYC") | {"MYC"}
        graph = graph.subgraph(downstream & upstream).copy()
        if not graph:
            raise ValueError("There is no EGFR-to-MYC path.")

    if show_weights is None:
        show_weights = focus

    # Each layer contains nodes whose upstream dependencies are in earlier layers.
    layers = [sorted(layer) for layer in nx.topological_generations(graph)]
    positions = {
        node: (level, (len(layer) - 1) / 2 - index)
        for level, layer in enumerate(layers)
        for index, node in enumerate(layer)
    }

    # Align the supplied network's branches into readable lanes.
    # These display coordinates do not affect graph structure or DP calculations.
    focus_positions = {
        "EGFR": (0, 0), "SHC1": (1, 3), "GRB2": (1, 1),
        "GAB1": (1, -1), "JAK1": (1, -3), "SOS1": (2, 1),
        "JAK2": (2, -3), "KRAS": (3, 2), "STAT3": (3, -3),
        "RAF1": (4, 2), "PIK3CA": (4, -0.2),
        "MAP2K1": (5, 2), "PDK1": (5, -0.2),
        "MAPK1": (6, 2), "AKT1": (6, -0.2),
        "MTOR": (7, 1), "GSK3B": (7, -1), "MYC": (8, 0),
    }
    if focus and set(graph) == set(focus_positions):
        positions = focus_positions

    fig, ax = plt.subplots(figsize=(18, 8) if focus else (24, 16))
    colors = [
        "#0f766e" if node == "EGFR" else
        "#b45309" if node == "MYC" else "#dbeafe"
        for node in graph
    ]
    node_size = 1900 if focus else 1000
    nx.draw_networkx_nodes(
        graph, positions, ax=ax, node_color=colors,
        node_size=node_size, edgecolors="white", linewidths=1.5,
    )
    for node, position in positions.items():
        ax.text(
            *position, node, ha="center", va="center",
            fontsize=10 if focus else 8, fontweight="bold",
            color="white" if node in {"EGFR", "MYC"} else "#172554",
        )

    # Curve edges that skip layers to keep them away from intermediate nodes.
    for u, v, data in graph.edges(data=True):
        span = positions[v][0] - positions[u][0]
        style = "arc3,rad=0.22" if span > 1 else "arc3,rad=0"
        nx.draw_networkx_edges(
            graph, positions, edgelist=[(u, v)], ax=ax,
            node_size=node_size, edge_color="#64748b", width=1.3,
            arrows=True, arrowsize=17, connectionstyle=style,
        )
        if show_weights:
            nx.draw_networkx_edge_labels(
                graph, positions, edge_labels={(u, v): f"{data['weight']:g}"},
                ax=ax, font_size=8, rotate=False, connectionstyle=style,
                label_pos=0.7 if span > 1 else 0.5,
                node_size=node_size,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.9},
            )

    title = "EGFR-to-MYC pathways" if focus else "Complete synthetic signaling network"
    ax.set_title(
        f"{title}\n{graph.number_of_nodes()} nodes | {graph.number_of_edges()} edges",
        fontsize=18, pad=22,
    )
    legend = [
        Line2D([], [], marker="o", linestyle="", color="#0f766e", label="EGFR: source"),
        Line2D([], [], marker="o", linestyle="", color="#b45309", label="MYC: target"),
    ]
    ax.legend(handles=legend, loc="upper left", frameon=False)
    caption = "Arrows: signal direction | Left to right: topological layers (not elapsed time)"
    if show_weights:
        caption += "\nEdge labels: latency in minutes"
    fig.text(0.5, 0.025, caption, ha="center", fontsize=11, color="#475569")
    ax.margins(x=0.08, y=0.25)
    ax.axis("off")
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    if save_path is not None:
        fig.savefig(save_path, dpi=180, bbox_inches="tight", facecolor="white")
    return fig, ax, graph


if __name__ == "__main__":
    folder = Path(__file__).resolve().parent
    plot_network(
        folder / "egfr_myc_large_network.csv",
        save_path=folder / "egfr_myc_network.png",
    )
    plt.show()
