import os
import traceback
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

from config import DATASETS

print("==================================================")
print("  MULTI-INSTITUTIONAL M-ONA PIPELINE ENGINE")
print("==================================================\n")

# Define the datasets we want to analyze
# DATASETS = ["FIDIT", "FABRI", "FZF", "FM", "FIDIT_FABRI_FZF_FM"]
NULL_ITERATIONS = 1000  # Passed through to RQ1's degree-preserving null models

# Create results directory
os.makedirs("RESULTS", exist_ok=True)

# Storage lists for our aggregated master tables
agg_rq1 = []
agg_rq2_mult = []
agg_rq2_triads = []
agg_rq2_simmat = []      # NEW: previously computed then discarded
agg_rq2_twins = []       # NEW: previously computed then discarded
agg_rq3_stats = []
agg_rq3_full = []        # NEW: full per-node PageRank/participation/constraint table
agg_rq3_ranked = []      # NEW: ranked/internal per-node table (Mono_Rank, Multi_Rank, Rank_Shift)
agg_rq4_ari = []
agg_rq4_core = []        # NEW: per-node core_number/stratum
agg_rq4_corestats = []   # NEW: max_k / elite / semi / periphery counts
agg_rq4_elite = []

# Manifest: tracks exactly what happened to every dataset in this run, so a
# partial or failed run is always auditable rather than silently incomplete.
manifest_rows = []

# ==========================================
# PIPELINE EXECUTION
# ==========================================

for ds in tqdm(DATASETS, desc="Processing Datasets", unit="dataset", colour="green"):

    manifest_entry = {"Dataset": ds, "Status": "Unknown", "Failed Stage": None, "Error": None}

    # -----------------------------------------
    # 1. Build Graph in RAM (No disk loading overhead!)
    # -----------------------------------------
    try:
        G_multi = build_multiplex_graph(ds, similarity_threshold=0.025)
    except Exception as e:
        manifest_entry.update({"Status": "Failed", "Failed Stage": "build_multiplex_graph", "Error": str(e)})
        manifest_rows.append(manifest_entry)
        print(f"\n[!] '{ds}' failed while building the graph: {e}")
        traceback.print_exc()
        continue

    if G_multi is None:
        manifest_entry.update({"Status": "Skipped", "Failed Stage": "build_multiplex_graph",
                                "Error": "nodes/edges/keywords CSVs not found for this dataset"})
        manifest_rows.append(manifest_entry)
        continue

    # Everything below is wrapped per-dataset: if one RQ stage throws on this
    # particular dataset (e.g. a degenerate subgraph), we record it and move on
    # to the next dataset instead of losing every dataset already processed.
    try:
        # -----------------------------------------
        # RQ1: Topologies & Homophily Null Models
        # -----------------------------------------
        df_rq1 = rq1_process_graph(G_multi, null_iterations=NULL_ITERATIONS)
        df_rq1.insert(0, "Dataset", ds)
        agg_rq1.append(df_rq1)

        # -----------------------------------------
        # RQ2: Multiplexity & Reinforcement
        # -----------------------------------------
        df_mult, sim_mat, twins_dict, df_triads = rq2_process_graph(G_multi)
        df_mult.insert(0, "Dataset", ds)
        df_triads.insert(0, "Dataset", ds)
        agg_rq2_mult.append(df_mult)
        agg_rq2_triads.append(df_triads)

        # NEW: persist the layer-similarity matrix (previously discarded).
        # Melt the layer x layer square matrix into a long (Dataset, Layer A, Layer B, Jaccard) table.
        sim_long = sim_mat.reset_index().melt(id_vars="index", var_name="Layer B", value_name="Jaccard")
        sim_long = sim_long.rename(columns={"index": "Layer A"})
        sim_long.insert(0, "Dataset", ds)
        agg_rq2_simmat.append(sim_long)

        # NEW: persist the structural-twins summary (previously discarded).
        twins_row = dict(twins_dict)
        twins_row["Dataset"] = ds
        agg_rq2_twins.append(pd.DataFrame([twins_row]))

        # -----------------------------------------
        # RQ3: Information Destruction (Aggregation)
        # -----------------------------------------
        df_rq3_full, df_internal, stats_dict = rq3_process_graph(G_multi)
        stats_dict = dict(stats_dict)
        stats_dict["Dataset"] = ds
        agg_rq3_stats.append(pd.DataFrame([stats_dict]))

        # NEW: persist the full per-node metrics table (previously discarded).
        # This is the table the paper's "Hidden Brokers" / structural-hole-spanner
        # claims are actually drawn from, so it needs to survive the run.
        df_rq3_full = df_rq3_full.copy()
        df_rq3_full.insert(0, "Dataset", ds)
        agg_rq3_full.append(df_rq3_full)

        df_internal = df_internal.copy()
        df_internal.insert(0, "Dataset", ds)
        agg_rq3_ranked.append(df_internal)

        # -----------------------------------------
        # RQ4: Core-Periphery & Persistence
        # -----------------------------------------
        ari_dict, df_core, core_stats_dict, df_inst_breakdown = rq4_process_graph(G_multi)

        # 1. Store ARI Results
        ari_dict = dict(ari_dict)
        ari_dict["Dataset"] = ds
        agg_rq4_ari.append(pd.DataFrame([ari_dict]))

        # NEW: persist the per-node core decomposition (previously discarded).
        df_core = df_core.copy()
        df_core.insert(0, "Dataset", ds)
        agg_rq4_core.append(df_core)

        # NEW: persist the core summary stats (max_k / elite / semi / periphery counts).
        # `thresholds` is a nested dict; flatten it so the row stays CSV-friendly.
        core_stats_row = {k: v for k, v in core_stats_dict.items() if k != "thresholds"}
        core_stats_row.update({f"threshold_{k}": v for k, v in core_stats_dict.get("thresholds", {}).items()})
        core_stats_row["Dataset"] = ds
        agg_rq4_corestats.append(pd.DataFrame([core_stats_row]))

        # 2. Store Elite Core Breakdown
        # FIX: an empty breakdown (e.g. an all-External or all-empty elite core) used to
        # be silently dropped, making the dataset indistinguishable from one that never
        # ran. Insert an explicit zero-row instead so it still shows up in the master table.
        if df_inst_breakdown is None or df_inst_breakdown.empty:
            df_inst_breakdown = pd.DataFrame([{"Institution": "None (empty or External-only elite core)", "Count": 0}])
        else:
            df_inst_breakdown = df_inst_breakdown.copy()

        if "Dataset" not in df_inst_breakdown.columns:
            df_inst_breakdown.insert(0, "Dataset", ds)
        agg_rq4_elite.append(df_inst_breakdown)

        manifest_entry["Status"] = "Success"

    except Exception as e:
        manifest_entry.update({"Status": "Failed", "Failed Stage": "RQ processing", "Error": str(e)})
        print(f"\n[!] '{ds}' failed during RQ processing: {e}")
        traceback.print_exc()
        # Whatever this dataset had already appended to the agg_* lists before the
        # exception stays in place; we only skip what came after the failure point.

    manifest_rows.append(manifest_entry)

print("\n\n==================================================")
print("  ANALYSIS COMPLETE. SAVING AGGREGATED RESULTS")
print("==================================================\n")


def save_master(frames, filename):
    """
    Concatenates and writes one MASTER csv, wrapped so that a problem with one
    table (e.g. an empty list because every dataset failed at that stage) can't
    prevent the other, healthy tables from being saved.
    """
    try:
        if not frames:
            print(f"[!] Skipping {filename}: no data collected for any dataset.")
            return
        pd.concat(frames, ignore_index=True).to_csv(f"RESULTS/{filename}", index=False)
        print(f"Saved RESULTS/{filename}")
    except Exception as e:
        print(f"[!] Failed to save {filename}: {e}")


# RQ1
save_master(agg_rq1, "MASTER_RQ1_Topologies.csv")

# RQ2
save_master(agg_rq2_mult, "MASTER_RQ2_EdgeMultiplicity.csv")
save_master(agg_rq2_triads, "MASTER_RQ2_TriadicClosure.csv")
save_master(agg_rq2_simmat, "MASTER_RQ2_LayerSimilarity.csv")     # NEW
save_master(agg_rq2_twins, "MASTER_RQ2_StructuralTwins.csv")      # NEW

# RQ3
save_master(agg_rq3_stats, "MASTER_RQ3_AggregationStats.csv")
save_master(agg_rq3_full, "MASTER_RQ3_NodeMetrics_Full.csv")      # NEW
save_master(agg_rq3_ranked, "MASTER_RQ3_NodeMetrics_Ranked.csv")  # NEW

# RQ4
save_master(agg_rq4_ari, "MASTER_RQ4_CommunityPersistence.csv")
save_master(agg_rq4_core, "MASTER_RQ4_CoreDecomposition.csv")     # NEW
save_master(agg_rq4_corestats, "MASTER_RQ4_CoreStats.csv")        # NEW
save_master(agg_rq4_elite, "MASTER_RQ4_EliteCoreBreakdown.csv")

# Manifest: always written, even if every single dataset failed, so a bad run
# is immediately visible instead of looking like a normal empty result.
pd.DataFrame(manifest_rows).to_csv("RESULTS/RUN_MANIFEST.csv", index=False)
print("Saved RESULTS/RUN_MANIFEST.csv")

n_success = sum(1 for r in manifest_rows if r["Status"] == "Success")
n_skipped = sum(1 for r in manifest_rows if r["Status"] == "Skipped")
n_failed = sum(1 for r in manifest_rows if r["Status"] == "Failed")

print(f"\nDatasets — Success: {n_success} | Skipped: {n_skipped} | Failed: {n_failed}")
if n_failed or n_skipped:
    print("See RESULTS/RUN_MANIFEST.csv for details on which datasets/stages had issues.")

print("\n✅ Pipeline finished.")
print("📁 Check the '/RESULTS' directory for your master comparison tables.")