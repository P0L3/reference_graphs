# CROSBI Reference Graph — Multiplex Academic Network Analysis

A pipeline for building and visualising **multiplex organisational networks** from Croatian academic data. It pulls publication and project records from the public [CROSBI](https://www.bib.irb.hr/) and [CroRIS](https://www.croris.hr/) APIs, resolves researcher identities across sources, and assembles a four-layer graph that can be explored in 3D, analysed statistically, or exported to Gephi/Cytoscape.

Built around the faculties of the **University of Rijeka** — FIDIT, FABRI, FZF, and FM — but easily extended to any Croatian institution with a CROSBI ID.

---

## Pipeline overview

```text
fetch_crosbi_data.py          →  nodes / edges / keywords CSVs
        ↓
build_graph_crosbi_data.py    →  GraphML + GEXF per layer (for Gephi/Cytoscape/PyVis)
        ↓
        ├── [Primary] run_pipeline.py            →  Aggregated MASTER comparison CSVs in RESULTS/
        │       (builds every dataset in-memory via builder.py, then calls the
        │        rq1-rq4 functions below internally — this is the script you run)
        │
        └── [Optional / diagnostic]
              multiplex_graph_analysis_crosbi_data.py  →  interactive 3D plot & ego-network CLI
```

---

## ⭐ The main entry point: `run_pipeline.py`

**If you only run one script, run this one.**

```shell
python run_pipeline.py
```

It automatically builds every configured dataset in memory (`FIDIT`, `FABRI`, `FZF`, `FM`, and the combined `FIDIT_FABRI_FZF_FM`), runs the full RQ1–RQ4 analytical suite on each, and writes tagged, comparable master tables to `RESULTS/` — one row per `Dataset` per metric, so a single institution can be compared directly against the others or against the whole university. This is the setup used to produce every comparative figure in the paper.

`rq1_script.py` through `rq4_script.py` (below) are **not separate pipeline steps** — they are the individual analysis modules that `run_pipeline.py` imports and calls internally (`rq1_process_graph()`, `rq2_process_graph()`, etc.). You do not need to run them yourself. They're documented separately only so that:
- you can inspect exactly which metric belongs to which research question, and
- you can run a single one standalone against one dataset while debugging or drafting a specific figure, without re-running the whole batch.

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
├── build_graph_crosbi_data.py            # Step 2 — Graph assembly, export for external tools
├── builder.py                            # In-memory multiplex graph constructor, used by run_pipeline.py
├── run_pipeline.py                       # ⭐ MAIN ENTRY POINT — master automation engine, all datasets
├── rq1_script.py                         # Module: Baseline topologies & Null models (called by run_pipeline.py)
├── rq2_script.py                         # Module: Multiplexity, triads & edge robustness (called by run_pipeline.py)
├── rq3_script.py                         # Module: Aggregation cost & interdisciplinary brokers (called by run_pipeline.py)
├── rq4_script.py                         # Module: Core-periphery & Community persistence (called by run_pipeline.py)
├── collab_recommender.py                 # Actionable insights: Synergetic recommendations
├── multiplex_graph_analysis_crosbi_data.py  # Optional — Interactive 3D layout & ego-network CLI
├── data_stats.py                         # Calculate publication and project statistics.
├── plot_master_results(_2)/visuals.py    # Plot the Figures used in the related paper (read from RESULTS/)
├── crosbi_coauthorship_institution.ipynb # Interactive notebook (older, single-institution)
├── DATA/                                 # Raw pickles / CSVs (not tracked)
├── RESULTS/                              # Aggregated multi-institutional CSV analysis tables (from run_pipeline.py)
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

Loads the three CSVs, computes research-similarity edges via pairwise Jaccard comparison on keywords, assembles four NetworkX graphs, and exports each layer as both **GraphML** and **GEXF** under `exported_graphs/`. This step is for feeding Gephi/Cytoscape/PyVis — it is not required by `run_pipeline.py`, which builds its own graphs in memory via `builder.py`.

---

### Step 3 — Run the analysis: `run_pipeline.py` ⭐

```shell
python run_pipeline.py
```

This is the script you should run for any statistical/comparative analysis. It iterates through isolated single-institution datasets (FIDIT alone, FABRI alone, FZF alone, FM alone) as well as the combined global university graph, constructs each graph in-memory via `builder.py`, runs all four RQ modules on each, and writes tagged master comparison tables to `RESULTS/`:

```text
RESULTS/MASTER_RQ1_Topologies.csv
RESULTS/MASTER_RQ2_EdgeMultiplicity.csv
RESULTS/MASTER_RQ2_TriadicClosure.csv
RESULTS/MASTER_RQ2_LayerSimilarity.csv
RESULTS/MASTER_RQ2_StructuralTwins.csv
RESULTS/MASTER_RQ3_AggregationStats.csv
RESULTS/MASTER_RQ3_NodeMetrics_Full.csv
RESULTS/MASTER_RQ3_NodeMetrics_Ranked.csv
RESULTS/MASTER_RQ4_CommunityPersistence.csv
RESULTS/MASTER_RQ4_CoreDecomposition.csv
RESULTS/MASTER_RQ4_CoreStats.csv
RESULTS/MASTER_RQ4_EliteCoreBreakdown.csv
RESULTS/RUN_MANIFEST.csv
```

Every table has a `Dataset` column so any metric can be compared across FIDIT / FABRI / FZF / FM / the combined university. `RUN_MANIFEST.csv` records which datasets were successfully processed vs. skipped (e.g. missing CSVs, or a dataset that errored partway through) so a partial run is always auditable rather than silently incomplete.

Ideal for testing macro (whole-university) vs. micro (single-faculty) organisational cultures.

---

### Optional — Interactive 3D Visualisation

```shell
python multiplex_graph_analysis_crosbi_data.py
```

Launches an interactive CLI to explore one dataset's network visually — useful for spot-checking or preparing a qualitative figure, not part of the statistical pipeline above.

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

### Reference — The individual RQ modules (called internally by `run_pipeline.py`)

You don't need to run these directly; they're documented here so each metric can be traced to the research question it answers. Each also has a standalone `__main__` block for debugging a single dataset in isolation.

#### RQ1: Structural Topology & Homophily — `rq1_script.py`
Calculates density, component count, and GCC. Tests institutional homophily (Assortativity) against **Degree-Preserving Null Models** to test whether departmental silos are driven by sociology or random chance.

#### RQ2: Cross-Layer Reinforcement — `rq2_script.py`
Computes Edge Multiplicity (robustness of ties) and the Layer Similarity Matrix. Tests **Multiplex Triadic Closure** to see if social capital in one layer (e.g., Projects) successfully transfers into another (e.g., Publications).

#### RQ3: Centrality & The Cost of Aggregation — `rq3_script.py`
Calculates the **Spearman Rank Correlation** between Monoplex and Multiplex PageRank to quantify the percentage of information destroyed when flattening a network. Identifies interdisciplinary boundary-spanners using the **Participation Coefficient ($P$)** and Burt's Constraint.

#### RQ4: Core-Periphery & Community Persistence — `rq4_script.py`
Uses **Multilayer $k$-core Decomposition** to isolate the resilient elite core of the university. Uses the **Adjusted Rand Index (ARI)** on Louvain communities to test whether formal administrative funding boundaries align with organic publication boundaries.

#### Gaps: Dynamic Collaboration Recommender — `collab_recommender.py`
```shell
python collab_recommender.py
```
Scans the network for researcher pairs who share a high thematic keyword similarity but have **zero** co-authored publications or shared projects. Generates a ranked checklist of inter-departmental synergy opportunities.

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