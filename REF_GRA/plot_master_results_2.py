import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from config import DATASETS, COMBINED_DATASET_NAME

print("==========================================")
print("  GENERATING MASTER PLOTS FROM CSV DATA")
print("==========================================\n")

os.makedirs("PLOTS", exist_ok=True)

# Okabe-Ito Color Palette
OKABE_ITO = {
    "orange":     "#E69F00",
    "sky_blue":   "#56B4E9",
    "green":      "#009E73",
    "yellow":     "#F0E442",
    "blue":       "#0072B2",
    "vermillion": "#D55E00",
    "purple":     "#CC79A7",
    "black":      "#000000",
    "grey":       "#999999"
}

# Global Plot Styling
plt.rcParams.update({
    'font.size': 12, 'axes.labelsize': 14, 'axes.titlesize': 15,
    'legend.fontsize': 11, 'xtick.labelsize': 11, 'ytick.labelsize': 11,
    'figure.dpi': 300, 'savefig.dpi': 300, 'font.family': 'serif'
})

# ==========================================
# PLOT 1: FRAGILITY OF TIES (EDGE MULTIPLICITY)
# ==========================================
try:
    df_mult = pd.read_csv("RESULTS/MASTER_RQ2_EdgeMultiplicity.csv")
    pivot_mult = df_mult.pivot(index="Dataset", columns="Layers Shared", values="Percentage (%)")
    # Order datasets logically
    order = DATASETS
    pivot_mult = pivot_mult.reindex(order)

    fig, ax = plt.subplots(figsize=(9, 6))
    colors = [OKABE_ITO["sky_blue"], OKABE_ITO["orange"], OKABE_ITO["green"], OKABE_ITO["vermillion"]]
    
    pivot_mult.plot(kind='bar', stacked=True, color=colors, ax=ax, edgecolor='black', linewidth=0.5)
    
    ax.set_title("RQ2: Fragility of Ties (Edge Multiplicity)")
    ax.set_ylabel("Percentage of Connected Pairs (%)")
    ax.set_xlabel("")
    plt.xticks(rotation=15)
    ax.legend(title="Layers Shared", loc="center left", bbox_to_anchor=(1.0, 0.5))
    ax.axhline(y=100, color='black', linewidth=1)
    
    plt.tight_layout()
    plt.savefig("PLOTS/Plot_1_Edge_Multiplicity.png")
    plt.close()
    print("Saved Plot 1: Edge Multiplicity")
except Exception as e: print(f"Skipping Plot 1: {e}")

# ==========================================
# PLOT 2: COST OF AGGREGATION
# ==========================================
try:
    df_agg = pd.read_csv("RESULTS/MASTER_RQ3_AggregationStats.csv")
    df_agg = df_agg.set_index("Dataset").reindex(order).reset_index()

    fig, ax = plt.subplots(figsize=(8, 5))
    
    # Highlight FM because of its massive spike
    colors = [OKABE_ITO["vermillion"] if ds == "FM" else OKABE_ITO["blue"] for ds in df_agg["Dataset"]]
    
    ax.bar(df_agg["Dataset"], df_agg["information_loss_pct"], color=colors, edgecolor='black')
    
    ax.set_title("RQ3: Information Loss from Network Aggregation")
    ax.set_ylabel("Information Destroyed (%)")
    ax.set_xlabel("")
    
    for i, v in enumerate(df_agg["information_loss_pct"]):
        ax.text(i, v + 0.5, f"{v:.1f}%", ha='center', fontweight='bold')
        
    ax.grid(axis='y', linestyle='--', alpha=0.6)
    plt.xticks(rotation=15)
    plt.tight_layout()
    plt.savefig("PLOTS/Plot_2_Aggregation_Cost.png")
    plt.close()
    print("Saved Plot 2: Cost of Aggregation")
except Exception as e: print(f"Skipping Plot 2: {e}")

# ==========================================
# PLOT 3: INSTITUTIONAL SILOS (ASSORTATIVITY)
# ==========================================
try:
    df_top = pd.read_csv("RESULTS/MASTER_RQ1_Topologies.csv")
    df_global_top = df_top[df_top["Dataset"] == COMBINED_DATASET_NAME].copy()

    x = np.arange(len(df_global_top["Layer"]))
    width = 0.35

    fig, ax = plt.subplots(figsize=(9, 6))
    
    rects1 = ax.bar(x - width/2, df_global_top["Observed Assort"], width, 
                    label='Observed Homophily', color=OKABE_ITO["orange"], edgecolor='black')
    rects2 = ax.bar(x + width/2, df_global_top["Null Assort"], width, 
                    label='Random Chance (Null Model)', color=OKABE_ITO["grey"], edgecolor='black')

    ax.set_title("RQ1: Statistical Proof of Institutional Silos (Global Network)")
    ax.set_ylabel("Assortativity Coefficient")
    ax.set_xticks(x)
    ax.set_xticklabels(df_global_top["Layer"])
    ax.legend()
    ax.grid(axis='y', linestyle='--', alpha=0.6)
    
    # Annotate Z-scores
    for i, z in enumerate(df_global_top["Assort Z-Score"]):
        ax.text(x[i] - width/2, df_global_top["Observed Assort"].iloc[i] + 0.02, 
                f"Z={z:.1f}", ha='center', fontsize=10, fontweight='bold', color='black')

    plt.tight_layout()
    plt.savefig("PLOTS/Plot_3_Homophily_Null_Models.png")
    plt.close()
    print("Saved Plot 3: Institutional Assortativity")
except Exception as e: print(f"Skipping Plot 3: {e}")

# ==========================================
# PLOT 4: COMMUNITY PERSISTENCE (ARI)
# ==========================================
try:
    df_ari = pd.read_csv("RESULTS/MASTER_RQ4_CommunityPersistence.csv")
    df_ari = df_ari.set_index("Dataset").reindex(order).reset_index()

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.barplot(data=df_ari, y="Dataset", x="ari_score", color=OKABE_ITO["green"], edgecolor='black', ax=ax)
    
    ax.set_title("RQ4: Community Persistence (Projects vs. Publications)")
    ax.set_xlabel("Adjusted Rand Index (ARI)")
    ax.set_ylabel("")
    ax.set_xlim(0, 1.0)
    
    # Add vertical lines for interpretation thresholds
    ax.axvline(x=0.3, color='grey', linestyle='--', label="Moderate Agreement Threshold")
    ax.axvline(x=0.7, color='black', linestyle='--', label="High Agreement Threshold")
    ax.legend(loc="upper right")
    
    for i, v in enumerate(df_ari["ari_score"]):
        ax.text(v + 0.02, i, f"{v:.2f}", va='center', fontweight='bold')

    plt.tight_layout()
    plt.savefig("PLOTS/Plot_4_Community_Persistence.png")
    plt.close()
    print("Saved Plot 4: Community Persistence")
except Exception as e: print(f"Skipping Plot 4: {e}")

# ==========================================
# PLOT 5: PATHWAYS OF SOCIAL CAPITAL (TRIADS)
# ==========================================
try:
    df_triad = pd.read_csv("RESULTS/MASTER_RQ2_TriadicClosure.csv")
    df_triad_global = df_triad[df_triad["Dataset"] == COMBINED_DATASET_NAME]

    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Simplify hypothesis labels for the chart
    labels = [
        "Project + Project\n→ Co-authorship",
        "Co-author + Co-author\n→ Project",
        "Project + Similarity\n→ Co-authorship"
    ]
    
    bars = ax.bar(labels, df_triad_global["Closure Rate (%)"], color=OKABE_ITO["purple"], edgecolor='black', width=0.5)
    
    ax.set_title("RQ2: Multiplex Triadic Closure (Pathways of Social Capital)")
    ax.set_ylabel("Triadic Closure Rate (%)")
    ax.grid(axis='y', linestyle='--', alpha=0.6)
    
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.3, f"{height:.2f}%", 
                ha='center', va='bottom', fontweight='bold', fontsize=12)

    plt.tight_layout()
    plt.savefig("PLOTS/Plot_5_Triadic_Closure.png")
    plt.close()
    print("Saved Plot 5: Triadic Closure")
except Exception as e: print(f"Skipping Plot 5: {e}")

print("\n✅ All 5 plots generated in ./PLOTS/")