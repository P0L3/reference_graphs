import os
import networkx as nx
import pandas as pd
import numpy as np
import itertools
from scipy.stats import spearmanr

print("==========================================")
print("  LOADING MULTIPLEX GRAPH")
print("==========================================\n")

EXPORT_DIR = "exported_graphs"
TIMESTAMP = "12-55-26-06-2026"  # Update to match your target run

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
        for u, v, data in G.edges(data=True):
            if 'weight' in data:
                try: data['weight'] = float(data['weight'])
                except: pass
        multiplex_graph[internal_key] = G
    else:
        print(f"Warning: File not found: {file_path}")

print("\n==========================================")
print("  RQ3: INTERDISCIPLINARY BROKERAGE & AGGREGATION COST")
print("==========================================\n")

# ---------------------------------------------------------
# 1. BUILD AGGREGATED (MONOPLEX) AND SUPRA-GRAPH
# ---------------------------------------------------------
print("Constructing Aggregated Graph and Supra-Graph...")
G_agg = nx.Graph()
G_supra = nx.DiGraph() # Directed to accommodate both undirected and directed layers safely

all_nodes = set()

# Populate intra-layer edges
for layer_name, G in multiplex_graph.items():
    all_nodes.update(G.nodes())
    for u, v, data in G.edges(data=True):
        w = data.get('weight', 1.0)
        
        # 1a. Aggregated Graph (Flattened)
        if G_agg.has_edge(u, v):
            G_agg[u][v]['weight'] += w
        else:
            G_agg.add_edge(u, v, weight=w)
            
        # 1b. Supra-Graph (Node-Layer tuples)
        node_u_layer = f"{u}_{layer_name}"
        node_v_layer = f"{v}_{layer_name}"
        
        G_supra.add_edge(node_u_layer, node_v_layer, weight=w)
        if not G.is_directed(): # Add reverse edge for undirected layers
            G_supra.add_edge(node_v_layer, node_u_layer, weight=w)

# Populate inter-layer coupling edges (Categorical coupling, omega = 1.0)
INTER_LAYER_WEIGHT = 1.0
for node in all_nodes:
    for l1, l2 in itertools.combinations(layers_mapping.keys(), 2):
        n1 = f"{node}_{l1}"
        n2 = f"{node}_{l2}"
        if G_supra.has_node(n1) and G_supra.has_node(n2):
            G_supra.add_edge(n1, n2, weight=INTER_LAYER_WEIGHT)
            G_supra.add_edge(n2, n1, weight=INTER_LAYER_WEIGHT)

# ---------------------------------------------------------
# 2. PAGERANK AND SPEARMAN CORRELATION
# ---------------------------------------------------------
print("Calculating Monoplex and Multiplex PageRank...")
pr_agg = nx.pagerank(G_agg, weight='weight')
pr_supra = nx.pagerank(G_supra, weight='weight')

# Marginalize Multiplex PageRank (Sum layer-node scores into a single node score)
pr_multi = {}
for node in all_nodes:
    pr_multi[node] = sum(pr_supra.get(f"{node}_{l}", 0.0) for l in layers_mapping.keys())

# ---------------------------------------------------------
# 3. PARTICIPATION COEFFICIENT & BURT'S CONSTRAINT
# ---------------------------------------------------------
print("Calculating Participation Coefficients and Structural Holes...")

# Filter active nodes for Burt's constraint (to avoid disconnected component errors)
active_agg_nodes = [n for n, d in G_agg.degree() if d > 0]
G_agg_active = G_agg.subgraph(active_agg_nodes)
constraints = nx.constraint(G_agg_active)

rq3_data = []

for node in all_nodes:
    # Safely extract attributes
    attrs = multiplex_graph["co-authorship"].nodes.get(node, {})
    name = f"{attrs.get('name', '')} {attrs.get('surname', '')}".strip()
    inst = attrs.get('institution', 'Unknown')
    
    # Calculate Participation Coefficient
    k_layers = []
    for layer_name, G in multiplex_graph.items():
        deg = (G.out_degree(node) + G.in_degree(node)) if G.is_directed() else G.degree(node)
        k_layers.append(deg)
        
    o_i = sum(k_layers)
    if o_i > 0:
        # P = 1 - sum((k_l / o_i)^2)
        participation = 1.0 - sum((k / o_i)**2 for k in k_layers)
    else:
        participation = 0.0

    # Burt's Constraint (Lower is better for brokerage)
    constraint_val = constraints.get(node, np.nan)
    
    rq3_data.append({
        "node_id": node,
        "Name": name if name else node,
        "Institution": inst,
        "Monoplex PR": pr_agg.get(node, 0.0),
        "Multiplex PR": pr_multi.get(node, 0.0),
        "Participation": participation,
        "Constraint": constraint_val,
        "Total Degree": o_i
    })

df_rq3 = pd.DataFrame(rq3_data)

# Filter out inactive nodes and "External" noise for rankings
df_internal = df_rq3[(df_rq3["Total Degree"] > 0) & (df_rq3["Institution"] != "External")].copy()

# Calculate Ranks
df_internal["Mono_Rank"] = df_internal["Monoplex PR"].rank(ascending=False).astype(int)
df_internal["Multi_Rank"] = df_internal["Multiplex PR"].rank(ascending=False).astype(int)

# Spearman Correlation
rho, p_val = spearmanr(df_internal["Mono_Rank"], df_internal["Multi_Rank"])
information_loss = (1 - rho) * 100

print("\n" + "="*42)
print("  RQ3 RESULTS: THE COST OF AGGREGATION")
print("="*42 + "\n")

print(f"Spearman Rank Correlation ($\rho$): {rho:.4f} (p-value: {p_val:.2e})")
print(f"Information Destruction Score: {information_loss:.1f}%")
print("  -> Interpretation: Flattening the university into a single graph")
print(f"     destroys {information_loss:.1f}% of the structural truth regarding who the key actors are.\n")

print("--- TOP 5 BY PARTICIPATION COEFFICIENT (The Multi-contextual Brokers) ---")
print("(Researchers who distribute their effort evenly across Projects, Papers, Mentoring, and Topics)")
top_p = df_internal[df_internal["Total Degree"] > 10].sort_values(by="Participation", ascending=False)
print(top_p.head(5)[["Name", "Institution", "Participation", "Multi_Rank", "Total Degree"]].to_string(index=False))

print("\n--- TOP 5 STRUCTURAL HOLE SPANNERS (Lowest Burt's Constraint) ---")
print("(Researchers who connect disconnected silos/faculties)")
top_c = df_internal.sort_values(by="Constraint", ascending=True)
print(top_c.head(5)[["Name", "Institution", "Constraint", "Multi_Rank", "Participation"]].to_string(index=False))

print("\n--- 'HIDDEN GIANTS' (Highest Rank Jump from Monoplex to Multiplex PR) ---")
df_internal["Rank_Shift"] = df_internal["Mono_Rank"] - df_internal["Multi_Rank"]
top_shift = df_internal.sort_values(by="Rank_Shift", ascending=False)
print(top_shift.head(5)[["Name", "Institution", "Mono_Rank", "Multi_Rank", "Rank_Shift"]].to_string(index=False))