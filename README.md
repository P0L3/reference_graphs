# CROSBI Reference Graph — Multiplex Academic Network Analysis

A pipeline for building and visualising **multiplex organisational networks** from Croatian academic data. It pulls publication and project records from the public [CROSBI](https://www.bib.irb.hr/) and [CroRIS](https://www.croris.hr/) APIs, resolves researcher identities across sources, and assembles a four-layer graph that can be explored in 3D or exported to Gephi/Cytoscape.

Built around the faculties of the **University of Rijeka** — FIDIT, FABRI, FZF, and FM — but easily extended to any Croatian institution with a CROSBI ID.

---

## Pipeline overview

```
fetch_crosbi_data.py          →  nodes / edges / keywords CSVs
        ↓
build_graph_crosbi_data.py    →  GraphML + GEXF per layer
        ↓
[Option A: All-in-One Interface]
multiplex_graph_analysis_crosbi_data.py  →  ONA metrics + 3D egocentric plot

[Option B: Modular Academic Analysis]
rq1_script.py          →  Layer-by-layer baseline topologies
rq2_script.py          →  Layer-to-layer Jaccard edge overlap
rq3_script.py          →  Centrality comparisons & hidden brokers (filtered)
rq4_script.py          →  Inter-institutional boundary-spanning ratios
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

```
REF_GRA/
├── fetch_crosbi_data.py                  # Step 1 — API extraction & entity resolution
├── build_graph_crosbi_data.py            # Step 2 — Graph assembly & Jaccard projection
├── multiplex_graph_analysis_crosbi_data.py  # Step 3 (A) — All-in-one ONA metrics & 3D layout
├── loading_graph.py                      # Step 3 (B) — Common helper to load timestamped GraphML
├── rq1_script.py                         # Step 3 (B) — RQ1: Baseline layer topologies
├── rq2_script.py                         # Step 3 (B) — RQ2: Layer Jaccard edge overlap
├── rq3_script.py                         # Step 3 (B) — RQ3: Centrality comparisons & brokers
├── rq4_script.py                         # Step 3 (B) — RQ4: Silo vs. Bridge ratios
├── collab_recommender.py                 # Step 3 (B) — Gaps: Synergetic recommendations
├── crosbi_coauthorship_institution.ipynb # Interactive notebook (older, single-institution)
├── DATA/                                 # Raw pickles / CSVs (not tracked)
└── exported_graphs/                      # GraphML & GEXF outputs (generated at runtime)
```

---

## Environment

```shell
conda create -n refgra python=3.10
conda activate refgra
conda install pandas networkx matplotlib pyvis ipykernel requests tqdm nbconvert scipy scikit-learn -y
```

---

## Usage

### Step 1 — Fetch data from CROSBI & CroRIS

```shell
python fetch_crosbi_data.py
```

Queries the CROSBI publications API and the CroRIS projects API for every configured institution, resolves researcher identities using a three-tier strategy (project metadata $\rightarrow$ publication vote majority $\rightarrow$ External fallback), and writes three CSV files:

```
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

### Step 2 — Build the multiplex graph

```shell
python build_graph_crosbi_data.py
```

Loads the three CSVs, computes research-similarity edges via pairwise Jaccard comparison on keywords (O(N²) — optimized with standard grouping), assembles four NetworkX graphs, prints per-layer statistics, and exports each layer as both **GraphML** and **GEXF** under `exported_graphs/`. The files are timestamped, so re-runs never overwrite previous exports.

---

### Step 3 (Option A) — All-in-One Interactive ONA & Visualisation

```shell
python multiplex_graph_analysis_crosbi_data.py
```

Runs baseline centrality and overlap calculations, and launches an interactive CLI:

```
Prompts:
  1. Researcher name substring search (accent-insensitive, e.g. 'mestrovic')
  2. Number of high-centrality context nodes to render alongside (default 120)
```

The output is an **egocentric multiplex view**: four horizontal planes (one per layer), cross-layer vertical coupling lines, and node position anchored across planes [1].

**Visual encoding**

| Element | Encoding |
|---------|----------|
| Plane colour | Layer identity |
| Node shape | Faculty affiliation (▲ FIDIT · ★ FABRI · ■ FZF · ◆ FM · ● External) [1] |
| Node position | Unified 2D coordinates projected onto vertical Z-planes [1] |
| Node opacity | Primary interaction layer = 0.90 · Ghost layers = 0.07 · Background = 0.15 |
| Edge weight | Thicker / black for edges incident to the target researcher |
| Vertical dashed line | Cross-layer coupling; bold for the ego node |

---

### Step 3 (Option B) — Modular Research Question Analysis

If you are running the analysis incrementally or preparing figures for specific chapters of your paper, you can run the individual modular scripts. These automatically load your target dataset via the helper module `loading_graph.py` [1].

First, open `loading_graph.py` and set your active graph run timestamp:
```python
TIMESTAMP = "12-01-25-06-2026"  # matches files in exported_graphs/
```

#### RQ1: Structural Topology of Layers
```shell
python rq1_script.py
```
Safely calculates density, component count, giant connected component (GCC) size, average path length, and diameter for each layer. Directed networks (Mentorship) and highly fragmented layers are evaluated strictly on their GCC to ensure mathematical accuracy and prevent code exceptions [1].

#### RQ2: Layer Edge Overlap
```shell
python rq2_script.py
```
Computes the pairwise Jaccard similarity of edges between your layers (e.g., how heavily projects and co-authorships overlap). Reveals whether formal funding structures are a structural prerequisite for actual scientific production [1].

#### RQ3: Centrality & Hidden Brokers (Filtered)
```shell
python rq3_script.py
```
Compares standard Monoplex degree with Multiplex Degree Overlap. Discovers "Hidden Brokers" (such as mathematicians) whose project-leading or mentoring footprint is massive but unrecognized by publication counts alone [1]. Automatically filters out external collaborators to keep the ranking focused strictly on internal faculty brokers [1].

#### RQ4: Inter-Institutional Silos vs. Bridges
```shell
python rq4_script.py
```
Evaluates the boundary-spanning ratio (cross-departmental edges vs. internal edges) across all 4 layers. Proves whether formal administrative interventions (Projects) are more effective at breaking departmental silos than organic co-authorship [1].

#### Gaps: Dynamic Collaboration Recommender
```shell
python collab_recommender.py
```
Scans the similarity layer for researcher pairs who share a high thematic keyword similarity (Jaccard index) but have absolutely **zero** co-authored publications or shared projects. Generates a ranked checklist of inter-departmental synergy opportunities [1].

---

## Data sources

| Source | API base | What it provides |
|--------|----------|------------------|
| CROSBI | `https://www.bib.irb.hr/crosbi-api/` | Publications, authors, keywords, mentorship |
| CroRIS | `https://www.croris.hr/projekti-api/` | Funded projects & team members |

Both APIs are public and unauthenticated. Rate-limit your requests if running against a large institution.

---

## Output formats

| File | Format | Tool |
|------|--------|------|
| `exported_graphs/<layer>_<timestamp>.graphml` | GraphML | Gephi, Cytoscape, NetworkX |
| `exported_graphs/<layer>_<timestamp>.gexf` | GEXF | Gephi (timeline support) |
| PyVis HTML | Interactive browser graph | Any browser |
| Matplotlib 3D figure | On-screen / saveable | `plt.savefig()` |