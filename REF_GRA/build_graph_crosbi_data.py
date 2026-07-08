import pandas as pd
import networkx as nx
import itertools
from tqdm import tqdm
import os
from datetime import datetime
from config import DATASETS, EXTERNAL_LABEL

# ==========================================
# CONFIG: WHICH DATASETS TO BUILD
# ==========================================
# Each entry must correspond to a nodes_{name}.csv / edges_{name}.csv / keywords_{name}.csv
# triplet produced by fetch_crosbi_data.py. Add/remove entries here to control which
# per-institution (and combined) graphs get built in a single run.
# DATASETS = ["FIDIT", "FABRI", "FZF", "FM", "FIDIT_FABRI_FZF_FM"]

SIMILARITY_THRESHOLD = 0.025
OUTPUT_DIR = "exported_graphs"


def load_dataset(dataset_name):
    """
    Loads the nodes/edges/keywords CSV triplet for a given dataset name
    (e.g. 'FIDIT' or 'FIDIT_FABRI_FZF_FM'). Returns (None, None, None) and
    prints a warning if any of the three files is missing, so a run over
    DATASETS can skip a dataset instead of crashing the whole batch.
    """
    try:
        df_nodes = pd.read_csv(f"nodes_{dataset_name}.csv")
        df_edges = pd.read_csv(f"edges_{dataset_name}.csv")
        df_keywords = pd.read_csv(f"keywords_{dataset_name}.csv")
    except FileNotFoundError as e:
        print(f"[!] Skipping '{dataset_name}': {e}")
        return None, None, None

    # Ensure null institutions are marked as Unknown
    df_nodes["institution"] = df_nodes["institution"].fillna(EXTERNAL_LABEL)
    return df_nodes, df_edges, df_keywords


def generate_similarity_edges(df_keywords, similarity_threshold=SIMILARITY_THRESHOLD):
    """
    Projects the bipartite author-keyword graph into Layer 3 (Research Similarity)
    via pairwise Jaccard similarity, thresholded at `similarity_threshold`.
    """
    node_keywords = df_keywords.groupby('node_id')['keyword'].apply(set).to_dict()
    nodes_with_keywords = list(node_keywords.keys())
    total_pairs = len(nodes_with_keywords) * (len(nodes_with_keywords) - 1) // 2

    similarity_edges = []
    for u, v in tqdm(itertools.combinations(nodes_with_keywords, 2),
                      desc="  Comparing keywords", total=total_pairs, leave=False):
        set_u, set_v = node_keywords[u], node_keywords[v]
        intersection = set_u.intersection(set_v)
        if not intersection:
            continue

        union = set_u.union(set_v)
        jaccard_index = len(intersection) / len(union)

        if jaccard_index >= similarity_threshold:
            similarity_edges.append({
                "source": u,
                "target": v,
                "layer": "similarity",
                "weight": jaccard_index,  # Weight is the similarity score 0.0 - 1.0
                "year_start": 0,
                "year_end": 2026,
                "context": f"shared_{len(intersection)}_keywords"
            })

    return pd.DataFrame(similarity_edges)


def build_multiplex_graph(df_nodes, df_edges, df_keywords, similarity_threshold=SIMILARITY_THRESHOLD):
    """
    Builds the 4-layer multiplex graph (dict of layer_name -> nx.Graph/DiGraph)
    entirely in memory for one dataset's nodes/edges/keywords frames.
    """
    print("  Generating Research Similarity Edges (Layer 3)...")
    df_similarity = generate_similarity_edges(df_keywords, similarity_threshold)
    print(f"  Created {len(df_similarity)} significant similarity edges (Threshold: {similarity_threshold})")

    # Combine raw edges (co-authorship, mentorship, project) with generated similarity edges
    df_all_edges = pd.concat([df_edges, df_similarity], ignore_index=True)

    # Define the 4 layers. DiGraph for Mentorship to keep direction (Mentor -> Student).
    multiplex_graph = {
        "co-authorship": nx.Graph(),
        "mentorship": nx.DiGraph(),
        "similarity": nx.Graph(),
        "project": nx.Graph()
    }

    # Add all nodes to all layers with attributes (including institution)
    for _, node_row in df_nodes.iterrows():
        node_id = node_row['node_id']
        attrs = {
            "name": node_row['name'],
            "surname": node_row['surname'],
            "institution": node_row['institution']
        }
        for layer_name in multiplex_graph.keys():
            multiplex_graph[layer_name].add_node(node_id, **attrs)

    # Static (time-collapsed) graph: group edges and sum weights.
    # .sum() keeps similarity edges' decimal Jaccard values while
    # co-authorship/project edges accumulate their occurrence counts.
    static_edges = df_all_edges.groupby(['source', 'target', 'layer'])['weight'].sum().reset_index()

    for _, edge in static_edges.iterrows():
        u, v, layer, w = edge['source'], edge['target'], edge['layer'], edge['weight']
        G = multiplex_graph[layer]
        if G.has_edge(u, v):
            G[u][v]['weight'] += w
        else:
            G.add_edge(u, v, weight=w)

    return multiplex_graph


def print_graph_stats(multiplex_graph, df_nodes, dataset_name):
    """Prints basic per-layer topology stats and institutional node distribution for one dataset."""
    print(f"\n--- MULTIPLEX NETWORK STATS [{dataset_name}] ---")
    for layer_name, G in multiplex_graph.items():
        active_nodes = [n for n, d in G.degree() if d > 0]
        print(f"Layer: {layer_name.upper()}")
        print(f"  Total Nodes: {G.number_of_nodes()} (Active: {len(active_nodes)})")
        print(f"  Total Edges: {G.number_of_edges()}")

        if len(active_nodes) > 1:
            subgraph = G.subgraph(active_nodes)
            print(f"  Density of active network: {nx.density(subgraph):.4f}\n")
        else:
            print("  Density: 0.0\n")

    print(f"--- NODE DISTRIBUTION BY INSTITUTION [{dataset_name}] ---")
    print(df_nodes["institution"].value_counts().to_string())


def export_multiplex_graph(multiplex_graph, dataset_name, timestamp, output_dir=OUTPUT_DIR):
    """
    Exports each layer to GraphML + GEXF. Every filename is tagged with the
    dataset acronym (FIDIT / FABRI / FZF / FM / FIDIT_FABRI_FZF_FM) so that
    per-institution and combined runs never collide or overwrite each other,
    e.g. 'co_authorship_FIDIT_12-55-26-06-2026.graphml'.
    """
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n--- EXPORTING GRAPHS [{dataset_name}] ---")
    for layer_name, G in multiplex_graph.items():
        safe_layer = layer_name.replace(" ", "_").replace("-", "_")
        base_name = f"{safe_layer}_{dataset_name}_{timestamp}"

        graphml_path = os.path.join(output_dir, f"{base_name}.graphml")
        nx.write_graphml(G, graphml_path)

        gexf_path = os.path.join(output_dir, f"{base_name}.gexf")
        nx.write_gexf(G, gexf_path)

        print(f"Saved {layer_name}:")
        print(f"  {graphml_path}")
        print(f"  {gexf_path}")


# =========================================================
# MAIN: BUILD & EXPORT EVERY DATASET IN `DATASETS`
# =========================================================
if __name__ == "__main__":
    # One shared timestamp per run, so all layers of all datasets built in this
    # invocation line up under the same TIMESTAMP for downstream rq*.py scripts.
    run_timestamp = datetime.now().strftime("%H-%M-%d-%m-%Y")

    processed, skipped = [], []

    for dataset_name in DATASETS:
        print("\n" + "=" * 60)
        print(f"  BUILDING MULTIPLEX GRAPH: {dataset_name}")
        print("=" * 60)

        df_nodes, df_edges, df_keywords = load_dataset(dataset_name)
        if df_nodes is None:
            skipped.append(dataset_name)
            continue

        multiplex_graph = build_multiplex_graph(df_nodes, df_edges, df_keywords)
        print_graph_stats(multiplex_graph, df_nodes, dataset_name)
        export_multiplex_graph(multiplex_graph, dataset_name, run_timestamp)
        processed.append(dataset_name)

    print("\n" + "=" * 60)
    print("  BATCH SUMMARY")
    print("=" * 60)
    print(f"Processed ({len(processed)}): {', '.join(processed) if processed else '-'}")
    print(f"Skipped   ({len(skipped)}): {', '.join(skipped) if skipped else '-'}")
    print(f"Run timestamp: {run_timestamp}")
    print("\n✅ Done.")