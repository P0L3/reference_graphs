
"""
plot_master_results.py

Template publication plotting script.

NOTE:
This scaffold is intentionally modular. It expects the following files
inside RESULTS/:

MASTER_RQ1_Topologies.csv
MASTER_RQ2_EdgeMultiplicity.csv
MASTER_RQ2_TriadicClosure.csv
MASTER_RQ3_AggregationStats.csv
MASTER_RQ4_CommunityPersistence.csv
"""

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

RESULTS = Path("RESULTS")
PLOTS = Path("PLOTS")
PLOTS.mkdir(exist_ok=True)

OKABE_ITO = {
    "blue":"#0072B2",
    "orange":"#E69F00",
    "green":"#009E73",
    "vermillion":"#D55E00",
    "purple":"#CC79A7",
    "yellow":"#F0E442",
    "sky":"#56B4E9",
    "black":"#000000"
}

plt.rcParams.update({
    "figure.dpi":300,
    "savefig.dpi":300,
    "font.size":11,
})

def save(fig,name):
    fig.tight_layout()
    fig.savefig(PLOTS/f"{name}.png")
    # fig.savefig(PLOTS/f"{name}.pdf")
    # fig.savefig(PLOTS/f"{name}.svg")
    plt.close(fig)

# ---------------- Figure 1 ----------------
try:
    df=pd.read_csv(RESULTS/"MASTER_RQ2_EdgeMultiplicity.csv")
    # Adapt these column names if necessary
    pivot=df.pivot(index="Dataset",columns="Layers Shared",values="Percentage (%)")
    fig,ax=plt.subplots(figsize=(8,5))
    bottom=None
    colors=[OKABE_ITO["sky"],OKABE_ITO["green"],OKABE_ITO["orange"],OKABE_ITO["vermillion"]]
    for c,col in zip(colors,pivot.columns):
        vals=pivot[col]
        ax.bar(pivot.index,vals,bottom=bottom,label=str(col),color=c)
        bottom=vals if bottom is None else bottom+vals
    ax.set_ylabel("% of ties")
    ax.set_title("Fragility of Ties")
    ax.legend(title="Shared layers")
    save(fig,"Fig01_FragilityOfTies")
except Exception as e:
    print("Fig1 skipped:",e)

# ---------------- Figure 2 ----------------
try:
    df=pd.read_csv(RESULTS/"MASTER_RQ3_AggregationStats.csv")
    fig,ax=plt.subplots(figsize=(7,4))
    ax.bar(df["Dataset"],df["information_loss_pct"],color=OKABE_ITO["vermillion"])
    for i,v in enumerate(df["information_loss_pct"]):
        ax.text(i,v,f"{v:.1f}%",ha="center",va="bottom")
    ax.set_ylabel("Information loss (%)")
    ax.set_title("Cost of Aggregation")
    save(fig,"Fig02_CostOfAggregation")
except Exception as e:
    print("Fig2 skipped:",e)

# ---------------- Figure 3 ----------------
try:
    df=pd.read_csv(RESULTS/"MASTER_RQ1_Topologies.csv")
    g=df[df["Dataset"]=="FIDIT_FABRI_FZF_FM"]
    x=range(len(g))
    w=0.35
    fig,ax=plt.subplots(figsize=(8,5))
    ax.bar([i-w/2 for i in x],g["Observed Assort"],w,label="Observed")
    ax.bar([i+w/2 for i in x],g["Null Assort"],w,label="Null")
    ax.set_xticks(list(x))
    ax.set_xticklabels(g["Layer"])
    ax.legend()
    ax.set_title("Institutional Homophily vs Null")
    save(fig,"Fig03_HomophilyVsNull")
except Exception as e:
    print("Fig3 skipped:",e)

# ---------------- Figure 4 ----------------
try:
    df=pd.read_csv(RESULTS/"MASTER_RQ4_CommunityPersistence.csv")
    fig,ax=plt.subplots(figsize=(7,4))
    ax.barh(df["Dataset"],df["ari_score"],color=OKABE_ITO["blue"])
    ax.set_xlabel("Adjusted Rand Index")
    ax.set_title("Community Persistence")
    save(fig,"Fig04_CommunityPersistence")
except Exception as e:
    print("Fig4 skipped:",e)

# ---------------- Figure 5 ----------------
try:
    df=pd.read_csv(RESULTS/"MASTER_RQ2_TriadicClosure.csv")
    g=df[df["Dataset"]=="FIDIT_FABRI_FZF_FM"] if "Dataset" in df.columns else df
    fig,ax=plt.subplots(figsize=(7,4))
    ax.bar(g["Hypothesis"],g["Closure Rate (%)"],color=OKABE_ITO["green"])
    ax.set_ylabel("Closure rate (%)")
    ax.set_title("Multiplex Triadic Closure")
    save(fig,"Fig05_MultiplexTriadicClosure")
except Exception as e:
    print("Fig5 skipped:",e)

print("Finished.")