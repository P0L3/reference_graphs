
# CROSBI Reference Graph — Multiplex Academic Network Analysis

A pipeline for building and visualising **multiplex organisational networks** from Croatian academic data. It pulls publication and project records from the public [CROSBI](https://www.bib.irb.hr/) and [CroRIS](https://www.croris.hr/) APIs, resolves researcher identities across sources, and assembles a four-layer graph that can be explored in 3D, analysed statistically, or exported to Gephi/Cytoscape.

Built around the faculties of the **University of Rijeka** — FIDIT, FABRI, FZF, and FM — but easily extended to any Croatian institution with a CROSBI ID.

---

## Pipeline overview

```text
fetch_crosbi_data.py          →  nodes / edges / keywords CSVs
        ↓
build_graph_crosbi_data.py    →  GraphML + GEXF per layer
        ↓
[Option A: Interactive Visualisation]
multiplex_graph_analysis_crosbi_data.py  →  3D egocentric plot & CLI exploration

[Option B: Automated Batch Pipeline]
run_pipeline.py (via builder.py)         →  Aggregated master CSVs in RESULTS/

[Option C: Modular Academic Analysis]
rq1_script.py          →  Topologies, homophily & null-model statistical testing
rq2_script.py          →  Edge multiplicity, Jaccard similarity matrices & triadic closure
rq3_script.py          →  Information loss (Spearman), Participation Coefficient & brokers
rq4_script.py          →  Multilayer k-core (Elite Core) & Community Persistence (ARI)
collab_recommender.py  →  Cross-faculty synergy matching (Jaccard gaps)
```

---

## The four network layers

| # | Layer | Type | Edge = |
|---|-------|------|--------|
| 1 | **Co-authorship** | Undirected | Two researchers share a publication |
| 2 | **Mentorship** | Directed (mentor → student) | Supervisor–student relationship on a thesis (skipped in Co-authorship if student thesis) |
| 3 | **Research Similarity** | Undirected | Pairwise Jaccard similarity $\ge 0.025$ on shared keywords |
| 4 | **Project Co-participation** | Undirected | Two researchers appear on the same funded project |

---

## Repository structure

```text
REF_GRA/
├── fetch_crosbi_data.py                  # Step 1 — API extraction & entity resolution
├── build_graph_crosbi_data.py            # Step 2 — Graph assembly & Jaccard projection
├── multiplex_graph_analysis_crosbi_data.py  # Step 3 (A) — Interactive 3D layout & ego-network CLI
├── builder.py                            # Helper — In-memory multiplex graph constructor
├── run_pipeline.py                       # Step 3 (B) — Master automation engine for multiple datasets
├── rq1_script.py                         # RQ1: Baseline topologies & Null models
├── rq2_script.py                         # RQ2: Multiplexity, triads & edge robustness
├── rq3_script.py                         # RQ3: Aggregation cost & interdisciplinary brokers
├── rq4_script.py                         # RQ4: Core-periphery & Community persistence
├── collab_recommender.py                 # Actionable insights: Synergetic recommendations
├── crosbi_coauthorship_institution.ipynb # Interactive notebook (older, single-institution)
├── DATA/                                 # Raw pickles / CSVs (not tracked)
├── RESULTS/                              # Aggregated multi-institutional CSV analysis tables
└── exported_graphs/                      # GraphML & GEXF outputs (generated at runtime)
```

---

## Environment

```shell
conda create -n refgra python=3.10
conda activate refgra
conda install pandas networkx matplotlib pyvis ipykernel requests tqdm nbconvert scipy scikit-learn seaborn pymnet -y
# python -m pip install pymnet
```

---

## Usage

### Step 1 — Fetch data from CROSBI & CroRIS

```shell
python fetch_crosbi_data.py
```

Queries the CROSBI publications API and the CroRIS projects API for every configured institution, resolves researcher identities using a three-tier strategy (project metadata $\rightarrow$ publication vote majority $\rightarrow$ External fallback), and writes three CSV files:

```text
nodes_FIDIT_FABRI_FZF_FM.csv      # one row per unique researcher with institution
edges_FIDIT_FABRI_FZF_FM.csv      # raw co-authorship, mentorship, project edges
keywords_FIDIT_FABRI_FZF_FM.csv   # keyword associations per researcher per publication
```

To analyse a different set of institutions, edit the `institutions` list at the top of the script:

```python
institutions = [
    {"name": "FIDIT", "crosbi_id": 289, "mbu": 318},
    # add or replace entries here
]
```

---

### Step 2 — Export Graphs for External Software

```shell
python build_graph_crosbi_data.py
```

Loads the three CSVs, computes research-similarity edges via pairwise Jaccard comparison on keywords, assembles four NetworkX graphs, and exports each layer as both **GraphML** and **GEXF** under `exported_graphs/`. The files are timestamped, so re-runs never overwrite previous exports.

---

### Step 3 (Option A) — Interactive 3D Visualisation

```shell
python multiplex_graph_analysis_crosbi_data.py
```

Launches an interactive CLI to explore the network visually:

```text
Prompts:
  1. Researcher name substring search (accent-insensitive, e.g. 'mestrovic')
  2. Number of high-centrality context nodes to render alongside (default 120)
```

The output is an **egocentric multiplex view**: four horizontal planes (one per layer), cross-layer vertical coupling lines, and node positions anchored across planes.

**Visual encoding**

| Element | Encoding |
|---------|----------|
| Plane colour | Layer identity |
| Node shape | Faculty affiliation (▲ FIDIT · ★ FABRI · ■ FZF · ◆ FM · ● External) |
| Node position | Unified 2D coordinates projected onto vertical Z-planes |
| Node opacity | Primary interaction layer = 0.90 · Ghost layers = 0.07 · Background = 0.15 |
| Edge weight | Thicker / black for edges incident to the target researcher |
| Vertical dashed line | Cross-layer coupling; bold for the ego node |

---

### Step 3 (Option B) — Automated Master Pipeline

```shell
python run_pipeline.py
```
Automatically iterates through isolated single-institution datasets (e.g., FIDIT alone, FABRI alone) as well as the global university graph. It constructs the graphs in-memory via `builder.py`, runs all modular RQ scripts, and outputs master comparison tables to the `RESULTS/` directory. Ideal for testing macro vs. micro organisational cultures.

---

### Step 3 (Option C) — Modular Research Question Analysis

If you are running the analysis incrementally or preparing figures for specific chapters of your paper, you can run the individual modular scripts standalone.

#### RQ1: Structural Topology & Homophily
```shell
python rq1_script.py
```
Safely calculates density, component count, and GCC. Tests institutional homophily (Assortativity) against **Degree-Preserving Null Models** to statistically prove whether departmental silos are driven by sociology or random chance.

#### RQ2: Cross-Layer Reinforcement
```shell
python rq2_script.py
```
Computes Edge Multiplicity (robustness of ties) and the Layer Similarity Matrix. Tests **Multiplex Triadic Closure** to see if social capital in one layer (e.g., Projects) successfully transfers into another (e.g., Publications).

#### RQ3: Centrality & The Cost of Aggregation
```shell
python rq3_script.py
```
Calculates the **Spearman Rank Correlation** between Monoplex and Multiplex PageRank to quantify the exact percentage of information destroyed when flattening a network. Identifies true interdisciplinary boundary-spanners using the **Participation Coefficient ($P$)** and Burt's Constraint.

#### RQ4: Core-Periphery & Community Persistence
```shell
python rq4_script.py
```
Uses **Multilayer $k$-core Decomposition** to isolate the resilient elite core of the university. Uses the **Adjusted Rand Index (ARI)** on Louvain communities to prove whether formal administrative funding boundaries dictate organic publication boundaries.

#### Gaps: Dynamic Collaboration Recommender
```shell
python collab_recommender.py
```
Scans the network for researcher pairs who share a high thematic keyword similarity but have absolutely **zero** co-authored publications or shared projects. Generates a ranked checklist of inter-departmental synergy opportunities.

---

## Implementation details

Metric/measure implementation details reference guide is available [here](readme_supplement.md).

## Data sources

| Source | API base | What it provides |
|--------|----------|------------------|
| CROSBI | `https://www.bib.irb.hr/crosbi-api/` | Publications, authors, keywords, mentorship |
| CroRIS | `https://www.croris.hr/projekti-api/` | Funded projects & team members |

Both APIs are public and unauthenticated. Rate-limit your requests if running against a large institution.

## ToDo
- [ ] Migration to [pymnet](https://github.com/mnets/pymnet) with a [implementation guide](REF_GRA/pymnet_migration_guide.md).
