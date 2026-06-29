import networkx as nx
import pandas as pd
import loading_graph


multiplex_graph = loading_graph.load_graph()

print("==========================================")
print("  RQ3: MONOPLEX VS. MULTIPLEX CENTRALITY")
print("==========================================\n")

degree_data = []

# Calculate degree centralities across all layers
for node in multiplex_graph["co-authorship"].nodes():
    attrs = multiplex_graph["co-authorship"].nodes[node]
    full_name = f"{attrs.get('name', '')} {attrs.get('surname', '')}".strip()
    institution = attrs.get('institution', 'Unknown')
    
    row = {
        "node_id": node, 
        "researcher": full_name, 
        "institution": institution
    }
    
    total_multiplex_degree = 0
    for layer_name, G in multiplex_graph.items():
        if G.is_directed():
            d = G.out_degree(node) + G.in_degree(node)
        else:
            d = G.degree(node)
        row[f"deg_{layer_name}"] = d
        total_multiplex_degree += d
        
    row["multiplex_degree"] = total_multiplex_degree
    degree_data.append(row)

df_analysis = pd.DataFrame(degree_data)

# 1. Rank by standard Monoplex (Co-authorship) degree
df_analysis["coauth_rank"] = df_analysis["deg_co-authorship"].rank(ascending=False, method="min").astype(int)

# 2. Rank by Multiplex Degree Overlap
df_analysis["multiplex_rank"] = df_analysis["multiplex_degree"].rank(ascending=False, method="min").astype(int)

# 3. Calculate Rank Shift (positive means they rank higher in multiplex than in monoplex)
df_analysis["rank_shift"] = df_analysis["coauth_rank"] - df_analysis["multiplex_rank"]

# Filter out inactive nodes
df_analysis = df_analysis[df_analysis["multiplex_degree"] > 0]

# Display Top 10 by Co-authorship
print("--- TOP 10 BY MONOPLEX CO-AUTHORSHIP DEGREE ---")
print(df_analysis.sort_values(by="coauth_rank").head(10)[["researcher", "institution", "deg_co-authorship", "coauth_rank", "multiplex_rank"]].to_string(index=False))
print("\n")

# Display Top 10 by Multiplex Degree
print("--- TOP 10 BY MULTIPLEX DEGREE OVERLAP ---")
print(df_analysis.sort_values(by="multiplex_rank").head(10)[["researcher", "institution", "multiplex_degree", "coauth_rank", "multiplex_rank"]].to_string(index=False))
print("\n")

# Display "Hidden Brokers" (High rank shift: people who are much more important in the multiplex view than in publications alone)
# Remove external affiliations
df_internal = df_analysis[df_analysis["institution"] != "External"].copy()

print("--- TOP 10 'HIDDEN BROKERS' (Highest Positive Rank Shift With Filtered Externals) ---")
df_brokers = df_internal.sort_values(by="rank_shift", ascending=False)
print(df_brokers.head(10)[["researcher", "institution", "coauth_rank", "multiplex_rank", "rank_shift", "deg_project", "deg_mentorship"]].to_string(index=False))