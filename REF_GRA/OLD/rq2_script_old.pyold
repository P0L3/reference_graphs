import networkx as nx
import pandas as pd
import itertools
import loading_graph


multiplex_graph = loading_graph.load_graph()


print("==========================================")
print("  RQ2: MULTIPLEX EDGE OVERLAP ANALYSIS")
print("==========================================\n")

def get_undirected_edge_set(G):
    """Normalizes directed and undirected edges to a standard, sorted undirected tuple set."""
    edges = set()
    for u, v in G.edges():
        edges.add(tuple(sorted((u, v))))
    return edges

# Extract edge sets for the main layers
edges_coauth = get_undirected_edge_set(multiplex_graph["co-authorship"])
edges_project = get_undirected_edge_set(multiplex_graph["project"])
edges_sim = get_undirected_edge_set(multiplex_graph["similarity"])
edges_mentor = get_undirected_edge_set(multiplex_graph["mentorship"])

all_layers = {
    "Co-authorship": edges_coauth,
    "Projects": edges_project,
    "Similarity": edges_sim,
    "Mentorship": edges_mentor
}

overlap_data = []

# Compare all pairs of layers
for (name_A, set_A), (name_B, set_B) in itertools.combinations(all_layers.items(), 2):
    intersection_size = len(set_A.intersection(set_B))
    union_size = len(set_A.union(set_B))
    jaccard_overlap = intersection_size / union_size if union_size > 0 else 0
    
    overlap_data.append({
        "Layer A": name_A,
        "Layer B": name_B,
        "Shared Edges": intersection_size,
        "Total Union": union_size,
        "Jaccard Overlap": f"{jaccard_overlap:.5f}"
    })

df_overlap = pd.DataFrame(overlap_data)
print(df_overlap.to_string(index=False))