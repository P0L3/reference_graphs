import os
import networkx as nx
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
import itertools
from scipy.spatial.distance import squareform
from scipy.cluster.hierarchy import linkage


def rq2_process_graph(multiplex_graph):
    """
    Analyses cross-layer reinforcement and multiplexity for a given multiplex
    graph dictionary. Expects undirected graphs (call .to_undirected() before
    passing in if needed).

    Returns a tuple of:
        - df_multiplicity  : DataFrame of edge multiplicity distribution
        - df_similarity    : DataFrame (layer x layer Jaccard similarity matrix)
        - structural_twins : dict with keys 'layer1', 'layer2', 'distance'
        - df_triads        : DataFrame of mixed triadic closure results
    """

    print("\n==========================================")
    print("  RQ2: CROSS-LAYER REINFORCEMENT & MULTIPLEXITY")
    print("==========================================\n")

    # ---------------------------------------------------------
    # 1. EDGE MULTIPLICITY DISTRIBUTION (Relationship Robustness)
    # ---------------------------------------------------------
    print("--- 1. EDGE MULTIPLICITY DISTRIBUTION ---")

    edge_layer_map = defaultdict(set)
    for layer_name, G in multiplex_graph.items():
        for u, v in G.edges():
            edge = tuple(sorted((u, v)))
            edge_layer_map[edge].add(layer_name)

    multiplicity_counts = Counter(len(layers) for layers in edge_layer_map.values())
    total_unique_edges = len(edge_layer_map)

    print("How many layers do connected researcher pairs share?")
    multiplicity_rows = []
    for k in range(1, 5):
        count = multiplicity_counts.get(k, 0)
        pct = (count / total_unique_edges) * 100 if total_unique_edges > 0 else 0
        print(f"  Existing in exactly {k} layer(s): {count:5d} pairs ({pct:.2f}%)")
        multiplicity_rows.append({"Layers Shared": k, "Pair Count": count, "Percentage (%)": round(pct, 2)})

    df_multiplicity = pd.DataFrame(multiplicity_rows)
    print()

    # ---------------------------------------------------------
    # 2. LAYER SIMILARITY MATRIX & HIERARCHICAL CLUSTERING
    # ---------------------------------------------------------
    print("--- 2. LAYER SIMILARITY MATRIX (JACCARD) ---")

    layer_names = list(multiplex_graph.keys())
    similarity_matrix = pd.DataFrame(index=layer_names, columns=layer_names, dtype=float)

    edge_sets = {
        l: set(tuple(sorted((u, v))) for u, v in multiplex_graph[l].edges())
        for l in layer_names
    }

    for l1, l2 in itertools.product(layer_names, repeat=2):
        if l1 == l2:
            similarity_matrix.loc[l1, l2] = 1.0
        else:
            s1, s2 = edge_sets[l1], edge_sets[l2]
            intersection = len(s1.intersection(s2))
            union = len(s1.union(s2))
            similarity_matrix.loc[l1, l2] = intersection / union if union > 0 else 0.0

    print(similarity_matrix.round(4))

    print("\n  -> Structural Twins (Closest Layers):")
    distance_matrix = 1.0 - similarity_matrix
    condensed_dist = squareform(distance_matrix.values, checks=False)
    Z = linkage(condensed_dist, method='complete')
    idx1, idx2 = int(Z[0, 0]), int(Z[0, 1])
    dist = Z[0, 2]
    print(f"     '{layer_names[idx1]}' and '{layer_names[idx2]}' are the most structurally similar (Distance: {dist:.4f})")

    structural_twins = {
        "layer1": layer_names[idx1],
        "layer2": layer_names[idx2],
        "distance": round(dist, 4)
    }
    print()

    # ---------------------------------------------------------
    # 3. MULTIPLEX TRANSITIVITY (Cozzo's Mixed Triads)
    # ---------------------------------------------------------
    print("--- 3. MULTIPLEX TRIADIC CLOSURE ---")

    def calculate_mixed_triad_closure(L1_name, L2_name, L3_name):
        """
        Checks: if U-V exists in L1 and V-W exists in L2,
        how often does U-W exist in L3?
        Note: wedges are counted twice (U-V-W and W-V-U),
        but the closure ratio remains accurate.
        """
        G1, G2, G3 = multiplex_graph[L1_name], multiplex_graph[L2_name], multiplex_graph[L3_name]
        open_wedges = 0
        closed_triangles = 0

        common_nodes = set(G1.nodes()).intersection(set(G2.nodes()))

        for v in common_nodes:
            neighbors_L1 = set(G1.neighbors(v))
            neighbors_L2 = set(G2.neighbors(v))
            for u in neighbors_L1:
                for w in neighbors_L2:
                    if u != w:
                        open_wedges += 1
                        if G3.has_edge(u, w):
                            closed_triangles += 1

        closure_rate = (closed_triangles / open_wedges) * 100 if open_wedges > 0 else 0
        return closure_rate, open_wedges // 2

    triad_tests = [
        ("project", "project", "co-authorship",
         "If A and B share a project, and B and C share a project, do A and C publish?"),
        ("co-authorship", "co-authorship", "project",
         "If A and B publish, and B and C publish, do A and C get a project?"),
        ("project", "similarity", "co-authorship",
         "If A & B share a project, and B & C share topics, do A & C publish?"),
    ]

    triad_rows = []
    for L1, L2, L3, hypothesis in triad_tests:
        rate, wedges = calculate_mixed_triad_closure(L1, L2, L3)
        print(f"Hypothesis: {hypothesis}")
        print(f"  Result: {rate:.2f}% closure rate (across {wedges} mixed open paths)\n")
        triad_rows.append({
            "L1": L1, "L2": L2, "L3": L3,
            "Hypothesis": hypothesis,
            "Closure Rate (%)": round(rate, 2),
            "Open Wedges": wedges
        })

    df_triads = pd.DataFrame(triad_rows)

    return df_multiplicity, similarity_matrix, structural_twins, df_triads


# =========================================================
# STANDALONE EXECUTION (Triggered only if run directly)
# =========================================================
if __name__ == "__main__":
    print("==========================================")
    print("  LOADING MULTIPLEX GRAPH (STANDALONE MODE)")
    print("==========================================\n")

    EXPORT_DIR = "exported_graphs"
    TIMESTAMP = "12-55-26-06-2026"  # Update to match your latest run

    layers_mapping = {
        "co-authorship": "co_authorship",
        "mentorship":    "mentorship",
        "similarity":    "similarity",
        "project":       "project"
    }

    multiplex_graph = {}
    for internal_key, file_prefix in layers_mapping.items():
        file_path = os.path.join(EXPORT_DIR, f"{file_prefix}_{TIMESTAMP}.graphml")
        if os.path.exists(file_path):
            G = nx.read_graphml(file_path)
            multiplex_graph[internal_key] = G.to_undirected()
            print(f"Loaded '{internal_key}' Layer (Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()})")
        else:
            print(f"Warning: File not found: {file_path}")

    # Run the analysis
    df_multiplicity, df_similarity, twins, df_triads = rq2_process_graph(multiplex_graph)

    # Print structured outputs
    print("\n==========================================")
    print("  RQ2 RESULTS SUMMARY")
    print("==========================================\n")
    print("-- Edge Multiplicity --")
    print(df_multiplicity.to_string(index=False))
    print(f"\n-- Structural Twins --")
    print(f"  '{twins['layer1']}' and '{twins['layer2']}' (Distance: {twins['distance']})")
    print("\n-- Triadic Closure --")
    print(df_triads[["L1", "L2", "L3", "Closure Rate (%)", "Open Wedges"]].to_string(index=False))