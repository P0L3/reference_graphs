import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

print("==========================================")
print("  COMPREHENSIVE DATASET STATISTICS")
print("==========================================\n")

os.makedirs("PLOTS", exist_ok=True)

# Okabe-Ito Color Palette
OKABE_ITO = {
    "FIDIT":  "#56B4E9",   # Sky Blue
    "FABRI": "#CC79A7",   # Vermillion
    "FZF":   "#E69F00",   # Orange
    "FM":    "#009E73",   # Green
    "GLOBAL": "#000000",   # Black 
}

plt.rcParams.update({
    'font.size': 12, 'axes.labelsize': 14, 'axes.titlesize': 15,
    'legend.fontsize': 11, 'xtick.labelsize': 11, 'ytick.labelsize': 11,
    'figure.dpi': 300, 'savefig.dpi': 300, 'font.family': 'serif'
})

DATASETS = [
    ("FIDIT", "FIDIT"), 
    ("FABRI", "FABRI"), 
    ("FZF", "FZF"), 
    ("FM", "FM"), 
    ("GLOBAL", "FIDIT_FABRI_FZF_FM")
]

stats = []

# Dictionaries to hold temporal data for plotting
pub_timelines = {}
proj_timelines = {}

# Time analysis window
MIN_YEAR = 2005
MAX_YEAR = 2026

for display_name, file_suffix in DATASETS:
    # 1. Load raw data
    try:
        df_nodes = pd.read_csv(f"nodes_{file_suffix}.csv")
        df_edges = pd.read_csv(f"edges_{file_suffix}.csv")
        df_keywords = pd.read_csv(f"keywords_{file_suffix}.csv")
    except FileNotFoundError:
        print(f"Warning: Files for {file_suffix} not found. Skipping...")
        continue

    # 2. Separate Unique Pubs and Projects based on 'context' ID
    df_pubs = df_edges[df_edges['layer'] == 'co-authorship'].drop_duplicates(subset=['context'])
    df_projs = df_edges[df_edges['layer'] == 'project'].drop_duplicates(subset=['context'])

    # 3. Calculate basic counts
    n_researchers = len(df_nodes)
    n_pubs = len(df_pubs)
    n_projs = len(df_projs)
    n_keywords = df_keywords['keyword'].nunique()

    # 4. Temporal Math (Publications)
    valid_pubs = df_pubs[(df_pubs['year_start'] > 1950) & (df_pubs['year_start'] <= MAX_YEAR)]
    if not valid_pubs.empty:
        pub_span = f"{valid_pubs['year_start'].min():.0f}--{valid_pubs['year_start'].max():.0f}"
        pub_median = f"{valid_pubs['year_start'].median():.0f}"
        # Save temporal distribution for plotting
        pub_counts = valid_pubs[valid_pubs['year_start'] >= MIN_YEAR]['year_start'].value_counts().sort_index()
        pub_timelines[display_name] = pub_counts
    else:
        pub_span, pub_median = "N/A", "N/A"

    # 5. Temporal Math (Projects - Active per year)
    valid_projs = df_projs[(df_projs['year_start'] > 1950) & (df_projs['year_end'] >= df_projs['year_start'])]
    active_projs_per_year = {y: 0 for y in range(MIN_YEAR, MAX_YEAR + 1)}
    
    if not valid_projs.empty:
        proj_durations = valid_projs['year_end'] - valid_projs['year_start']
        avg_proj_dur = f"{proj_durations.mean():.1f} yrs"
        
        # Count how many projects were active in each year
        for _, row in valid_projs.iterrows():
            start = max(int(row['year_start']), MIN_YEAR)
            end = min(int(row['year_end']), MAX_YEAR)
            for y in range(start, end + 1):
                active_projs_per_year[y] += 1
                
        proj_timelines[display_name] = pd.Series(active_projs_per_year)
    else:
        avg_proj_dur = "N/A"

    # 6. Format label for the table
    stats.append({
        "Institution": display_name,
        "Researchers": n_researchers,
        "Collab_Pubs": n_pubs,
        "Pub_Timeline": f"{pub_span} ({pub_median})",
        "Projects": n_projs,
        "Avg_Proj_Dur": avg_proj_dur,
        "Unique_Keywords": n_keywords
    })

# ==========================================
# GENERATE COMPARATIVE PLOTS (2005 - 2026)
# ==========================================
print("Generating Timeline Distributions...")

# Plot 1: Publications Over Time
fig, ax = plt.subplots(figsize=(10, 6))

for inst in ["FIDIT", "FABRI", "FZF", "FM"]:
    if inst in pub_timelines:
        ax.plot(
            pub_timelines[inst].index,
            pub_timelines[inst].values,
            label=inst,
            color=OKABE_ITO[inst],
            linewidth=2.5,
            marker='o',
            markersize=5
        )

# ax.set_title("Longitudinal Distribution of Collaborative Publications (2005–2026)")
ax.set_ylabel("Number of Publications")
ax.set_xlabel("Year")

# Set x-axis ticks to the years
ax.set_xticks(pub_timelines[inst].index)

# Rotate tick labels
ax.tick_params(axis='x', labelrotation=45)

ax.grid(axis='y', linestyle='--', alpha=0.6)
ax.set_xlim(MIN_YEAR, MAX_YEAR)
ax.legend(title="Faculty")

plt.tight_layout()
plt.savefig("PLOTS/Dataset_Pubs_Timeline.png")
plt.close()

# Plot 2: Active Projects Over Time
fig, ax = plt.subplots(figsize=(10, 6))
for inst in ["FIDIT", "FABRI", "FZF", "FM"]:
    if inst in proj_timelines:
        ax.plot(proj_timelines[inst].index, proj_timelines[inst].values, 
                label=inst, color=OKABE_ITO[inst], linewidth=2.5, marker='s', markersize=5)

# ax.set_title("Density of Active Funded Projects per Year (2005–2026)")
ax.set_ylabel("Number of Active Projects")
ax.set_xlabel("Year")

# Set x-axis ticks to the years
ax.set_xticks(proj_timelines[inst].index)

# Rotate tick labels
ax.tick_params(axis='x', labelrotation=45)
ax.grid(axis='y', linestyle='--', alpha=0.6)
ax.set_xlim(MIN_YEAR, MAX_YEAR)
ax.legend(title="Faculty")
plt.tight_layout()
plt.savefig("PLOTS/Dataset_Projs_Timeline.png")
plt.close()
print("Saved timeline plots to ./PLOTS/")


# ==========================================
# OUTPUT 100% COPY-READY LATEX TABLE
# ==========================================
print("\n" + "="*50)
print("  COPY-PASTE THE FOLLOWING BLOCK INTO LATEX")
print("="*50 + "\n")

latex_str = r"""\begin{table}[htpb]
\centering
\caption{Descriptive statistics of the dataset per institution and globally.}
\label{tab:desc_stats}
\resizebox{\textwidth}{!}{%
\begin{tabular}{lcccccc}
\toprule
\textbf{Institution} & \textbf{Researchers} & \textbf{Collab. Pubs} & \textbf{Pub Timeline (Median)} & \textbf{Projects} & \textbf{Avg. Proj Duration} & \textbf{Unique Keywords} \\
\midrule
"""

for s in stats:
    if s['Institution'] == "GLOBAL":
        latex_str += "\\midrule\n"
        latex_str += f"\\textbf{{{s['Institution']}}} & \\textbf{{{s['Researchers']}}} & \\textbf{{{s['Collab_Pubs']}}} & \\textbf{{{s['Pub_Timeline']}}} & \\textbf{{{s['Projects']}}} & \\textbf{{{s['Avg_Proj_Dur']}}} & \\textbf{{{s['Unique_Keywords']}}} \\\\\n"
    else:
        latex_str += f"{s['Institution']} & {s['Researchers']} & {s['Collab_Pubs']} & {s['Pub_Timeline']} & {s['Projects']} & {s['Avg_Proj_Dur']} & {s['Unique_Keywords']} \\\\\n"

latex_str += r"""\bottomrule
\end{tabular}%
}
\end{table}"""

print(latex_str)
print("\n" + "="*50)