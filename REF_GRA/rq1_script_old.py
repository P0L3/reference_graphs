import networkx as nx
import pandas as pd
import numpy as np
import os
import networkx as nx
from tqdm import tqdm
import loading_graph


multiplex_graph = loading_graph.load_graph()

print("==========================================")
print("  RQ1: TOPOLOGICAL BASELINE OF LAYERS")
print("==========================================\n")

rq1_data = []

for layer_name, G in tqdm(multiplex_graph.items()):
    # 1. Filter out completely isolated nodes to get the active network
    active_nodes = [n for n, d in G.degree() if d > 0]
    G_active = G.subgraph(active_nodes) if active_nodes else G
    
    num_nodes = G_active.number_of_nodes()
    num_edges = G_active.number_of_edges()
    density = nx.density(G_active) if num_nodes > 1 else 0
    
    # 2. Track Fragmentation (Connected Components)
    if G_active.is_directed():
        components = list(nx.weakly_connected_components(G_active))
        num_components = len(components)
        gcc = G_active.subgraph(max(components, key=len)) if components else G_active
    else:
        components = list(nx.connected_components(G_active))
        num_components = len(components)
        gcc = G_active.subgraph(max(components, key=len)) if components else G_active
        
    gcc_nodes = gcc.number_of_nodes()
    gcc_ratio = (gcc_nodes / num_nodes) * 100 if num_nodes > 0 else 0
    
    # 3. Calculate Clustering (Triads)
    # Directed graphs use different clustering metrics, so we treat them separately
    if G_active.is_directed():
        avg_clustering = nx.degree_centrality(G_active) # Fallback or skip
        # For directed mentorship, transitive clustering is often less informative than reciprocity
        reciprocity = nx.overall_reciprocity(G_active)
        clustering_str = f"Recip: {reciprocity:.4f}"
    else:
        avg_clustering = nx.average_clustering(G_active)
        clustering_str = f"Clust: {avg_clustering:.4f}"
        
    # 4. Calculate Path Length and Diameter safely on the GCC
    if gcc_nodes > 1:
        if gcc.is_directed():
            # For directed path lengths, we treat as undirected to measure generic reachability
            gcc_undirected = gcc.to_undirected()
            avg_path_len = nx.average_shortest_path_length(gcc_undirected)
            diameter = nx.diameter(gcc_undirected)
        else:
            avg_path_len = nx.average_shortest_path_length(gcc)
            diameter = nx.diameter(gcc)
    else:
        avg_path_len = 0
        diameter = 0
        
    rq1_data.append({
        "Layer": layer_name.upper(),
        "Active Nodes": num_nodes,
        "Edges": num_edges,
        "Density": f"{density:.4f}",
        "Components": num_components,
        "GCC Size (%)": f"{gcc_ratio:.1f}%",
        "Path Length (GCC)": f"{avg_path_len:.2f}",
        "Diameter (GCC)": diameter,
        "Clustering/Reciprocity": clustering_str
    })

df_rq1 = pd.DataFrame(rq1_data)
print(df_rq1.to_string(index=False))