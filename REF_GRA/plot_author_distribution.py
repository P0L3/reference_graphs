import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import warnings

warnings.filterwarnings("ignore")

# Import the datasets list from your configuration
from config import DATASETS, INSTITUTION_COLORS

print("==================================================")
print("  AUTHORSHIP DISTRIBUTION ANALYSIS")
print("==================================================\n")

os.makedirs("PLOTS", exist_ok=True)

# Global plot settings for academic style
plt.rcParams.update({
    'font.size': 12, 'axes.labelsize': 14, 'axes.titlesize': 15,
    'legend.fontsize': 11, 'xtick.labelsize': 11, 'ytick.labelsize': 11,
    'figure.dpi': 300, 'savefig.dpi': 300, 'font.family': 'serif'
})

PROPOSED_THRESHOLD = 20

for ds in tqdm(DATASETS, desc="Processing Datasets", colour="green"):
    try:
        # 1. Load edge data
        df_edges = pd.read_csv(f"edges_{ds}.csv")
        
        # 2. Isolate co-authorship edges
        coauth_mask = df_edges['layer'] == 'co-authorship'
        
        # 3. Count edges per publication context
        edge_counts = df_edges[coauth_mask]['context'].value_counts()
        
        # 4. Mathematically reverse-engineer author count from edge count: E = N*(N-1)/2 
        # Adding round() and astype(int) to ensure clean binning
        author_counts = np.round((1 + np.sqrt(1 + 8 * edge_counts)) / 2).astype(int)
        
        if author_counts.empty:
            print(f"\n[!] No co-authorship data for {ds}, skipping.")
            continue
            
        max_authors = author_counts.max()
        
        # 5. Plotting
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # We assign a color based on the dataset (fallback to black for the COMBINED graph)
        color = INSTITUTION_COLORS.get(ds, "#000000")
        
        # Create bins covering 1 to the maximum number of authors found
        bins = np.arange(1, max_authors + 2) - 0.5 
        
        counts, _, _ = ax.hist(author_counts, bins=bins, color=color, edgecolor='black', alpha=0.75)
        
        # Set Y-axis to logarithmic to make outliers (1 or 2 massive papers) visible
        ax.set_yscale('log')
        
        ax.set_title(f"[{ds}] Distribution of Authors per Publication")
        ax.set_xlabel("Number of Authors per Publication")
        ax.set_ylabel("Frequency (Log Scale)")
        
        # Draw a line showing the cutoff limit
        ax.axvline(x=PROPOSED_THRESHOLD, color='red', linestyle='--', linewidth=2, 
                   label=f'Hyper-authorship Cutoff (> {PROPOSED_THRESHOLD})')
        
        # Add a text label showing how many papers exist beyond the threshold
        massive_papers_count = (author_counts > PROPOSED_THRESHOLD).sum()
        ax.text(0.95, 0.95, f"Max Authors in a paper: {max_authors}\nPapers > {PROPOSED_THRESHOLD} authors: {massive_papers_count}", 
                transform=ax.transAxes, ha='right', va='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
        
        # Clean up X-ticks to make them readable
        if max_authors < 20:
            ax.set_xticks(range(1, max_authors + 1))
        else:
            # If we have 70 authors, stepping by 5 keeps it clean
            ax.set_xticks(np.arange(0, max_authors + 5, 5))
            
        ax.grid(axis='y', linestyle='--', alpha=0.6)
        ax.legend(loc='center right')
        
        plt.tight_layout()
        plt.savefig(f"PLOTS/{ds}_Author_Distribution.png")
        plt.close()

    except FileNotFoundError:
        print(f"\n[!] Error loading {ds}: edges file not found.")
    except Exception as e:
        print(f"\n[!] Unexpected error for {ds}: {e}")

print("\n✅ Finished! Check the /PLOTS directory for the histograms.")