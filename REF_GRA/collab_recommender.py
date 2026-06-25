import pandas as pd
import networkx as nx

import loading_graph


multiplex_graph = loading_graph.load_graph()

print("==========================================")
print("  ANALYSIS E: COLLABORATION RECOMENDER")
print("==========================================\n")

# Get institution mapping
node_institutions = {}
for node in multiplex_graph["similarity"].nodes():
    node_institutions[node] = multiplex_graph["similarity"].nodes[node].get("institution", "Unknown")

recs = []

# Iterate through similarity edges (weighted by Jaccard similarity)
for u, v, data in multiplex_graph["similarity"].edges(data=True):
    weight = data.get('weight', 0)
    
    # 1. Filter: They must NOT have a co-authorship edge
    if not multiplex_graph["co-authorship"].has_edge(u, v):
        
        # 2. Filter: They must NOT have a project edge
        if not multiplex_graph["project"].has_edge(u, v):
            
            inst_u = node_institutions.get(u, "Unknown")
            inst_v = node_institutions.get(v, "Unknown")
            
            # 3. Filter: Only keep cross-institutional gaps (no unknowns, no externals for noise)
            if inst_u != "Unknown" and inst_v != "Unknown" and inst_u != "External" and inst_v != "External":
                if True: # inst_u != inst_v:
                    # Get display names
                    attrs_u = multiplex_graph["similarity"].nodes[u]
                    attrs_v = multiplex_graph["similarity"].nodes[v]
                    name_u = f"{attrs_u.get('name', '')} {attrs_u.get('surname', '')}".strip()
                    name_v = f"{attrs_v.get('name', '')} {attrs_v.get('surname', '')}".strip()
                    
                    recs.append({
                        "Researcher A": name_u,
                        "Inst A": inst_u,
                        "Researcher B": name_v,
                        "Inst B": inst_v,
                        "Intellectual Proximity (Jaccard)": f"{weight:.4f}"
                    })

df_recs = pd.DataFrame(recs)

if not df_recs.empty:
    # Sort by the highest Jaccard similarity
    df_recs = df_recs.sort_values(by="Intellectual Proximity (Jaccard)", ascending=False)
    print("--- TOP 10 INTER-DEPARTMENTAL RESEARCH SYNERGIES ---")
    print("(High keyword overlap, but 0 publications or projects together)")
    print(df_recs.head(10).to_string(index=False))
else:
    print("No gaps found!")