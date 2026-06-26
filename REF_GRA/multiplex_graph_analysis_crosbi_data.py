import os
import re
import sys
import itertools
from datetime import datetime
import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from tqdm import tqdm

# ==========================================
# 1. LOAD DATA & RECONSTRUCT MULTIPLEX GRAPH
# ==========================================
print("Loading data files...")
try:
    df_nodes = pd.read_csv("nodes_FIDIT.csv") # nodes_FIDIT_FABRI_FZF_FM
    df_edges = pd.read_csv("edges_FIDIT.csv") # edges_FIDIT_FABRI_FZF_FM
    df_keywords = pd.read_csv("keywords_FIDIT.csv") # keywords_FIDIT_FABRI_FZF_FM
except FileNotFoundError as e:
    print(f"Error: {e}")
    print("Please make sure you have executed the extraction script and have the CSV files in your directory.")
    sys.exit(1)

# Ensure null institutions are marked as External
df_nodes["institution"] = df_nodes["institution"].fillna("External")

# 1a. Generate Layer 3 (Research Similarity) using Jaccard Similarity
print("Reconstructing Research Similarity Layer (Jaccard projection)...")
node_keywords = df_keywords.groupby('node_id')['keyword'].apply(set).to_dict()
SIMILARITY_THRESHOLD = 0.025
similarity_edges = []
nodes_with_keywords = list(node_keywords.keys())

for u, v in itertools.combinations(nodes_with_keywords, 2):
    set_u = node_keywords[u]
    set_v = node_keywords[v]
    intersection = set_u.intersection(set_v)
    if not intersection:
        continue
    union = set_u.union(set_v)
    jaccard_index = len(intersection) / len(union)
    if jaccard_index >= SIMILARITY_THRESHOLD:
        similarity_edges.append({
            "source": u,
            "target": v,
            "layer": "similarity",
            "weight": jaccard_index,
            "year_start": 0,
            "year_end": 2026,
            "context": f"shared_{len(intersection)}_keywords"
        })

df_similarity = pd.DataFrame(similarity_edges)
df_all_edges = pd.concat([df_edges, df_similarity], ignore_index=True)

# 1b. Assemble Multiplex Graph
multiplex_graph = {
    "co-authorship": nx.Graph(),
    "mentorship":    nx.DiGraph(),
    "similarity":    nx.Graph(),
    "project":       nx.Graph()
}

# Add nodes with metadata
for _, node_row in df_nodes.iterrows():
    node_id = node_row['node_id']
    attrs = {
        "name": node_row['name'], 
        "surname": node_row['surname'],
        "institution": node_row['institution']
    }
    for layer_name in multiplex_graph.keys():
        multiplex_graph[layer_name].add_node(node_id, **attrs)

# Aggregate and apply weights using sum() to preserve Jaccard weights
static_edges = df_all_edges.groupby(['source', 'target', 'layer'])['weight'].sum().reset_index()

for _, edge in static_edges.iterrows():
    u, v, layer, w = edge['source'], edge['target'], edge['layer'], edge['weight']
    if not multiplex_graph[layer].is_directed():
        if multiplex_graph[layer].has_edge(u, v):
            multiplex_graph[layer][u][v]['weight'] += w
        else:
            multiplex_graph[layer].add_edge(u, v, weight=w)
    else:
        if multiplex_graph[layer].has_edge(u, v):
            multiplex_graph[layer][u][v]['weight'] += w
        else:
            multiplex_graph[layer].add_edge(u, v, weight=w)

# ==========================================
# 2. RUN ORGANIZATIONAL NETWORK ANALYSIS (ONA)
# ==========================================
print("\n" + "="*42)
print("  PHASE C: MULTILAYER NETWORK ANALYSIS")
print("="*42 + "\n")

# Analysis 1: Multiplex Degree Centrality
degree_data = []
for node in multiplex_graph["co-authorship"].nodes():
    attrs = multiplex_graph["co-authorship"].nodes[node]
    full_name = f"{attrs.get('name', '')} {attrs.get('surname', '')}".strip()
    row = {"node_id": node, "researcher": full_name, "institution": attrs.get('institution', 'External')}
    total_multiplex_degree = 0
    for layer_name, G in multiplex_graph.items():
        d = G.out_degree(node) + G.in_degree(node) if G.is_directed() else G.degree(node)
        row[f"deg_{layer_name}"] = d
        total_multiplex_degree += d
    row["multiplex_degree_overlap"] = total_multiplex_degree
    degree_data.append(row)

df_centrality = pd.DataFrame(degree_data)
df_centrality = df_centrality[df_centrality["multiplex_degree_overlap"] > 0].sort_values(by="multiplex_degree_overlap", ascending=False)

print("--- TOP 10 RESEARCHERS BY MULTIPLEX DEGREE OVERLAP ---")
print(df_centrality.head(10)[["researcher", "institution", "multiplex_degree_overlap", "deg_co-authorship", "deg_project"]].to_string(index=False))
print("\n")

# Analysis 2: Layer Edge Overlap
def get_undirected_edge_set(G):
    return set([tuple(sorted((u, v))) for u, v in G.edges()])

edges_coauth = get_undirected_edge_set(multiplex_graph["co-authorship"])
edges_project = get_undirected_edge_set(multiplex_graph["project"])
edges_sim = get_undirected_edge_set(multiplex_graph["similarity"])

def calculate_overlap(set_A, set_B, name_A, name_B):
    intersection = len(set_A.intersection(set_B))
    union = len(set_A.union(set_B))
    jaccard = intersection / union if union > 0 else 0
    print(f"Overlap between '{name_A}' and '{name_B}': {jaccard:.4f} ({intersection} shared edges)")

print("--- LAYER EDGE OVERLAP ---")
calculate_overlap(edges_coauth, edges_project, "Co-authorship", "Projects")
calculate_overlap(edges_coauth, edges_sim, "Co-authorship", "Similarity")
print("\n")

# ==========================================
# 3. INTERACTIVE CLI INTERFACE
# ==========================================
print("="*42)
print("  PHASE D: INTERACTIVE VISUALIZATION SETUP")
print("="*42 + "\n")

# 3a. Search Name Selection with Substring Support
while True:
    search_query = input("Enter researcher name to highlight (e.g. 'mestrovic', 'andrija'): ").strip()
    if not search_query:
        print("Input cannot be empty. Try again.")
        continue
    
    # Sanitize search input to lower ascii-like search
    query_clean = re.sub(r'[^\w\s]', '', search_query.lower())
    
    # Search registry
    matches = []
    for _, r in df_nodes.iterrows():
        node_name_clean = re.sub(r'[^\w\s]', '', f"{r['name']} {r['surname']}".lower())
        if query_clean in node_name_clean or query_clean in r['node_id'].lower():
            matches.append(r)
            
    if not matches:
        print("No matching researchers found. Please try another name.")
    elif len(matches) == 1:
        search_name = matches[0]['node_id']
        display_name = f"{matches[0]['name']} {matches[0]['surname']}"
        print(f"-> Resolved to: {display_name} ({matches[0]['institution']})")
        break
    else:
        print("\nMultiple matches found. Please choose the correct ID:")
        for idx, match in enumerate(matches):
            print(f" [{idx}] {match['name']} {match['surname']} ({match['institution']}) -> ID: {match['node_id']}")
        
        choice = input("Enter the number of your choice: ").strip()
        if choice.isdigit() and int(choice) < len(matches):
            chosen = matches[int(choice)]
            search_name = chosen['node_id']
            display_name = f"{chosen['name']} {chosen['surname']}"
            print(f"-> Resolved to: {display_name} ({chosen['institution']})")
            break
        else:
            print("Invalid selection. Restarting search.")

# 3b. Context Node Selection
num_nodes_input = input("Enter number of context nodes to display [default 120]: ").strip()
num_nodes = int(num_nodes_input) if num_nodes_input.isdigit() else 120
print(f"-> Plotting target researcher, neighbors, and Top {num_nodes} context nodes.")

# ==========================================
# 4. PREPARE 3D GRAPH DATA
# ==========================================
node_to_highlight = search_name
top_nodes_initial = df_centrality.head(num_nodes)['node_id'].tolist()

priority_layers = ["co-authorship", "mentorship", "project", "similarity"]
neighbors_of_target = set()
neighbor_first_level = {}

for layer_name in priority_layers:
    G = multiplex_graph[layer_name]
    z_val = {"co-authorship": 4, "mentorship": 3, "project": 2, "similarity": 1}[layer_name]
    
    if G.has_node(search_name):
        current_layer_neighbors = set()
        if G.is_directed():
            current_layer_neighbors.update(G.successors(search_name))
            current_layer_neighbors.update(G.predecessors(search_name))
        else:
            current_layer_neighbors.update(G.neighbors(search_name))
            
        for n in current_layer_neighbors:
            neighbors_of_target.add(n)
            if n not in neighbor_first_level:
                neighbor_first_level[n] = z_val

nodes_to_include = set(top_nodes_initial)
nodes_to_include.add(search_name)
nodes_to_include.update(neighbors_of_target)
top_nodes = list(nodes_to_include)

G_agg = nx.Graph()
for layer_name, G in multiplex_graph.items():
    for u, v in G.edges():
        if u in top_nodes and v in top_nodes:
            G_agg.add_edge(u, v)

pos_2d = nx.spring_layout(G_agg, seed=42, k=0.65)

# ==========================================
# 5. DRAW 3D MATPLOTLIB GRAPH
# ==========================================
fig = plt.figure(figsize=(15, 13))
ax = fig.add_subplot(111, projection='3d')

# Define layer ordering heights and faint colors for the boundaries
layers_meta = {
    "co-authorship": {"z": 4, "color": "#0072B2"}, # Blue Plane
    "mentorship":    {"z": 3, "color": "#CC79A7"}, # Purple Plane
    "project":       {"z": 2, "color": "#009E73"}, # Green Plane
    "similarity":    {"z": 1, "color": "#E69F00"}  # Orange Plane
}

# High-contrast colorblind-safe palette mapping for institutions
# Vermillion, Sky Blue, Yellowish Green, Charcoal, Grey
# colorblind-friendly markers for institutional mapping
INST_MARKERS = {
    "FIDIT": "^",     # Triangle Up
    "FABRI": "*",     # Star (5-point)
    "FZF": "s",       # Square
    "FM": "D",        # Diamond
    "External": "o"    # Circle (fallback)
}

# 5a. Draw Layer Planes (Planes remain distinct, while node colors reflect institution)
x_vals = [coords[0] for coords in pos_2d.values()]
y_vals = [coords[1] for coords in pos_2d.values()]
margin = 0.25
xx, yy = np.meshgrid(np.linspace(min(x_vals)-margin, max(x_vals)+margin, 2),
                     np.linspace(min(y_vals)-margin, max(y_vals)+margin, 2))

for layer, meta in layers_meta.items():
    z = meta["z"]
    # Faint plane for boundary detection
    ax.plot_surface(xx, yy, np.full_like(xx, z), alpha=0.06, color='grey', edgecolor='none')
    ax.text2D(0.02, z/5.0, layer.upper(), transform=ax.transAxes, color=meta["color"], fontsize=12, fontweight='bold')

# 5b. Draw Intra-Layer Edges & Nodes
for layer_name, meta in layers_meta.items():
    G = multiplex_graph[layer_name]
    z = meta["z"]
    color = meta["color"]
    
    # Draw Layer Edges
    for u, v in G.edges():
        if u in pos_2d and v in pos_2d:
            x_edge = [pos_2d[u][0], pos_2d[v][0]]
            y_edge = [pos_2d[u][1], pos_2d[v][1]]
            z_edge = [z, z]
            
            if u == search_name or v == search_name:
                ax.plot(x_edge, y_edge, z_edge, color='black', alpha=0.9, linewidth=2.5, zorder=6)
            else:
                ax.plot(x_edge, y_edge, z_edge, color=color, alpha=0.3, linewidth=1.0)
            
    # Draw Nodes (shape-coded dynamically by institution, colored by layer)
    for n in pos_2d.keys():
        node_inst = G.nodes[n].get('institution', 'External')
        node_marker = INST_MARKERS.get(node_inst, INST_MARKERS["External"])

        # --- Opacity logic ---
        if n == search_name:
            # Target researcher: always fully visible on every plane
            node_alpha = 0.95
            node_size  = 130
            edge_col   = 'black'
        elif n in neighbors_of_target:
            primary_z = neighbor_first_level.get(n)
            if primary_z == z:
                # This is the layer where the neighbour first connects → full presence
                node_alpha = 0.90
                node_size  = 85
                edge_col   = 'black'
            else:
                # All other layers → ghost marker so spatial position is hinted
                node_alpha = 0.07
                node_size  = 55
                edge_col   = 'none'   # drop the border so it really fades out
        else:
            # Background context nodes: unchanged dim styling
            node_alpha = 0.35
            node_size  = 80
            edge_col   = 'black'

        ax.scatter(
            [pos_2d[n][0]], [pos_2d[n][1]], [z],
            s=node_size,
            c=color,
            marker=node_marker,
            edgecolors=edge_col,
            linewidths=0.7,
            alpha=node_alpha,
            zorder=4,
            depthshade=True,
        )

# 5c. Draw Cross-Layer Couplings & Dynamic Vertical Labels
for node in pos_2d.keys():
    x, y = pos_2d[node]
    z_min, z_max = 1, 4  
    
    attrs = multiplex_graph['co-authorship'].nodes.get(node, {})
    name_display = f"{attrs.get('name', '')} {attrs.get('surname', '')}".strip()
    if not name_display: name_display = node
    
    if node == node_to_highlight:
        # Main Node: Floats above topmost plane
        ax.plot([x, x], [y, y], [z_min, z_max], color='black', linestyle='--', linewidth=3, zorder=10)
        ax.text(x, y, z_max + 0.3, name_display, color='black', fontsize=13, fontweight='bold', ha='center', zorder=12)
        
    elif node in neighbors_of_target:
        # Neighbor Nodes: Float at the level of their highest-priority direct interaction
        z_connected = neighbor_first_level.get(node, 1)
        ax.plot([x, x], [y, y], [z_min, z_max], color='dimgrey', linestyle='--', linewidth=1.2, alpha=0.6, zorder=9)
        ax.text(x, y, z_connected + 0.12, name_display, color='black', fontsize=9, fontweight='semibold', ha='center', alpha=0.8, zorder=11)
        
    else:
        # Background Nodes: Faint coupling line, no text label
        ax.plot([x, x], [y, y], [z_min, z_max], color='grey', linestyle=':', alpha=0.15, linewidth=1)

# 5d. Display adjustments
ax.set_zlim(0.5, 5.0) 
ax.set_axis_off() 
ax.view_init(elev=22, azim=-55) 

# Legend mapping for Node Institution shapes
legend_elements = [plt.Line2D([0], [0], marker=marker, color='w', label=inst,
                              markerfacecolor='darkgrey', markersize=10, markeredgecolor='black')
                   for inst, marker in INST_MARKERS.items()]
ax.legend(handles=legend_elements, loc='upper right', title="Faculty Affiliation")

plt.title(f"Egocentric Multiplex View: {display_name}", fontsize=16, y=0.96)
plt.tight_layout()
plt.show()