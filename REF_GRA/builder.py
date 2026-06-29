"""
A modularized version of the build_graph_crosbi_data.py script.
"""

import pandas as pd
import networkx as nx
import itertools

def build_multiplex_graph(dataset_name, similarity_threshold=0.025):
    """
    Reads nodes, edges, and keywords for a given dataset name.
    Calculates Jaccard similarity, builds the 4-layer multiplex graph,
    and returns it entirely in memory.
    """
    # Load the data
    try:
        df_nodes = pd.read_csv(f"nodes_{dataset_name}.csv")
        df_edges = pd.read_csv(f"edges_{dataset_name}.csv")
        df_keywords = pd.read_csv(f"keywords_{dataset_name}.csv")
    except FileNotFoundError as e:
        print(f"\n[!] Error loading {dataset_name}: {e}")
        return None

    df_nodes["institution"] = df_nodes["institution"].fillna("Unknown")

    # Generate Research Similarity Edges (Jaccard)
    node_keywords = df_keywords.groupby('node_id')['keyword'].apply(set).to_dict()
    similarity_edges = []
    nodes_with_keywords = list(node_keywords.keys())

    for u, v in itertools.combinations(nodes_with_keywords, 2):
        set_u = node_keywords[u]
        set_v = node_keywords[v]
        intersection = set_u.intersection(set_v)
        
        if not intersection: continue
            
        union = set_u.union(set_v)
        jaccard_index = len(intersection) / len(union)
        
        if jaccard_index >= similarity_threshold:
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

    # Initialize Graph Dictionary
    multiplex_graph = {
        "co-authorship": nx.Graph(),
        "mentorship": nx.DiGraph(),
        "similarity": nx.Graph(),
        "project": nx.Graph()
    }

    # Add Nodes
    for _, node_row in df_nodes.iterrows():
        node_id = node_row['node_id']
        attrs = {
            "name": node_row['name'], 
            "surname": node_row['surname'],
            "institution": node_row['institution']
        }
        for layer_name in multiplex_graph.keys():
            multiplex_graph[layer_name].add_node(node_id, **attrs)

    # Aggregate Edges
    static_edges = df_all_edges.groupby(['source', 'target', 'layer'])['weight'].sum().reset_index()

    for _, edge in static_edges.iterrows():
        u, v, layer, w = edge['source'], edge['target'], edge['layer'], edge['weight']
        G = multiplex_graph[layer]
        
        if G.has_edge(u, v):
            G[u][v]['weight'] += w
        else:
            G.add_edge(u, v, weight=w)

    return multiplex_graph