import os
import networkx as nx
import pandas as pd
import numpy as np
from sklearn.metrics import adjusted_rand_score
from networkx.algorithms.community import louvain_communities
from config import EXTERNAL_LABEL


def rq4_process_graph(multiplex_graph):
    """
    Analyses core-periphery structure and community persistence for a given
    multiplex graph dictionary. Expects undirected graphs (call .to_undirected()
    before passing in if needed).

    Returns a tuple of:
        - ari_result       : dict with 'ari_score', 'n_comms_project',
                             'n_comms_coauth', 'n_common_nodes', 'interpretation'
                             (all None if insufficient overlap)
        - df_core          : DataFrame with per-node 'core_number' and 'stratum'
        - core_stats       : dict with 'max_k', 'elite_core', 'semi_core',
                             'periphery' (counts), and 'thresholds'
        - df_inst_breakdown: DataFrame of institutional composition of the Elite Core
    """

    print("\n==========================================")
    print("  RQ4: CORE-PERIPHERY & COMMUNITY PERSISTENCE")
    print("==========================================\n")

    # ---------------------------------------------------------
    # 1. COMMUNITY PERSISTENCE (Adjusted Rand Index)
    # ---------------------------------------------------------
    print("--- 1. COMMUNITY PERSISTENCE (Projects vs. Co-authorship) ---")

    G_coauth  = multiplex_graph["co-authorship"]
    G_project = multiplex_graph["project"]

    active_coauth  = {n for n, d in G_coauth.degree()  if d > 0}
    active_project = {n for n, d in G_project.degree() if d > 0}
    common_active_nodes = list(active_coauth.intersection(active_project))

    print(f"Researchers active in BOTH Projects and Co-authorship: {len(common_active_nodes)}")

    ari_result = {
        "ari_score":       None,
        "n_comms_project": None,
        "n_comms_coauth":  None,
        "n_common_nodes":  len(common_active_nodes),
        "interpretation":  None
    }

    if len(common_active_nodes) > 1:
        sub_coauth  = G_coauth.subgraph(common_active_nodes)
        sub_project = G_project.subgraph(common_active_nodes)

        comms_coauth  = louvain_communities(sub_coauth,  weight='weight', seed=42)
        comms_project = louvain_communities(sub_project, weight='weight', seed=42)

        node_to_comm_coauth  = {node: cid for cid, comm in enumerate(comms_coauth)  for node in comm}
        node_to_comm_project = {node: cid for cid, comm in enumerate(comms_project) for node in comm}

        labels_coauth  = [node_to_comm_coauth[n]  for n in common_active_nodes]
        labels_project = [node_to_comm_project[n] for n in common_active_nodes]

        ari_score = adjusted_rand_score(labels_project, labels_coauth)

        if ari_score > 0.7:
            interpretation = "High persistence. Project teams strictly dictate publication groups."
        elif ari_score > 0.3:
            interpretation = "Moderate persistence. Funding influences, but does not strictly control, publication output."
        else:
            interpretation = "Low persistence. Academic publishing is highly autonomous and structurally independent of project boundaries."

        ari_result.update({
            "ari_score":       round(ari_score, 4),
            "n_comms_project": len(comms_project),
            "n_comms_coauth":  len(comms_coauth),
            "interpretation":  interpretation
        })

        print(f"Number of distinct communities in Projects:     {len(comms_project)}")
        print(f"Number of distinct communities in Co-authorship: {len(comms_coauth)}")
        print(f"Adjusted Rand Index (ARI): {ari_score:.4f}")
        print(f"  -> Interpretation: {interpretation}")
    else:
        print("Not enough common nodes to perform community persistence analysis.")

    print()

    # ---------------------------------------------------------
    # 2. MULTILAYER k-CORE DECOMPOSITION
    # ---------------------------------------------------------
    print("--- 2. MULTILAYER k-CORE DECOMPOSITION ---")

    # Binary aggregated graph: a tie exists if it appears in ANY layer
    G_agg_unweighted = nx.Graph()
    for layer_name, G in multiplex_graph.items():
        for u, v in G.edges():
            G_agg_unweighted.add_edge(u, v)

    # Report and remove self-loops (core_number does not support them)
    for layer_name, G in multiplex_graph.items():
        loops = list(nx.selfloop_edges(G))
        if loops:
            print(f"  [{layer_name}] {len(loops)} self-loop(s) found: {loops[:5]}")
    G_agg_unweighted.remove_edges_from(nx.selfloop_edges(G_agg_unweighted))

    # Remove isolated nodes
    active_agg_nodes = [n for n, d in G_agg_unweighted.degree() if d > 0]
    G_agg_unweighted = G_agg_unweighted.subgraph(active_agg_nodes).copy()

    core_numbers = nx.core_number(G_agg_unweighted)
    max_k = max(core_numbers.values())

    semi_core_threshold = max_k / 2

    elite_core = [n for n, k in core_numbers.items() if k == max_k]
    semi_core  = [n for n, k in core_numbers.items() if semi_core_threshold <= k < max_k]
    periphery  = [n for n, k in core_numbers.items() if k < semi_core_threshold]

    print(f"Maximum k-core level achieved (The Elite Core threshold): k = {max_k}")
    print(f"  Elite Core (k={max_k}):                   {len(elite_core)} researchers")
    print(f"  Semi-Core  ({semi_core_threshold:.1f} <= k < {max_k}): {len(semi_core)} researchers")
    print(f"  Periphery  (k < {semi_core_threshold:.1f}):             {len(periphery)} researchers\n")

    core_stats = {
        "max_k":      max_k,
        "elite_core": len(elite_core),
        "semi_core":  len(semi_core),
        "periphery":  len(periphery),
        "thresholds": {"elite": max_k, "semi_core_min": semi_core_threshold}
    }

    # Build per-node core DataFrame
    def _stratum(k):
        if k == max_k:            return "Elite Core"
        if k >= semi_core_threshold: return "Semi-Core"
        return "Periphery"

    df_core = pd.DataFrame([
        {"node_id": n, "core_number": k, "stratum": _stratum(k)}
        for n, k in core_numbers.items()
    ])

    # ---------------------------------------------------------
    # 3. INSTITUTIONAL COMPOSITION OF THE ELITE CORE
    # ---------------------------------------------------------
    print("Institutional breakdown of the Elite Core:")

    core_institutions = [
        multiplex_graph["co-authorship"].nodes.get(n, {}).get("institution", "Unknown")
        for n in elite_core
    ]
    internal_insts = [i for i in core_institutions if i != EXTERNAL_LABEL]

    if internal_insts:
        inst_counts = pd.Series(internal_insts).value_counts().reset_index()
        inst_counts.columns = ["Institution", "Count"]
        for _, row in inst_counts.iterrows():
            print(f"  {row['Institution']}: {row['Count']} researchers")
    else:
        inst_counts = pd.DataFrame(columns=["Institution", "Count"])
        print("  The Elite Core consists entirely of External nodes (or is empty).")

    return ari_result, df_core, core_stats, inst_counts


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
    ari_result, df_core, core_stats, df_inst = rq4_process_graph(multiplex_graph)

    print("\n==========================================")
    print("  RQ4 RESULTS SUMMARY")
    print("==========================================\n")
    print("-- Community Persistence --")
    if ari_result["ari_score"] is not None:
        print(f"  ARI Score        : {ari_result['ari_score']}")
        print(f"  Communities (Co-auth / Project): {ari_result['n_comms_coauth']} / {ari_result['n_comms_project']}")
        print(f"  Interpretation   : {ari_result['interpretation']}")
    else:
        print("  Insufficient overlap for ARI calculation.")

    print("\n-- k-Core Stats --")
    print(f"  Max k            : {core_stats['max_k']}")
    print(f"  Elite Core       : {core_stats['elite_core']} researchers")
    print(f"  Semi-Core        : {core_stats['semi_core']} researchers")
    print(f"  Periphery        : {core_stats['periphery']} researchers")

    print("\n-- Elite Core Institutional Breakdown --")
    print(df_inst.to_string(index=False))