import numpy as np
import os
import networkx as nx
# Define the directory and timestamp of your exported run
EXPORT_DIR = "exported_graphs"
TIMESTAMP = "12-01-25-06-2026"  # Update this to match the target run

# Map the internal multiplex dictionary keys to your sanitized filenames
layers_mapping = {
    "co-authorship": "co_authorship",
    "mentorship":    "mentorship",
    "similarity":    "similarity",
    "project":       "project"
}

def load_graph(EXPORT_DIR=EXPORT_DIR, TIMESTAMP=TIMESTAMP, layers_mapping=layers_mapping):

    multiplex_graph = {}

    print("==========================================")
    print(f"  LOADING MULTIPLEX GRAPH (Run: {TIMESTAMP})")
    print("==========================================\n")

    for internal_key, file_prefix in layers_mapping.items():
        file_path = os.path.join(EXPORT_DIR, f"{file_prefix}_{TIMESTAMP}.graphml")
        
        if os.path.exists(file_path):
            # read_graphml automatically detects and handles directed vs undirected graphs
            G = nx.read_graphml(file_path)
            
            # Defensive conversion: Ensure edge weights are floats
            for u, v, data in G.edges(data=True):
                if 'weight' in data:
                    try:
                        data['weight'] = float(data['weight'])
                    except (ValueError, TypeError):
                        pass
                        
            multiplex_graph[internal_key] = G
            print(f"Successfully loaded '{internal_key}' Layer:")
            print(f"  Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")
        else:
            print(f"Warning: File not found for '{internal_key}' Layer: {file_path}")

    print(f"\nAll loaded layers: {list(multiplex_graph.keys())}")

    return multiplex_graph