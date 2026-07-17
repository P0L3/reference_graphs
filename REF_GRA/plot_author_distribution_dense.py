import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import warnings

warnings.filterwarnings("ignore")

# Import the datasets list from your configuration
from config import DATASETS, INSTITUTION_COLORS

print("==================================================")
print("  AUTHORSHIP DISTRIBUTION ANALYSIS (GRID PLOT)")
print("==================================================\n")

os.makedirs("PLOTS", exist_ok=True)

# Global plot settings for academic style
plt.rcParams.update({
    'font.size': 11, 'axes.labelsize': 12, 'axes.titlesize': 13,
    'legend.fontsize': 11, 'xtick.labelsize': 10, 'ytick.labelsize': 10,
    'figure.dpi': 300, 'savefig.dpi': 300, 'font.family': 'serif'
})

PROPOSED_THRESHOLD = 20

def get_author_counts(ds):
    """Helper function to load a dataset and calculate author counts per paper."""
    try:
        df_edges = pd.read_csv(f"edges_{ds}.csv")
        coauth_mask = df_edges['layer'] == 'co-authorship'
        edge_counts = df_edges[coauth_mask]['context'].value_counts()
        author_counts = np.round((1 + np.sqrt(1 + 8 * edge_counts)) / 2).astype(int)
        return author_counts
    except FileNotFoundError:
        print(f"[!] Warning: edges_{ds}.csv not found.")
        return pd.Series(dtype=int)

# ---------------------------------------------------------
# 1. SETUP FIGURE AND GRID LAYOUT
# ---------------------------------------------------------
# 3 rows, 2 columns. The bottom row will be forced to span both columns.
fig = plt.figure(figsize=(14, 16))
gs = GridSpec(3, 2, figure=fig, height_ratios=[1, 1, 1.2], hspace=0.35, wspace=0.15)

# Map datasets to their respective axes based on the expected 4 + 1 configuration
axes_map = {
    DATASETS[0]: fig.add_subplot(gs[0, 0]),  # Row 0, Col 0 (FIDIT)
    DATASETS[1]: fig.add_subplot(gs[0, 1]),  # Row 0, Col 1 (FABRI)
    DATASETS[2]: fig.add_subplot(gs[1, 0]),  # Row 1, Col 0 (FZF)
    DATASETS[3]: fig.add_subplot(gs[1, 1]),  # Row 1, Col 1 (FM)
    DATASETS[4]: fig.add_subplot(gs[2, :])   # Row 2, spanning ALL columns (COMBINED)
}

# ---------------------------------------------------------
# 2. PLOT EACH DATASET
# ---------------------------------------------------------
for ds, ax in axes_map.items():
    author_counts = get_author_counts(ds)
    
    if author_counts.empty:
        ax.text(0.5, 0.5, f"No Data for {ds}", ha='center', va='center', fontsize=14)
        continue
        
    max_authors = author_counts.max()
    
    # Fallback to dark grey if the combined string isn't explicitly in the color map
    color = INSTITUTION_COLORS.get(ds, "#444444")
    
    bins = np.arange(1, max_authors + 2) - 0.5 
    ax.hist(author_counts, bins=bins, color=color, edgecolor='black', alpha=0.8)
    
    # Logarithmic Y-axis to show the massive outliers
    ax.set_yscale('log')
    ax.set_title(f"[{ds}] Authorship Distribution", fontweight='bold')
    
    # Labels
    if ds == DATASETS[-1]: # If it's the large bottom plot
        ax.set_xlabel("Number of Authors per Publication", fontsize=14)
        ax.set_ylabel("Frequency (Log Scale)", fontsize=13)
        # Only put the legend on the big bottom plot to avoid clutter
        ax.axvline(x=PROPOSED_THRESHOLD, color='red', linestyle='--', linewidth=2, 
                   label=f'Hyper-authorship Cutoff (> {PROPOSED_THRESHOLD})')
        ax.legend(loc='upper right', fontsize=12)
    else: # Smaller subplots
        ax.set_xlabel("Authors per Pub")
        ax.set_ylabel("Freq (Log)")
        ax.axvline(x=PROPOSED_THRESHOLD, color='red', linestyle='--', linewidth=1.5)
               
    # Stats Text Box
    massive_papers_count = (author_counts > PROPOSED_THRESHOLD).sum()
    textstr = f"Max Authors: {max_authors}\nPapers > {PROPOSED_THRESHOLD}: {massive_papers_count}"
    ax.text(0.95, 0.85 if ds == DATASETS[-1] else 0.95, textstr, 
            transform=ax.transAxes, ha='right', va='top', 
            bbox=dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.9, edgecolor='grey'))
            
    # X-axis tick formatting
    if max_authors < 20:
        ax.set_xticks(range(1, max_authors + 1))
    else:
        step = 10 if max_authors > 40 else 5
        ax.set_xticks(np.arange(0, max_authors + step, step))
        
    ax.grid(axis='y', linestyle='--', alpha=0.5)

# Overall Figure Title
# fig.suptitle("Hyper-Authorship and Collaboration Scale by Faculty", fontsize=18, y=0.94, fontweight='bold')

plt.savefig("PLOTS/All_Author_Distributions_Grid.png", bbox_inches='tight')
plt.close()

print("\n✅ Finished! Saved to PLOTS/All_Author_Distributions_Grid.png")