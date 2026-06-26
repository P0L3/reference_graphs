import os
import networkx as nx
import pandas as pd
import numpy as np
from sklearn.metrics import adjusted_rand_score
from networkx.algorithms.community import louvain_communities

print("==========================================")
print("  LOADING MULTIPLEX GRAPH")
print("==========================================\n")

EXPORT_DIR = "exported_graphs"
TIMESTAMP = "12-55-26-06-2026"   # Update to match your target run

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
        # Safely convert to undirected for community and core analysis
        multiplex_graph[internal_key] = G.to_undirected()
    else:
        print(f"Warning: File not found: {file_path}")

print("\n==========================================")
print("  RQ4: CORE-PERIPHERY & COMMUNITY PERSISTENCE")
print("==========================================\n")

# ---------------------------------------------------------
# 1. COMMUNITY PERSISTENCE (Adjusted Rand Index)
# ---------------------------------------------------------
print("--- 1. COMMUNITY PERSISTENCE (Projects vs. Co-authorship) ---")

G_coauth = multiplex_graph["co-authorship"]
G_project = multiplex_graph["project"]

# Find researchers active in BOTH layers
active_coauth = set([n for n, d in G_coauth.degree() if d > 0])
active_project = set([n for n, d in G_project.degree() if d > 0])
common_active_nodes = list(active_coauth.intersection(active_project))

print(f"Researchers active in BOTH Projects and Co-authorship: {len(common_active_nodes)}")

if len(common_active_nodes) > 1:
    # Induce subgraphs of only the overlapping researchers
    sub_coauth = G_coauth.subgraph(common_active_nodes)
    sub_project = G_project.subgraph(common_active_nodes)
    
    # Run Louvain Community Detection
    # Note: louvain_communities returns a list of sets (the communities)
    comms_coauth = louvain_communities(sub_coauth, weight='weight', seed=42)
    comms_project = louvain_communities(sub_project, weight='weight', seed=42)
    
    # Map nodes to their community ID
    # We must ensure the arrays passed to ARI are in the exact same node order
    node_to_comm_coauth = {}
    for comm_id, comm in enumerate(comms_coauth):
        for node in comm:
            node_to_comm_coauth[node] = comm_id
            
    node_to_comm_project = {}
    for comm_id, comm in enumerate(comms_project):
        for node in comm:
            node_to_comm_project[node] = comm_id
            
    labels_coauth = [node_to_comm_coauth[n] for n in common_active_nodes]
    labels_project = [node_to_comm_project[n] for n in common_active_nodes]
    
    # Calculate Adjusted Rand Index (ARI)
    ari_score = adjusted_rand_score(labels_project, labels_coauth)
    
    print(f"Number of distinct communities in Projects: {len(comms_project)}")
    print(f"Number of distinct communities in Co-authorship: {len(comms_coauth)}")
    print(f"Adjusted Rand Index (ARI): {ari_score:.4f}")
    
    if ari_score > 0.7:
        print("  -> Interpretation: High persistence. Project teams strictly dictate publication groups.")
    elif ari_score > 0.3:
        print("  -> Interpretation: Moderate persistence. Funding influences, but does not strictly control, publication output.")
    else:
        print("  -> Interpretation: Low persistence. Academic publishing is highly autonomous and structurally independent of project boundaries.")
else:
    print("Not enough common nodes to perform community persistence analysis.")

print("\n")

# ---------------------------------------------------------
# 2. MULTILAYER k-CORE DECOMPOSITION
# ---------------------------------------------------------
print("--- 2. MULTILAYER k-CORE DECOMPOSITION ---")

# Build a binary aggregated graph (if a tie exists in ANY layer, it exists here)
# This represents the total structural scaffolding of the university
G_agg_unweighted = nx.Graph()
for layer_name, G in multiplex_graph.items():
    for u, v in G.edges():
        G_agg_unweighted.add_edge(u, v)

for layer_name, G in multiplex_graph.items():
    loops = list(nx.selfloop_edges(G))
    if loops:
        print(f"  [{layer_name}] {len(loops)} self-loop(s) found: {loops[:5]}")

# Remove self-loops (core_number does not support them)
G_agg_unweighted.remove_edges_from(nx.selfloop_edges(G_agg_unweighted))

# Remove completely isolated nodes (External noise, etc.)
active_agg_nodes = [n for n, d in G_agg_unweighted.degree() if d > 0]
G_agg_unweighted = G_agg_unweighted.subgraph(active_agg_nodes).copy()



# Calculate the core number for every node
# The core number of a node is the largest k such that the node is contained in a k-core.
core_numbers = nx.core_number(G_agg_unweighted)

max_k = max(core_numbers.values())
print(f"Maximum k-core level achieved (The Elite Core threshold): k = {max_k}")

# Categorize the university into 3 sociological strata:
elite_core = []
semi_core = []
periphery = []

for node, k in core_numbers.items():
    if k == max_k:
        elite_core.append(node)
    elif k >= max_k / 2:
        semi_core.append(node)
    else:
        periphery.append(node)

print(f"  Elite Core (k={max_k}):       {len(elite_core)} researchers")
print(f"  Semi-Core  ({max_k/2:.1f} <= k < {max_k}): {len(semi_core)} researchers")
print(f"  Periphery  (k < {max_k/2:.1f}):       {len(periphery)} researchers\n")

# Analyze the Institutional Composition of the Elite Core
print("Institutional breakdown of the Elite Core:")
core_institutions = []
for node in elite_core:
    inst = multiplex_graph["co-authorship"].nodes.get(node, {}).get("institution", "Unknown")
    # Filter out external to see true institutional anchors
    if inst != "External":
        core_institutions.append(inst)

if core_institutions:
    inst_counts = pd.Series(core_institutions).value_counts()
    for inst, count in inst_counts.items():
        print(f"  {inst}: {count} researchers")
else:
    print("  The Elite Core consists entirely of External nodes (or is empty).")