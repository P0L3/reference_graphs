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
multiplex_graph_analysis_crosbi_data.py  →  ONA metrics + 3D egocentric plot
```

---

## The four network layers

| # | Layer | Type | Edge = |
|---|-------|------|--------|
| 1 | **Co-authorship** | Undirected | Two researchers share a publication |
| 2 | **Mentorship** | Directed (mentor → student) | Supervisor–student relationship on a thesis |
| 3 | **Research Similarity** | Undirected | Jaccard similarity ≥ 0.025 on shared keywords |
| 4 | **Project Co-participation** | Undirected | Two researchers appear on the same funded project |

---

## Repository structure

```
REF_GRA/
├── fetch_crosbi_data.py                  # Step 1 — API extraction & entity resolution
├── build_graph_crosbi_data.py            # Step 2 — Graph assembly & export
├── multiplex_graph_analysis_crosbi_data.py  # Step 3 — ONA metrics & 3D visualisation
├── crosbi_coauthorship_institution.ipynb # Interactive notebook (older, single-institution)
├── DATA/                                 # Raw pickles / CSVs (not tracked)
└── exported_graphs/                      # GraphML & GEXF outputs (generated at runtime)
```

> **`OLD/`** contains an early prototype that used the Semantic Scholar API — kept for reference only.

---

## Environment

```shell
conda create -n refgra python=3.10
conda activate refgra
conda install pandas networkx matplotlib pyvis ipykernel requests tqdm nbconvert -y
```

---

## Usage

### Step 1 — Fetch data from CROSBI & CroRIS

```shell
python fetch_crosbi_data.py
```

Queries the CROSBI publications API and the CroRIS projects API for every configured institution, resolves researcher identities using a three-tier strategy (project metadata → publication vote majority → External fallback), and writes three CSV files:

```
nodes_FIDIT_FABRI_FZF_FM.csv      # one row per unique researcher
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

Loads the three CSVs, computes research-similarity edges via pairwise Jaccard comparison on keywords (O(N²) — takes a moment for large corpora), assembles four NetworkX graphs, prints per-layer statistics, and exports each layer as both **GraphML** and **GEXF** under `exported_graphs/`. The files are timestamped, so re-runs never overwrite previous exports.

**Jaccard threshold** — default `0.025`. Raise it to reduce noise; lower it to catch weaker thematic overlaps:

```python
SIMILARITY_THRESHOLD = 0.025   # in build_graph_crosbi_data.py
```

---

### Step 3 — Analyse & visualise

```shell
python multiplex_graph_analysis_crosbi_data.py
```

Runs **Phase C** (Organisational Network Analysis) then launches an interactive CLI for **Phase D** (3D visualisation):

```
Phase C outputs
  • Multiplex Degree Overlap ranking — top researchers by summed degree across all layers
  • Layer Edge Overlap — Jaccard similarity between edge-sets of layer pairs

Phase D prompts
  1. Researcher name substring search (accent-insensitive)
  2. Number of high-centrality context nodes to render alongside (default 120)
```

The resulting figure is an **egocentric multiplex view**: four horizontal planes (one per layer), cross-layer coupling lines, and node opacity tied to where each neighbour *first* appears — solid at their primary layer, near-invisible on all others.

**Visual encoding**

| Element | Encoding |
|---------|----------|
| Plane colour | Layer identity |
| Node shape | Faculty affiliation (▲ FIDIT · ★ FABRI · ■ FZF · ◆ FM · ● External) |
| Node opacity | Primary layer = 0.90 · Ghost layers = 0.07 · Background = 0.35 |
| Edge weight | Thicker / black for edges incident to the target researcher |
| Vertical dashed line | Cross-layer coupling; bold for the ego node |

---

## Interactive notebook

`crosbi_coauthorship_institution.ipynb` is a self-contained notebook that fetches data for a **single institution**, builds a co-authorship graph, and renders it as an interactive PyVis HTML file. It predates the three-script pipeline and targets only FIDIT by default. Useful for quick exploration or as a teaching reference — note that some helper logic has since been superseded by the main scripts.

```shell
jupyter notebook crosbi_coauthorship_institution.ipynb
```

---

## Data sources

| Source | API base | What it provides |
|--------|----------|------------------|
| CROSBI | `https://www.croris.hr/crosbi-api/` | Publications, authors, keywords, mentorship |
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

---

## Extending to other institutions

1. Look up the institution's CROSBI ID at `https://www.bib.irb.hr/` and its MBU (project unit ID) at `https://www.croris.hr/`.
2. Add an entry to the `institutions` list in `fetch_crosbi_data.py`.
3. Add the IDs to the `ID_TO_ACRONYM` map so project-based affiliation resolution works.
4. Re-run all three scripts in order.