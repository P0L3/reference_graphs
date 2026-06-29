import networkx as nx
import pandas as pd
import itertools
import loading_graph


multiplex_graph = loading_graph.load_graph()

print("==========================================")
print("  RQ4: INTER-INSTITUTIONAL DYNAMICS")
print("==========================================\n")

# Get institution mapping from the node attributes
node_institutions = {}
for node in multiplex_graph["co-authorship"].nodes():
    node_institutions[node] = multiplex_graph["co-authorship"].nodes[node].get("institution", "Unknown")

rq4_data = []

# Analyze each layer
for layer_name, G in multiplex_graph.items():
    # Only look at active edges
    edges = list(G.edges())
    if not edges:
        continue
        
    internal_count = 0
    external_count = 0
    
    for u, v in edges:
        inst_u = node_institutions.get(u, "Unknown")
        inst_v = node_institutions.get(v, "Unknown")
        
        # Skip connections with unknown nodes
        if inst_u == "Unknown" or inst_v == "Unknown":
            continue
            
        if inst_u == inst_v:
            internal_count += 1
        else:
            external_count += 1
            
    total_valid_edges = internal_count + external_count
    ext_ratio = external_count / total_valid_edges if total_valid_edges > 0 else 0
    
    rq4_data.append({
        "Layer": layer_name.upper(),
        "Internal Edges (Silo)": internal_count,
        "External Edges (Bridge)": external_count,
        "Total Counted": total_valid_edges,
        "Boundary-Spanning Ratio": f"{ext_ratio * 100:.2f}%"
    })

df_rq4 = pd.DataFrame(rq4_data)
print(df_rq4.to_string(index=False))