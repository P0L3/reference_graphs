import pandas as pd
import networkx as nx
import itertools
from tqdm import tqdm
import os
from datetime import datetime

# Load the multi-institutional data files

df_nodes = pd.read_csv("nodes_FIDIT.csv")# ("nodes_FIDIT_FABRI_FZF_FM.csv")
df_edges = pd.read_csv("edges_FIDIT.csv")# ("edges_FIDIT_FABRI_FZF_FM.csv")
df_keywords = pd.read_csv("keywords_FIDIT.csv")# ("keywords_FIDIT_FABRI_FZF_FM.csv")

# Ensure null institutions are marked as Unknown
df_nodes["institution"] = df_nodes["institution"].fillna("Unknown")

# ==========================================
# 5. GENERATE LAYER 3 (RESEARCH SIMILARITY) - JACCARD VERSION
# ==========================================
print("\nGenerating Research Similarity Edges (Layer 3)...")

# 1. Create a dictionary mapping Node -> Set of unique keywords they have used
node_keywords = df_keywords.groupby('node_id')['keyword'].apply(set).to_dict()

# 2. Define your significance threshold (e.g., 0.025 means they must share 2.5% of their total keywords)
SIMILARITY_THRESHOLD = 0.025

similarity_edges = []
nodes_with_keywords = list(node_keywords.keys())

# 3. Compare every pair of researchers (O(N^2))
for u, v in tqdm(itertools.combinations(nodes_with_keywords, 2), desc="Comparing keywords", total=len(nodes_with_keywords)*(len(nodes_with_keywords)-1)//2):
    set_u = node_keywords[u]
    set_v = node_keywords[v]
    
    intersection = set_u.intersection(set_v)
    if not intersection:
        continue
        
    union = set_u.union(set_v)
    
    # Calculate Jaccard Similarity
    jaccard_index = len(intersection) / len(union)
    
    # Only create an edge if it passes the threshold
    if jaccard_index >= SIMILARITY_THRESHOLD:
        similarity_edges.append({
            "source": u,
            "target": v,
            "layer": "similarity",
            "weight": jaccard_index, # Weight is now the similarity score 0.0 - 1.0
            "year_start": 0,
            "year_end": 2026,
            "context": f"shared_{len(intersection)}_keywords"
        })

df_similarity = pd.DataFrame(similarity_edges)
print(f"Created {len(df_similarity)} significant similarity edges (Threshold: {SIMILARITY_THRESHOLD})")

# Combine raw edges with generated similarity edges
df_all_edges = pd.concat([df_edges, df_similarity], ignore_index=True)

# ==========================================
# 6. AGGREGATE WEIGHTS & BUILD MULTIPLEX GRAPH
# ==========================================
print("\nAggregating edges and building Multiplex Graph...")

# Define our 4 layers. We use DiGraph for Mentorship to keep direction (Mentor -> Student).
# The others are undirected.
multiplex_graph = {
    "co-authorship": nx.Graph(),
    "mentorship": nx.DiGraph(),
    "similarity": nx.Graph(),
    "project": nx.Graph()
}

# Add all nodes to all layers with attributes (including dynamic institution!)
for _, node_row in df_nodes.iterrows():
    node_id = node_row['node_id']
    attrs = {
        "name": node_row['name'], 
        "surname": node_row['surname'],
        "institution": node_row['institution'] # <--- Added dynamic institution tracking
    }
    for layer_name in multiplex_graph.keys():
        multiplex_graph[layer_name].add_node(node_id, **attrs)

# To analyze the STATIC graph (across all time), we group the edges and sum the weights
# We use .sum() on "weight" to ensure similarity edges keep their decimal Jaccard values,
# while co-authorship and projects sum up their occurrences.
static_edges = df_all_edges.groupby(['source', 'target', 'layer'])['weight'].sum().reset_index()

# Add edges to the respective NetworkX graphs
for _, edge in static_edges.iterrows():
    u = edge['source']
    v = edge['target']
    layer = edge['layer']
    w = edge['weight']
    
    # For undirected graphs, we need to avoid A->B and B->A overwriting each other
    if not multiplex_graph[layer].is_directed():
        # If edge already exists, just add to the weight
        if multiplex_graph[layer].has_edge(u, v):
            multiplex_graph[layer][u][v]['weight'] += w
        else:
            multiplex_graph[layer].add_edge(u, v, weight=w)
    else:
        # Directed graph (Mentorship)
        if multiplex_graph[layer].has_edge(u, v):
            multiplex_graph[layer][u][v]['weight'] += w
        else:
            multiplex_graph[layer].add_edge(u, v, weight=w)

# ==========================================
# 7. BASIC MULTIPLEX METRICS (PROOF OF CONCEPT)
# ==========================================
print("\n--- MULTIPLEX NETWORK STATS ---")
for layer_name, G in multiplex_graph.items():
    # Only count isolated nodes to see how "active" a layer is
    active_nodes = [n for n, d in G.degree() if d > 0]
    print(f"Layer: {layer_name.upper()}")
    print(f"  Total Nodes: {G.number_of_nodes()} (Active: {len(active_nodes)})")
    print(f"  Total Edges: {G.number_of_edges()}")
    
    # Calculate density (ignoring isolated nodes for a fairer metric)
    if len(active_nodes) > 1:
        subgraph = G.subgraph(active_nodes)
        print(f"  Density of active network: {nx.density(subgraph):.4f}\n")
    else:
        print("  Density: 0.0\n")

# Show Node Distribution by Institution for confirmation
print("--- NODE DISTRIBUTION BY INSTITUTION ---")
print(df_nodes["institution"].value_counts().to_string())


# Create output folder
output_dir = "exported_graphs"
os.makedirs(output_dir, exist_ok=True)

# Timestamp format: hour-minute-date
timestamp = datetime.now().strftime("%H-%M-%d-%m-%Y")

# Export each layer separately
for layer_name, G in multiplex_graph.items():

    # Sanitize filename
    safe_name = layer_name.replace(" ", "_").replace("-", "_")

    # GraphML (recommended for Gephi, Cytoscape, NetworkX)
    graphml_path = os.path.join(
        output_dir,
        f"{safe_name}_{timestamp}.graphml"
    )
    nx.write_graphml(G, graphml_path)

    # Optional: GEXF (also works well with Gephi)
    gexf_path = os.path.join(
        output_dir,
        f"{safe_name}_{timestamp}.gexf"
    )
    nx.write_gexf(G, gexf_path)

    print(f"Saved {layer_name}:")
    print(f"  {graphml_path}")
    print(f"  {gexf_path}")