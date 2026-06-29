import os
import pandas as pd
from tqdm import tqdm
import warnings

# Suppress minor pandas/networkx warnings for a clean CLI output
warnings.filterwarnings("ignore")

# Import the builder and our custom RQ modules
from builder import build_multiplex_graph
from rq1_script import rq1_process_graph
from rq2_script import rq2_process_graph
from rq3_script import rq3_process_graph
from rq4_script import rq4_process_graph

print("==================================================")
print("  MULTI-INSTITUTIONAL M-ONA PIPELINE ENGINE")
print("==================================================\n")

# Define the datasets we want to analyze
DATASETS = ["FIDIT", "FABRI", "FZF", "FM", "FIDIT_FABRI_FZF_FM"]

# Create results directory
os.makedirs("RESULTS", exist_ok=True)

# Storage lists for our aggregated master tables
agg_rq1 = []
agg_rq2_mult = []
agg_rq2_triads = []
agg_rq3_stats = []
agg_rq4_ari = []
agg_rq4_elite = []

# ==========================================
# PIPELINE EXECUTION
# ==========================================

# Use tqdm for the outer dataset loop
for ds in tqdm(DATASETS, desc="Processing Datasets", unit="dataset", colour="green"):
    
    # 1. Build Graph in RAM (No disk loading overhead!)
    G_multi = build_multiplex_graph(ds, similarity_threshold=0.025)
    
    if G_multi is None:
        continue # Skip if files are missing

    # -----------------------------------------
    # RQ1: Topologies & Homophily Null Models
    # -----------------------------------------
    # Note: Reduce null_iterations to 5 or 10 if it takes too long
    df_rq1 = rq1_process_graph(G_multi, null_iterations=10)
    df_rq1.insert(0, "Dataset", ds) # Tag with scope
    agg_rq1.append(df_rq1)

    # -----------------------------------------
    # RQ2: Multiplexity & Reinforcement
    # -----------------------------------------
    df_mult, sim_mat, twins_str, df_triads = rq2_process_graph(G_multi)
    df_mult.insert(0, "Dataset", ds)
    df_triads.insert(0, "Dataset", ds)
    agg_rq2_mult.append(df_mult)
    agg_rq2_triads.append(df_triads)
    
    # (Optional: You could save sim_mat directly to a CSV here if you want per-dataset matrices)

    # -----------------------------------------
    # RQ3: Information Destruction (Aggregation)
    # -----------------------------------------
    df_rq3_full, df_internal, stats_dict = rq3_process_graph(G_multi)
    # stats_dict -> {'rho': x, 'p_value': y, 'information_loss_pct': z}
    stats_dict["Dataset"] = ds
    agg_rq3_stats.append(pd.DataFrame([stats_dict]))

    # -----------------------------------------
    # RQ4: Core-Periphery & Persistence
    # -----------------------------------------
    ari_dict, df_core, core_stats_dict, df_inst_breakdown = rq4_process_graph(G_multi)
    
    # 1. Store ARI Results
    ari_dict["Dataset"] = ds
    agg_rq4_ari.append(pd.DataFrame([ari_dict]))
    
    # 2. Store Elite Core Breakdown
    if not df_inst_breakdown.empty:
        # Prevent "Dataset" column from being inserted multiple times if the loop re-uses references
        if "Dataset" not in df_inst_breakdown.columns:
            df_inst_breakdown.insert(0, "Dataset", ds)
        agg_rq4_elite.append(df_inst_breakdown)

print("\n\n==================================================")
print("  ANALYSIS COMPLETE. SAVING AGGREGATED RESULTS")
print("==================================================\n")

# Combine and export RQ1
pd.concat(agg_rq1, ignore_index=True).to_csv("RESULTS/MASTER_RQ1_Topologies.csv", index=False)

# Combine and export RQ2
pd.concat(agg_rq2_mult, ignore_index=True).to_csv("RESULTS/MASTER_RQ2_EdgeMultiplicity.csv", index=False)
pd.concat(agg_rq2_triads, ignore_index=True).to_csv("RESULTS/MASTER_RQ2_TriadicClosure.csv", index=False)

# Combine and export RQ3
pd.concat(agg_rq3_stats, ignore_index=True).to_csv("RESULTS/MASTER_RQ3_AggregationStats.csv", index=False)

# Combine and export RQ4
pd.concat(agg_rq4_ari, ignore_index=True).to_csv("RESULTS/MASTER_RQ4_CommunityPersistence.csv", index=False)
if agg_rq4_elite:
    pd.concat(agg_rq4_elite, ignore_index=True).to_csv("RESULTS/MASTER_RQ4_EliteCoreBreakdown.csv", index=False)

print("✅ Pipeline executed successfully!")
print("📁 Check the '/RESULTS' directory for your master comparison tables.")