# pymnet Migration Guide & RQ Discrepancy Analysis
## CROSBI Multiplex Academic Network — University of Rijeka

---

## Part 1: pymnet Library Capabilities Relevant to This Codebase

Based on the official pymnet documentation, the following features directly map to your current architecture:

### Core Data Structures

| pymnet API | Replaces | Notes |
|---|---|---|
| `MultiplexNetwork(couplings="categorical", fullyInterconnected=False)` | `dict` of `nx.Graph` | Single first-class object for the entire 4-layer network |
| `net.A["co-authorship"]` | `multiplex_graph["co-authorship"]` | Returns a NetworkX-compatible layer graph |
| `pymnet.aggregate(net, aspects=[1])` | Manual `G_agg` loop | Native weighted/unweighted flattening |
| `pymnet.supra_adjacency_matrix(net, includeCouplings=True)` | Manual `G_supra` with string keys like `"node_layer"` | Proper matrix with interlayer coupling |
| `pymnet.subnet(net, nodes, layers)` | `G.subgraph(active_nodes)` | Native subgraph extraction per layer |

### Metrics Available Natively in pymnet

| pymnet Function | What It Computes | Current Code Equivalent |
|---|---|---|
| `pymnet.multiplex_degs(net, node)` | Per-layer degree dict `{layer: deg}` | Manual loop over `multiplex_graph[l].degree(node)` |
| `pymnet.multiplex_density(net)` | Per-layer density | Manual `nx.density(subgraph)` per layer |
| `pymnet.density(net, layer="co-authorship")` | Single-layer density | Same, but cleaner |
| `pymnet.lcc(net)` | Largest connected component (multiplex-aware) | Manual per-layer `nx.connected_components` |
| `pymnet.cc_zhang(net)` | Zhang et al. (2005) multilayer clustering | `nx.average_clustering` (per layer only) |
| `pymnet.cc_barrat(net)` | Barrat et al. (2004) weighted clustering | Same |
| `pymnet.cc_barrett(net)` | Barrett et al. cross-layer clustering coefficient | **Not in current code at all** |
| `pymnet.cc_onnela(net)` | Onnela et al. clustering | **Not in current code at all** |
| `pymnet.draw(net, layout="circular")` | 3D matplotlib plot | ~200 lines in `multiplex_graph_analysis_crosbi_data.py` |
| `pymnet.webplot(net)` | Interactive D3 browser plot | `pyvis` workaround |

### NetworkX Integration (Critical)

pymnet exposes a `pymnet.nx` namespace. Importing it wraps standard NetworkX functions to accept pymnet objects:

```python
from pymnet import nx as pnx

# Returns a pymnet MultilayerNetwork, not a raw nx.Graph
net = pnx.karate_club_graph()

# Iterate per-layer NX graphs for NX-only algorithms:
{layer: pnx.number_connected_components(net.A[layer])
 for layer in net.get_layers()}
```

This is the escape hatch for any algorithm (e.g., Louvain, Burt's constraint) that pymnet does not implement natively.

---

## Part 2: How to Reimplement `builder.py`

### Current Architecture (dict of nx.Graph)

```python
multiplex_graph = {
    "co-authorship": nx.Graph(),
    "mentorship":    nx.DiGraph(),
    "similarity":    nx.Graph(),
    "project":       nx.Graph()
}
```

### Proposed pymnet Architecture

The `mentorship` layer is directed; the other three are undirected. pymnet's `MultiplexNetwork` is homogeneous in directionality. The cleanest solution is to treat the three undirected layers as the core pymnet object and keep the directed mentorship layer as a companion `nx.DiGraph`. This is actually correct theoretically: mentorship is a fundamentally different type of relation that should not be mixed carelessly into undirected centrality metrics.

```python
import pymnet as pn
import networkx as nx

def build_multiplex_pymnet(dataset_name, similarity_threshold=0.025):
    """
    Returns:
        net         : pymnet.MultiplexNetwork (3 undirected layers)
        G_mentorship: nx.DiGraph (directed, kept separate)
        node_attrs  : dict {node_id: {name, surname, institution}}
    """
    # ... load CSVs and compute Jaccard edges as before ...

    UNDIRECTED_LAYERS = ["co-authorship", "similarity", "project"]

    net = pn.MultiplexNetwork(
        couplings="categorical",   # diagonal interlayer edges weight=1
        fullyInterconnected=False, # nodes don't need to exist in all layers
        directed=False
    )

    # Add node attributes (pymnet stores them on the network object)
    node_attrs = {}
    for _, row in df_nodes.iterrows():
        nid = row['node_id']
        node_attrs[nid] = {
            "name":        row['name'],
            "surname":     row['surname'],
            "institution": row.get('institution', 'Unknown')
        }

    # Add undirected layer edges
    for _, edge in static_edges[static_edges['layer'].isin(UNDIRECTED_LAYERS)].iterrows():
        u, v, layer, w = edge['source'], edge['target'], edge['layer'], edge['weight']
        net[u, v, layer] = w          # pymnet edge-set syntax

    # Mentorship stays as a raw NetworkX DiGraph
    G_mentorship = nx.DiGraph()
    for _, row in df_nodes.iterrows():
        G_mentorship.add_node(row['node_id'], **node_attrs[row['node_id']])
    for _, edge in static_edges[static_edges['layer'] == 'mentorship'].iterrows():
        u, v, w = edge['source'], edge['target'], edge['weight']
        if G_mentorship.has_edge(u, v):
            G_mentorship[u][v]['weight'] += w
        else:
            G_mentorship.add_edge(u, v, weight=w)

    return net, G_mentorship, node_attrs
```

### Accessing Layers

```python
# Get a NetworkX-compatible graph for one layer
G_coauth   = net.A["co-authorship"]   # behaves like nx.Graph
G_project  = net.A["project"]
G_sim      = net.A["similarity"]

# All layers
for layer_name in net.get_layers():
    G = net.A[layer_name]
    print(layer_name, G.number_of_edges())
```

---

## Part 3: RQ-by-RQ Analysis — Discrepancies and Better Solutions

---

### RQ1: Structural Topology & Homophily

#### Current Simplification

`rq1_script.py` iterates over `multiplex_graph.items()` and calls standard `nx.*` functions on each layer in isolation:
- `nx.average_clustering(G_active)` is a *per-layer, monoplex* clustering coefficient
- Null models are generated per-layer independently
- GCC is computed per layer

This is methodologically valid *if* described as "layer-wise topology", but it misses what pymnet makes easy: **multilayer** structural metrics.

#### Better Solution with pymnet

**Clustering Coefficients** — pymnet offers four distinct multilayer definitions. They are not interchangeable and each answers a different question:

```python
import pymnet as pn

# Barrett (2012): counts triangles that span across layers.
# This is the most appropriate for a multiplex network because it rewards
# researchers who close triads by contributing across different relationship types.
cc_multilayer = pn.cc_barrett(net)
# Returns a dict {node: cc_value}; take mean for network-level statistic.

# Zhang/Barrat: treats each layer independently (same as current code)
cc_zhang  = {n: pn.cc_zhang(net, node=n)  for n in net}
cc_barrat = {n: pn.cc_barrat(net, node=n) for n in net}
```

**LCC (Largest Connected Component)** — pymnet's `lcc` returns the LCC in the *multiplex sense* (the set of nodes that form the largest component in the aggregated topology), which is what the analysis needs:

```python
lcc_nodes = pn.lcc(net)   # set of nodes
lcc_pct   = len(lcc_nodes) / len(list(net)) * 100
```

**Null Models** — Instead of degree-preserving shuffle per layer, generate a proper multiplex null:

```python
# ER multiplex null: same density per layer, independent random wiring
layer_densities = [pn.density(net, layer=l) for l in net.get_layers()]
n_nodes         = len(list(net))

def generate_multiplex_null(net):
    n  = len(list(net))
    ps = [pn.density(net, layer=l) for l in net.get_layers()]
    return pn.er(n, ps)          # pymnet.er builds an ER multiplex directly
```

**Homophily** — the per-layer assortativity via `net.A["layer"]` is identical to current code and remains valid. No change needed here.

---

### RQ2: Cross-Layer Reinforcement & Multiplexity

#### Current Simplification

`rq2_script.py` manually builds `edge_layer_map` using `defaultdict(set)` and `tuple(sorted((u,v)))`. The mixed triadic closure is computed with nested loops. Both are correct but verbose.

The most significant gap is that the **mixed triadic closure** is described as a multiplex phenomenon but is measured without any multiplex-aware framework — it is effectively three separate single-layer queries joined by shared node identity.

#### Better Solution with pymnet

**Edge Multiplicity** — `pymnet.multiplex_degs()` gives per-node, per-layer degrees. For edge-level multiplicity, iterate the pymnet edge iterator:

```python
from collections import Counter, defaultdict

edge_layer_map = defaultdict(set)
for layer in net.get_layers():
    for u, v in net.A[layer].edges():
        edge_layer_map[tuple(sorted((u, v)))].add(layer)

multiplicity_dist = Counter(len(v) for v in edge_layer_map.values())
```

This is the same logic but driven by `net.A[layer]` instead of `multiplex_graph[layer]`.

**Cross-Layer Clustering (The Real Fix)** — The `cc_barrett` function natively captures whether a node's neighborhood forms triangles that *cross layers*, which is the theoretical backbone of "cross-layer reinforcement":

```python
# cc_barrett counts: for node v, paths u-v-w where the two edges come from
# potentially *different* layers, and the closing edge u-w exists in *any* layer.
# This is a far better test of "does social capital in one layer transfer to another?"
# than the manual calculate_mixed_triad_closure() function.

cc_barrett_per_node = {n: pn.cc_barrett(net, node=n) for n in net}
mean_cc_barrett = sum(cc_barrett_per_node.values()) / len(cc_barrett_per_node)
```

**Multiplex Graphlets (Advanced)** — For a truly rigorous cross-layer motif analysis, pymnet exposes:

```python
from pymnet.graphlets import orbit_counts_all, graphlets

# Count all 2-4 node graphlets simultaneously across all layers.
# This is computationally expensive but gives reviewer-proof evidence of
# cross-layer structural patterns that no monoplex tool can produce.
gcm = pn.graphlets.GCM(net)   # Graphlet Correlation Matrix
gcd = pn.graphlets.GCD(net1, net2)  # Graphlet Correlation Distance between datasets
```

---

### RQ3: Centrality & The Cost of Aggregation

#### Current Simplification

`rq3_script.py` constructs `G_supra` by creating string node IDs (`f"{u}_{layer_name}"`). This is fragile (node IDs containing underscores will collide) and does not use pymnet's native supra-adjacency machinery. Additionally, the interlayer coupling weight is hardcoded to `INTER_LAYER_WEIGHT = 1.0` without justification.

#### Better Solution with pymnet

**Aggregation (Monoplex)** — pymnet's native aggregate replaces the manual loop:

```python
# Aggregate all layers into a single weighted nx.Graph
# weights are summed across layers (equivalent to current G_agg logic)
G_agg_pymnet = pn.aggregate(net, aspects=1)
# G_agg_pymnet is a pymnet MultilayerNetwork with 0 aspects (i.e., a monoplex graph)
# It behaves like an nx.Graph via the pymnet.nx bridge
```

**Supra-Adjacency Matrix** — replace the manual `G_supra` with:

```python
import scipy.sparse as sp

# Returns scipy sparse matrix + node/layer ordering
A_supra, node_layer_index = pn.supra_adjacency_matrix(
    net,
    includeCouplings=True  # includes categorical interlayer edges
)
# Can now run scipy eigenvalue/PageRank solver directly on A_supra
# without the string-ID collision problem
```

**Multiplex PageRank via Power Iteration** — using the supra-adjacency matrix:

```python
import numpy as np
from scipy.sparse.linalg import eigs

n_total = A_supra.shape[0]
d = 0.85   # damping

# Row-normalise
row_sums = np.array(A_supra.sum(axis=1)).flatten()
row_sums[row_sums == 0] = 1
D_inv    = sp.diags(1.0 / row_sums)
T        = D_inv @ A_supra  # column-stochastic transition matrix

# Power iteration for PageRank
pr_vec = np.ones(n_total) / n_total
for _ in range(100):
    pr_vec = d * T.T @ pr_vec + (1 - d) / n_total

# Map back to node IDs and marginalize over layers
# node_layer_index[i] = (node_id, layer_name)
pr_multi = {}
for i, (node, layer) in enumerate(node_layer_index):
    pr_multi[node] = pr_multi.get(node, 0.0) + pr_vec[i]
```

**Participation Coefficient** — `pymnet.multiplex_degs()` makes this clean and correct:

```python
def participation_coefficient(net, node):
    """P = 1 - sum((k_l / o_i)^2), using pymnet native degree query."""
    layer_degs = pn.multiplex_degs(net, node)   # {layer: degree}
    # multiplex_degs returns a dict; values are undirected degrees per layer
    k_values = list(layer_degs.values())
    o_i      = sum(k_values)
    if o_i == 0:
        return 0.0
    return 1.0 - sum((k / o_i) ** 2 for k in k_values)
```

This is cleaner than the manual loop and directly uses pymnet's internal degree representation.

---

### RQ4: Core-Periphery & Community Persistence

#### THE MAJOR DISCREPANCY

This is the most serious methodological gap in the entire codebase, as you identified.

**What the text claims:** Vector-valued multilayer k-core per Galimberti et al. (2020). A node is in the **(k₁, k₂, k₃, k₄)-core** if and only if it has at least kₗ neighbours *within layer l* for all four layers simultaneously.

**What the code does:** Builds a binary aggregated unweighted projection (`G_agg_unweighted`) and runs `nx.core_number()` on it — a single scalar. This is the **topological projection k-core**, not a multilayer k-core.

#### Three Valid Options (Graded by Effort)

---

**Option A — Honest Rename (Minimal effort, fully defensible)**

Simply rename what is computed and describe it accurately. This is still a rigorous, interpretable metric:

> *"We compute the k-core decomposition on the binary topological projection of the multiplex network — the unweighted union graph where an edge (i,j) exists if the pair co-appears in at least one layer. This projection constitutes the structural scaffolding of the university's collaboration topology, and its k-core identifies researchers who maintain dense redundant ties across at least one channel of collaboration."*

No code change needed beyond removing the word "multilayer" from the section heading and result labels.

---

**Option B — Layer-Wise Core Vector (Medium effort, honest and richer)**

This gives each node a 4-tuple `(k_coauth, k_mentor, k_sim, k_project)` computed by running `nx.core_number()` independently on each layer. This is not the Galimberti definition but is fully honest and provides reviewer-worthy per-layer structural information:

```python
def layer_wise_core_decomposition(net, G_mentorship):
    """
    Returns a DataFrame with per-node k-core number for each layer.
    This is NOT the Galimberti vector k-core; it is four independent
    k-core decompositions, one per layer.
    """
    results = {}

    # Undirected layers via pymnet
    for layer in net.get_layers():
        G_layer = net.A[layer]
        # Remove self-loops and isolated nodes for core_number
        G_clean = G_layer.copy()
        G_clean.remove_edges_from(nx.selfloop_edges(G_clean))
        active   = [n for n, d in G_clean.degree() if d > 0]
        G_active = G_clean.subgraph(active)
        core_nums = nx.core_number(G_active)
        for node, k in core_nums.items():
            results.setdefault(node, {})[layer] = k

    # Mentorship layer (convert to undirected for core decomposition)
    G_ment_u = G_mentorship.to_undirected()
    G_ment_u.remove_edges_from(nx.selfloop_edges(G_ment_u))
    active_m  = [n for n, d in G_ment_u.degree() if d > 0]
    G_ment_active = G_ment_u.subgraph(active_m)
    for node, k in nx.core_number(G_ment_active).items():
        results.setdefault(node, {})["mentorship"] = k

    layer_cols = list(net.get_layers()) + ["mentorship"]
    rows = []
    for node, kvals in results.items():
        row = {"node_id": node}
        row.update({f"k_{l}": kvals.get(l, 0) for l in layer_cols})
        row["k_min"]  = min(kvals.get(l, 0) for l in layer_cols)
        row["k_mean"] = sum(kvals.get(l, 0) for l in layer_cols) / len(layer_cols)
        rows.append(row)

    df = pd.DataFrame(rows).sort_values("k_min", ascending=False)
    return df
```

**Academic framing:**
> *"We compute independent k-core decompositions for each of the four layers, assigning each researcher a core vector **k** = (k_coauth, k_mentor, k_sim, k_project). The 'Elite Core' is defined as the set of nodes with k_coauth ≥ threshold AND k_project ≥ threshold, i.e., researchers who are structurally indispensable across both empirical activity layers simultaneously."*

---

**Option C — True Galimberti (2020) Multilayer k-Core (High effort, academically strongest)**

This requires implementing the algorithm from scratch. pymnet's per-layer access via `.A[layer]` makes it tractable. The algorithm is iterative pruning:

```python
def multilayer_kcore(net, G_mentorship, k_vec):
    """
    Galimberti et al. (2020) multilayer k-core decomposition.
    
    Args:
        net      : pymnet.MultiplexNetwork (undirected layers)
        G_mentor : nx.DiGraph for mentorship (used undirected)
        k_vec    : dict {layer_name: k_threshold}
                   e.g. {"co-authorship": 3, "project": 2,
                          "similarity": 2, "mentorship": 1}
    
    Returns:
        set of node IDs in the (k1,k2,k3,k4)-core
    """
    all_layers = list(net.get_layers()) + ["mentorship"]
    
    # Build per-layer adjacency as plain dicts for speed
    adj = {}
    for layer in net.get_layers():
        adj[layer] = {u: set(net.A[layer].neighbors(u)) for u in net.A[layer].nodes()}
    # Mentorship undirected
    G_m_ud = G_mentorship.to_undirected()
    adj["mentorship"] = {u: set(G_m_ud.neighbors(u)) for u in G_m_ud.nodes()}

    # Active node set = union of all nodes across all layers
    active = set()
    for layer in all_layers:
        active.update(adj[layer].keys())

    changed = True
    while changed:
        changed  = False
        to_remove = set()
        for node in active:
            for layer in all_layers:
                k_thresh = k_vec.get(layer, 0)
                if k_thresh == 0:
                    continue
                # Count active neighbours in this layer
                neighbours_in_layer = adj[layer].get(node, set()) & active
                if len(neighbours_in_layer) < k_thresh:
                    to_remove.add(node)
                    break  # No need to check other layers

        if to_remove:
            active -= to_remove
            changed = True

    return active


def find_max_balanced_kcore(net, G_mentorship):
    """
    Binary-search for the largest symmetric k where
    all layers use the same threshold.
    Reports the k-core shell for each k.
    """
    shells = {}
    prev_core = None

    for k in range(1, 50):
        k_vec = {layer: k for layer in list(net.get_layers()) + ["mentorship"]}
        core  = multilayer_kcore(net, G_mentorship, k_vec)
        if not core or core == prev_core:
            break
        shells[k]  = core
        prev_core  = core

    return shells
```

**Usage and academic framing:**
```python
shells = find_max_balanced_kcore(net, G_mentorship)
max_k  = max(shells.keys())
elite  = shells[max_k]
print(f"True multilayer k={max_k} core: {len(elite)} researchers")
```

> *"Following Galimberti et al. (2020), we implement the vector-valued multilayer k-core. A node belongs to the (k,...,k)-core if and only if it simultaneously has at least k neighbours in each of the four layers. We iteratively prune nodes that fail this criterion in any layer until stability, yielding the true elite core of the network."*

This is the definition your text already claims, and now the code would match it.

---

### Community Persistence (ARI) — No Discrepancy

The ARI analysis in `rq4_script.py` is methodologically sound. The only improvement is using pymnet to build the subgraphs:

```python
# Replace manual .subgraph(common_active_nodes) calls with pymnet subnet
from pymnet import nx as pnx

sub_coauth  = pn.subnet(net, nodes=common_active_nodes, layers=["co-authorship"])
sub_project = pn.subnet(net, nodes=common_active_nodes, layers=["project"])

# Then call Louvain directly on the layer graphs:
comms_coauth  = pnx.louvain_communities(sub_coauth.A["co-authorship"],  weight='weight', seed=42)
comms_project = pnx.louvain_communities(sub_project.A["project"], weight='weight', seed=42)
```

---

## Part 4: Summary Table — Discrepancies and Fixes

| RQ | Claim in Text | Actual Code | Severity | Fix |
|---|---|---|---|---|
| RQ1 | Multilayer clustering tested against null models | Per-layer `nx.average_clustering()` — no cross-layer clustering | Medium | Add `pymnet.cc_barrett()` for cross-layer clustering; use `pymnet.er()` for multiplex null |
| RQ1 | Multiplex GCC | Per-layer GCC (four separate numbers) | Low | Use `pymnet.lcc()` for true multiplex LCC; keep per-layer for comparison |
| RQ2 | "Cross-layer reinforcement" via triadic closure | Three independent single-layer closure queries joined manually | Medium | Use `pymnet.cc_barrett()` as the native measure; report graphlets via `pymnet.graphlets.orbit_counts_all()` |
| RQ3 | Supra-adjacency PageRank with coupling omega | Manual string-key `G_supra` with hardcoded `omega=1.0`; string ID collision risk | Medium | Use `pymnet.supra_adjacency_matrix(includeCouplings=True)` for collision-free matrix; vary omega as a sensitivity parameter |
| RQ3 | Participation Coefficient via multiplex degree | Manual loop over `multiplex_graph[l].degree(node)` — excludes mentorship's directionality | Low | Use `pymnet.multiplex_degs()` for undirected layers; handle mentorship separately |
| **RQ4** | **Vector-valued multilayer k-core (Galimberti 2020)** | **`nx.core_number()` on binary projection — single scalar** | **CRITICAL** | **Choose one of: (A) rename honestly, (B) layer-wise 4-tuple, (C) implement true Galimberti algorithm using `net.A[layer]`** |
| RQ4 | Community persistence ARI | Correct; minor inefficiency | None | Use `pymnet.subnet()` for cleaner subgraph extraction |

---

## Part 5: Recommended Environment Update

```shell
conda create -n refgra_pymnet python=3.10
conda activate refgra_pymnet
conda install pandas networkx matplotlib pyvis ipykernel requests tqdm nbconvert scipy scikit-learn seaborn -y
pip install pymnet
```

pymnet installs cleanly via pip and has no conflicts with the existing stack. The `from pymnet import nx` bridge means all existing NetworkX calls remain valid on individual layer graphs via `net.A[layer_name]`.

---

## Part 6: Migration Strategy (Incremental)

Given the codebase has ~2700 lines across 15 files, a full rewrite is risky. The recommended approach is incremental:

**Phase 1 — `builder.py` only.** Replace the `dict` of `nx.Graph` with the `(MultiplexNetwork, G_mentorship)` pair. Update all `rq*_script.py` files to unpack the new return value and substitute `multiplex_graph[l]` → `net.A[l]`.

**Phase 2 — RQ4 fix (highest priority).** Fix the k-core discrepancy to make the paper defensible. Option A takes 30 minutes; Option C takes a day.

**Phase 3 — Native pymnet metrics.** Replace per-layer loops with `pymnet.multiplex_degs`, `pymnet.cc_barrett`, and `pymnet.lcc` calls. Add the Barrett clustering column to the RQ1 output table.

**Phase 4 — Supra-adjacency PageRank.** Replace the fragile string-key `G_supra` in `rq3_script.py` with `pymnet.supra_adjacency_matrix`. Add omega sensitivity analysis.

**Phase 5 — Visualisation.** Replace the ~200-line 3D matplotlib code in `multiplex_graph_analysis_crosbi_data.py` with `pymnet.draw(net, layout="circular")` plus `pymnet.webplot(net)` for the interactive D3 version.
