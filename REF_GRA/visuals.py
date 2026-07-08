import os
import networkx as nx
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import norm
import itertools
from tqdm import tqdm
import warnings

from config import DATASETS, INSTITUTION_COLORS as INST_COLORS, INSTITUTION_MARKERS as INST_MARKERS

warnings.filterwarnings("ignore")

# Import your graph builder
from builder import build_multiplex_graph

print("==================================================")
print("  GENERATING PUBLICATION-READY PLOTS (ON-THE-FLY)")
print("==================================================\n")

# ==========================================
# 0. SETUP: DIRECTORIES, DATA & STYLING
# ==========================================
os.makedirs("PLOTS", exist_ok=True)

# DATASETS = ["FIDIT", "FABRI", "FZF", "FM", "FIDIT_FABRI_FZF_FM"]

# Okabe-Ito Color Palette
OKABE_ITO = {
    "orange":     "#E69F00",
    "sky_blue":   "#56B4E9",
    "green":      "#009E73",
    "yellow":     "#F0E442",
    "blue":       "#0072B2",
    "vermillion": "#D55E00",
    "purple":     "#CC79A7",
    "black":      "#000000"
}

# Institutional Color Mapping
# INST_COLORS = {
#     "FIDIT": OKABE_ITO["vermillion"],
#     "FABRI": OKABE_ITO["sky_blue"],
#     "FZF":   "gold", # Tweaked for scatter visibility
#     "FM":    OKABE_ITO["black"],
#     "External": "grey",
#     "Unknown": "lightgrey"
# }

# Institutional Markers for Plot 4
# INST_MARKERS = {
#     "FIDIT": "^",
#     "FABRI": "*",
#     "FZF": "s",
#     "FM": "D",
#     "External": "o",
#     "Unknown": "o"
# }

plt.rcParams.update({
    'font.size': 12, 'axes.labelsize': 14, 'axes.titlesize': 16,
    'legend.fontsize': 11, 'xtick.labelsize': 11, 'ytick.labelsize': 11,
    'figure.dpi': 300, 'savefig.dpi': 300, 'font.family': 'serif'
})

def generate_null_model(G_active):
    """Fast degree-preserving randomization for Plot 1."""
    G_null = G_active.copy()
    num_edges = G_null.number_of_edges()
    if num_edges > 0:
        try:
            if G_null.is_directed():
                nx.directed_edge_swap(G_null, nswap=num_edges, max_tries=num_edges*10)
            else:
                nx.double_edge_swap(G_null, nswap=num_edges, max_tries=num_edges*10)
        except:
            pass
    return G_null

# ==========================================
# BATCH PROCESSING LOOP
# ==========================================
for ds in tqdm(DATASETS, desc="Processing Datasets", colour="blue"):
    
    # 1. Build Graph in RAM
    multiplex_graph = build_multiplex_graph(ds, similarity_threshold=0.025)
    if multiplex_graph is None:
        continue
        
    layer_names = list(multiplex_graph.keys())

    # ==========================================
    # PLOT 1: NULL MODEL SIGNIFICANCE
    # ==========================================
    # Using 'project' layer to test homophily
    G_proj = multiplex_graph["project"]
    active_proj = [n for n, d in G_proj.degree() if d > 0]
    G_proj_act = G_proj.subgraph(active_proj).copy()
    
    if G_proj_act.number_of_nodes() > 2:
        try:
            obs_assort = nx.attribute_assortativity_coefficient(G_proj_act, 'institution')
            if not np.isnan(obs_assort):
                null_assorts = []
                for _ in range(10): # 10 iterations for speed
                    G_null = generate_null_model(G_proj_act)
                    try:
                        null_assorts.append(nx.attribute_assortativity_coefficient(G_null, 'institution'))
                    except: pass
                
                if len(null_assorts) > 2:
                    null_mean, null_std = np.mean(null_assorts), np.std(null_assorts)
                    if null_std == 0: null_std = 0.001
                    
                    x = np.linspace(-0.2, 1.0, 500)
                    y = norm.pdf(x, null_mean, null_std)
                    
                    fig, ax = plt.subplots(figsize=(8, 5))
                    ax.plot(x, y, color='grey', linewidth=2, label="Null Model (Randomized)")
                    ax.fill_between(x, y, color='lightgrey', alpha=0.5)
                    ax.axvline(x=obs_assort, color=OKABE_ITO["vermillion"], linestyle='--', linewidth=3, label=f"Observed ({obs_assort:.2f})")
                    ax.axvline(x=null_mean, color=OKABE_ITO["black"], linestyle=':', linewidth=2)
                    
                    ax.set_title(f"[{ds}] Institutional Assortativity vs Random Chance")
                    ax.set_xlabel("Assortativity (Homophily)")
                    ax.set_ylabel("Probability Density")
                    ax.legend(loc='upper right')
                    plt.tight_layout()
                    plt.savefig(f"PLOTS/{ds}_1_Null_Model_Significance.png")
                    plt.close()
        except Exception as e:
            pass # Skip if node attributes fail (e.g. single node dataset)

    # ==========================================
    # PLOT 2: STRUCTURAL TWINS (Jaccard Heatmap)
    # ==========================================
    sim_matrix = pd.DataFrame(index=layer_names, columns=layer_names, dtype=float)
    edge_sets = {l: set(tuple(sorted((u, v))) for u, v in multiplex_graph[l].edges()) for l in layer_names}

    for l1, l2 in itertools.product(layer_names, repeat=2):
        if l1 == l2: sim_matrix.loc[l1, l2] = 1.0
        else:
            s1, s2 = edge_sets[l1], edge_sets[l2]
            union = len(s1.union(s2))
            sim_matrix.loc[l1, l2] = len(s1.intersection(s2)) / union if union > 0 else 0.0

    sim_matrix.columns = [c.capitalize() for c in sim_matrix.columns]
    sim_matrix.index = [i.capitalize() for i in sim_matrix.index]

    try:
        g = sns.clustermap(sim_matrix, annot=True, cmap="YlGnBu", fmt=".3f", 
                           figsize=(7, 6), vmin=0, vmax=0.5, cbar_kws={'label': 'Jaccard Edge Overlap'})
        g.fig.suptitle(f"[{ds}] Layer Similarity & Structural Twins", y=1.02, fontsize=14)
        plt.savefig(f"PLOTS/{ds}_2_Structural_Twins.png", bbox_inches='tight')
        plt.close()
    except ValueError:
        pass # Fails if variance is exactly 0 across all layers

    # ==========================================
    # PLOT 3 & 4 DATA PREP (Aggregation & Cartography)
    # ==========================================
    G_agg = nx.Graph()
    G_supra = nx.DiGraph()
    all_nodes = set()

    for layer_name, G in multiplex_graph.items():
        all_nodes.update(G.nodes())
        for u, v, data in G.edges(data=True):
            w = data.get('weight', 1.0)
            if G_agg.has_edge(u, v): G_agg[u][v]['weight'] += w
            else: G_agg.add_edge(u, v, weight=w)
            
            G_supra.add_edge(f"{u}_{layer_name}", f"{v}_{layer_name}", weight=w)
            if not G.is_directed(): G_supra.add_edge(f"{v}_{layer_name}", f"{u}_{layer_name}", weight=w)

    for node in all_nodes:
        for l1, l2 in itertools.combinations(layer_names, 2):
            n1, n2 = f"{node}_{l1}", f"{node}_{l2}"
            if G_supra.has_node(n1) and G_supra.has_node(n2):
                G_supra.add_edge(n1, n2, weight=1.0)
                G_supra.add_edge(n2, n1, weight=1.0)

    pr_agg = nx.pagerank(G_agg, weight='weight')
    pr_supra = nx.pagerank(G_supra, weight='weight')
    pr_multi = {node: sum(pr_supra.get(f"{node}_{l}", 0.0) for l in layer_names) for node in all_nodes}

    node_data = []
    for node in all_nodes:
        inst = multiplex_graph["co-authorship"].nodes.get(node, {}).get('institution', 'Unknown')
        if inst not in INST_COLORS: inst = "External"
        
        k_layers = [(multiplex_graph[l].out_degree(node) + multiplex_graph[l].in_degree(node)) if multiplex_graph[l].is_directed() else multiplex_graph[l].degree(node) for l in layer_names]
        o_i = sum(k_layers)
        p_i = 1.0 - sum((k / o_i)**2 for k in k_layers) if o_i > 0 else 0.0
        
        if o_i > 0: 
            node_data.append({"node": node, "Inst": inst, "Mono_PR": pr_agg.get(node, 0), "Multi_PR": pr_multi.get(node, 0), "P": p_i, "Degree": o_i})

    df_nodes = pd.DataFrame(node_data)
    if not df_nodes.empty:
        df_nodes["Mono_Rank"] = df_nodes["Mono_PR"].rank(ascending=False).astype(int)
        df_nodes["Multi_Rank"] = df_nodes["Multi_PR"].rank(ascending=False).astype(int)

        # ==========================================
        # PLOT 3: COST OF AGGREGATION
        # ==========================================
        fig, ax = plt.subplots(figsize=(8, 8))
        
        # We plot scatter using a loop to assign proper shapes per institution
        for inst_key in df_nodes['Inst'].unique():
            subset = df_nodes[df_nodes['Inst'] == inst_key]
            ax.scatter(subset["Mono_Rank"], subset["Multi_Rank"], 
                       color=INST_COLORS[inst_key], marker=INST_MARKERS[inst_key], 
                       s=70, alpha=0.8, edgecolor='black', label=inst_key)

        max_rank = max(df_nodes["Mono_Rank"].max(), df_nodes["Multi_Rank"].max())
        ax.plot([1, max_rank], [1, max_rank], color='grey', linestyle='--', label="y=x (No Info Loss)")
        
        ax.set_xlim(max_rank + 5, -5) # Invert axis
        ax.set_ylim(max_rank + 5, -5)
        ax.set_xlabel("Monoplex Rank (Aggregated)")
        ax.set_ylabel("Multiplex Rank (Total Overlap)")
        ax.set_title(f"[{ds}] The Cost of Aggregation")
        ax.legend(title="Faculty")
        ax.grid(True, linestyle=':', alpha=0.6)
        
        plt.tight_layout()
        plt.savefig(f"PLOTS/{ds}_3_Aggregation_Cost.png")
        plt.close()

        # ==========================================
        # PLOT 4: ROLE CARTOGRAPHY
        # ==========================================
        fig, ax = plt.subplots(figsize=(9, 7))
        for inst_key in df_nodes['Inst'].unique():
            subset = df_nodes[df_nodes['Inst'] == inst_key]
            ax.scatter(subset["P"], subset["Degree"], 
                       color=INST_COLORS[inst_key], marker=INST_MARKERS[inst_key], 
                       s=80, alpha=0.85, edgecolor='black', label=inst_key)

        ax.axvline(x=0.5, color='grey', linestyle='--')
        ax.axhline(y=df_nodes["Degree"].median() * 2, color='grey', linestyle='--')
        ax.set_xlabel("Participation Coefficient ($P$)")
        ax.set_ylabel("Total Multiplex Degree")
        ax.set_title(f"[{ds}] Role Cartography: Boundary Spanners")
        ax.legend(title="Faculty")
        ax.grid(True, linestyle=':', alpha=0.6)
        
        plt.tight_layout()
        plt.savefig(f"PLOTS/{ds}_4_Role_Cartography.png")
        plt.close()

    # ==========================================
    # PLOT 5: SILOS VS BRIDGES
    # ==========================================
    bar_data = []
    for layer_name, G in multiplex_graph.items():
        internal_edges, external_edges = 0, 0
        for u, v in G.edges():
            inst_u = multiplex_graph["co-authorship"].nodes.get(u, {}).get("institution", "Unknown")
            inst_v = multiplex_graph["co-authorship"].nodes.get(v, {}).get("institution", "Unknown")
            if inst_u == "Unknown" or inst_v == "Unknown": continue
                
            if inst_u == inst_v: internal_edges += 1
            else: external_edges += 1
                
        total = internal_edges + external_edges
        if total > 0:
            bar_data.append({
                "Layer": layer_name.capitalize(),
                "Internal (Silo)": (internal_edges / total) * 100,
                "External (Bridge)": (external_edges / total) * 100
            })

    if bar_data:
        df_bars = pd.DataFrame(bar_data).set_index("Layer")
        fig, ax = plt.subplots(figsize=(8, 6))
        df_bars.plot(kind='bar', stacked=True, ax=ax, color=[OKABE_ITO["blue"], OKABE_ITO["vermillion"]], edgecolor='black')
        ax.set_ylabel("Percentage of Edges (%)")
        ax.set_title(f"[{ds}] Inter-Institutional Dynamics: Silos vs. Bridges")
        ax.axhline(y=50, color='black', linestyle='--', alpha=0.5)
        
        for c in ax.containers:
            for v in c:
                height = v.get_height()
                if height > 5:
                    ax.text(v.get_x() + v.get_width()/2, v.get_y() + height/2, 
                            f"{height:.1f}%", ha='center', va='center', color='white', fontweight='bold')

        plt.xticks(rotation=0)
        plt.legend(loc="upper right", bbox_to_anchor=(1.35, 1))
        plt.tight_layout()
        plt.savefig(f"PLOTS/{ds}_5_Silos_Vs_Bridges.png")
        plt.close()

print("\n✅ All publication-ready plots generated in ./PLOTS/ directory!")