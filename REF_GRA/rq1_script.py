import os
import networkx as nx
import pandas as pd
import numpy as np
from tqdm import tqdm

print("==========================================")
print("  LOADING MULTIPLEX GRAPH")
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
        
        # Ensure correct data types for weight and institution
        for u, v, data in G.edges(data=True):
            if 'weight' in data:
                try: data['weight'] = float(data['weight'])
                except: pass
        for n, data in G.nodes(data=True):
            if 'institution' not in data or pd.isna(data['institution']):
                data['institution'] = 'Unknown'
                
        multiplex_graph[internal_key] = G
        print(f"Loaded '{internal_key}' Layer (Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()})")
    else:
        print(f"Warning: File not found: {file_path}")

print("\n==========================================")
print("  RQ1: HOMOPHILY & NULL MODEL BASELINES")
print("==========================================\n")

# Settings for statistical rigor
NULL_MODEL_ITERATIONS = 10  # Number of random graphs to generate per layer

def generate_degree_preserving_null(G_active):
    """Generates a randomized network preserving the exact degree of every node."""
    G_null = G_active.copy()
    num_edges = G_null.number_of_edges()
    if num_edges == 0:
        return G_null

    # For sparse graphs, requesting too many swaps is infeasible.
    # Cap swaps at num_edges and give a much more generous try budget.
    num_swaps = num_edges          # was: num_edges * 2
    max_tries = num_swaps * 50     # was: num_swaps * 5

    try:
        if G_null.is_directed():
            nx.directed_edge_swap(G_null, nswap=num_swaps, max_tries=max_tries)
        else:
            nx.double_edge_swap(G_null, nswap=num_swaps, max_tries=max_tries)
    except (nx.NetworkXError, nx.NetworkXAlgorithmError):
        # Graph is too small/dense/sparse to hit the swap target — return
        # whatever partial randomization was achieved.
        pass

    return G_null

rq1_data = []

for layer_name, G in multiplex_graph.items():
    print(f"Processing Layer: {layer_name.upper()}...")
    
    # 1. Isolate Filtering & Baseline Metrics
    total_nodes = G.number_of_nodes()
    active_nodes = [n for n, d in G.degree() if d > 0]
    G_active = G.subgraph(active_nodes).copy()
    
    num_active = G_active.number_of_nodes()
    num_edges = G_active.number_of_edges()
    isolate_pct = ((total_nodes - num_active) / total_nodes) * 100 if total_nodes > 0 else 0
    density = nx.density(G_active) if num_active > 1 else 0
    
    # GCC Calculation
    if G_active.is_directed():
        components = list(nx.weakly_connected_components(G_active))
    else:
        components = list(nx.connected_components(G_active))
    
    gcc_nodes = len(max(components, key=len)) if components else 0
    gcc_pct = (gcc_nodes / num_active) * 100 if num_active > 0 else 0
    
    # 2. Observed Sociological Metrics (Clustering & Assortativity)
    if G_active.is_directed():
        # Directed clustering is handled slightly differently in NetworkX
        obs_clustering = nx.average_clustering(G_active) 
    else:
        obs_clustering = nx.average_clustering(G_active)
        
    try:
        # Institutional Assortativity (Homophily)
        obs_assortativity = nx.attribute_assortativity_coefficient(G_active, 'institution')
    except Exception:
        obs_assortativity = np.nan
        
    # 3. Statistical Testing (Degree-Preserving Null Models)
    null_clusterings = []
    null_assortativities = []
    
    for _ in tqdm(range(NULL_MODEL_ITERATIONS), desc=f"  Null Models ({layer_name})", leave=False):
        G_null = generate_degree_preserving_null(G_active)
        null_clusterings.append(nx.average_clustering(G_null))
        try:
            null_assortativities.append(nx.attribute_assortativity_coefficient(G_null, 'institution'))
        except:
            pass
            
    mean_null_clust = np.mean(null_clusterings)
    std_null_clust = np.std(null_clusterings) if np.std(null_clusterings) > 0 else 1e-6
    z_clust = (obs_clustering - mean_null_clust) / std_null_clust
    
    mean_null_assort = np.mean(null_assortativities) if null_assortativities else np.nan
    std_null_assort = np.std(null_assortativities) if len(null_assortativities) > 0 and np.std(null_assortativities) > 0 else 1e-6
    z_assort = (obs_assortativity - mean_null_assort) / std_null_assort if not np.isnan(obs_assortativity) else np.nan
    
    rq1_data.append({
        "Layer": layer_name.upper(),
        "Isolates (%)": f"{isolate_pct:.1f}%",
        "GCC (%)": f"{gcc_pct:.1f}%",
        "Observed Clust": f"{obs_clustering:.3f}",
        "Null Clust (Mean)": f"{mean_null_clust:.3f}",
        "Clust Z-Score": f"{z_clust:.1f}",
        "Observed Assort": f"{obs_assortativity:.3f}",
        "Null Assort": f"{mean_null_assort:.3f}",
        "Assort Z-Score": f"{z_assort:.1f}"
    })

print("\n==========================================")
print("  RQ1 RESULTS: BASELINES & SIGNIFICANCE")
print("==========================================\n")

df_rq1 = pd.DataFrame(rq1_data)
print(df_rq1.to_string(index=False))