# Multiplex Network Metrics: Repository Supplement

This document serves as a technical reference guide for all graph metrics, statistical tests, and network measures implemented in this repository and utilized in the associated paper. 

It maps the theoretical concepts to their exact programmatic implementations within the `REF_GRA` pipeline.

---

## 1. Intra-Layer Topology & Homophily
Metrics used to establish the baseline structural profile of individual relational layers.

### Density
* **Reference**: Standard graph theory (Section: *Intra-Layer Topology*).
* **Description**: The ratio of actual observed edges to the total possible edges in a specific layer. Used to determine if a layer is sparse or cohesive.
* **Implementation**: `REF_GRA/rq1_script.py` and `REF_GRA/build_graph_crosbi_data.py` via `nx.density(G_active)`.

### Giant Connected Component (GCC)
* **Reference**: Standard graph theory (Section: *Intra-Layer Topology*).
* **Description**: The size (or percentage) of the largest weakly/strongly connected component of a network layer. Indicates structural fragmentation versus global integration.
* **Implementation**: `REF_GRA/rq1_script.py` via `nx.weakly_connected_components` and `nx.connected_components`.

### Average Clustering Coefficient
* **Reference**: Standard graph theory (Section: *Intra-Layer Topology*).
* **Description**: Measures the degree to which nodes in a graph tend to cluster together (local triadic closure).
* **Implementation**: `REF_GRA/rq1_script.py` via `nx.average_clustering(G_active)`.

### Institutional Assortativity (Homophily)
* **Reference**: Newman (2002)
* **Description**: Measures the tendency of researchers to connect preferentially with others from the same faculty (assortative mixing by categorical attribute). Higher values indicate institutional siloing.
* **Implementation**: `REF_GRA/rq1_script.py` and `REF_GRA/visuals.py` via `nx.attribute_assortativity_coefficient(G_active, 'institution')`.

### Degree-preserving Randomized Null Models (Z-score)
* **Reference**: Milo et al. (2004), Carstens et al. (2017)
* **Description**: Repeated edge-swapping algorithms that randomize the network while keeping node degrees fixed. Used to calculate a Z-score, testing whether observed assortativity or clustering is statistically significant rather than a mechanical artifact of network density.
* **Implementation**: `REF_GRA/rq1_script.py` (inside `generate_degree_preserving_null`) and `REF_GRA/visuals.py`.

---

## 2. Multiplex Edge Overlap & Reinforcement
Metrics assessing how ties translate or replicate across different contextual layers.

### Edge Multiplicity (Distribution)
* **Reference**: Battiston et al. (2014)
* **Description**: The proportion of ties that appear in exactly one, two, or more multiplex layers. Quantifies the functional robustness and separation of academic relationships.
* **Implementation**: `REF_GRA/rq2_script.py` (calculated via `Counter` of `edge_layer_map`).

### Jaccard Edge Overlap (Layer Similarity Matrix)
* **Reference**: Battiston et al. (2014)
* **Description**: The intersection of two distinct layers' edge sets divided by their union. Quantifies how strongly two relational dimensions (e.g., Projects vs. Co-authorship) align structurally.
* **Implementation**: `REF_GRA/rq2_script.py`, `REF_GRA/multiplex_graph_analysis_crosbi_data.py`, and `REF_GRA/visuals.py`.

### Multiplex Triadic Closure
* **Reference**: Battiston et al. (2014), Cozzo et al. (2015)
* **Description**: Generalizes transitivity to multilayer settings. Checks if an indirect connection between two researchers in one or more layers (e.g., sharing a Project neighbor) successfully closes a triangle in a completely different layer (e.g., Co-authorship).
* **Implementation**: `REF_GRA/rq2_script.py` (inside `calculate_mixed_triad_closure()`).

---

## 3. Centrality, Brokerage & Information Loss
Metrics comparing standard single-layer dynamics against multilayer hierarchy.

### Monoplex PageRank
* **Reference**: Page et al. (1999)
* **Description**: A random-walk centrality metric computed on the standard, single-layer aggregated graph (where all multiplex ties are flattened into a single weighted edge set).
* **Implementation**: `REF_GRA/rq3_script.py` and `REF_GRA/visuals.py` via `nx.pagerank(G_agg)`.

### Multiplex PageRank (Supra-adjacency)
* **Reference**: De Domenico et al. (2015), Solé-Ribalta et al. (2014, 2016)
* **Description**: Centrality computed over the full interconnected multilayer structure (a supra-graph where nodes are replicated per layer and connected via inter-layer couplings). The scores are marginalized back to physical nodes to determine multi-contextual prominence.
* **Implementation**: `REF_GRA/rq3_script.py` and `REF_GRA/visuals.py` via `nx.pagerank(G_supra)` followed by layer marginalization.

### Spearman Rank Correlation ($\rho$) & Information Loss
* **Reference**: Solé-Ribalta et al. (2014, 2016)
* **Description**: Evaluates the rank divergence between monoplex and multiplex PageRank. "Information loss" is quantified as $(1 - \rho) \times 100$, calculating how much structural hierarchy is destroyed by flattening the network.
* **Implementation**: `REF_GRA/rq3_script.py` via `scipy.stats.spearmanr`.

### Participation Coefficient ($P_i$)
* **Reference**: Battiston et al. (2014)
* **Description**: Measures how evenly a node's ties are distributed across the available layers. High participation identifies interdisciplinary brokers embedded in multiple contexts simultaneously.
* **Implementation**: `REF_GRA/rq3_script.py` and `REF_GRA/visuals.py` (calculated via $1.0 - \sum (k_l / o_i)^2$).

### Total Multiplex / Overlapping Degree ($o_i$)
* **Reference**: Defined inside the Participation Coefficient equations (Battiston et al., 2014).
* **Description**: The sum of a node's degrees across all individual layers, acting as the baseline denominator for the Participation Coefficient.
* **Implementation**: `REF_GRA/rq3_script.py`, `REF_GRA/multiplex_graph_analysis_crosbi_data.py`, and `REF_GRA/visuals.py`.

### Burt's Constraint
* **Reference**: Burt (2001), Everett & Borgatti (2020)
* **Description**: Measures the extent to which a researcher's network neighborhood is closed/redundant. Low constraint identifies "structural hole spanners"—individuals who connect otherwise disconnected groups.
* **Implementation**: `REF_GRA/rq3_script.py` via `nx.constraint(G_agg_active)`.

---

## 4. Mesoscopic Structure & Community Dynamics
Metrics evaluating community persistence, organizational bridging, and core structures.

### Louvain Community Detection
* **Reference**: Blondel et al. (2008)
* **Description**: A modularity-optimization algorithm used to partition the network into distinct, tightly-knit communities (applied independently to the Project and Co-authorship layers).
* **Implementation**: `REF_GRA/rq4_script.py` via `networkx.algorithms.community.louvain_communities`.

### Adjusted Rand Index (ARI)
* **Reference**: Warrens & van der Hoorn (2022)
* **Description**: Quantifies "Community Persistence" by measuring the agreement between two independent community partitions (e.g., comparing organic publication communities against top-down project funding clusters) while correcting for chance.
* **Implementation**: `REF_GRA/rq4_script.py` via `sklearn.metrics.adjusted_rand_score`.

### k-Core Decomposition (Aggregated Topological Projection)
* **Reference**: Galimberti et al. (2020) — *Note: Operationalized practically on the aggregated binary graph, per the codebase migration guide.*
* **Description**: Recursively removes nodes with a degree less than $k$ to strip away peripheral actors, identifying the most resilient, cohesive "Elite Core" of the university based on their combined relational scaffolding.
* **Implementation**: `REF_GRA/rq4_script.py` via `nx.core_number(G_agg_unweighted)`.

### Boundary-Spanning Ratio (Internal vs. External Edges)
* **Reference**: Described contextually in the *Inter-Institutional Dynamics* section of the paper.
* **Description**: Evaluates institutional integration by measuring the percentage of edges in a specific layer that connect nodes from *different* faculties (Bridges) versus the *same* faculty (Silos).
* **Implementation**: `REF_GRA/visuals.py` (inside the Plot 5 routine calculating `internal_edges` and `external_edges`).

---

## 5. Network Construction Metrics
Metrics used in the pre-processing and dynamic generation of edges.

### Jaccard Similarity (Bipartite Node-Keyword Projection)
* **Reference**: Methodological definition (Section: *Research Similarity Layer*).
* **Description**: Projects a bipartite author-keyword graph into a unipartite layer. A cognitive tie is formed between researchers if their keyword overlap (Jaccard Index) equals or exceeds the significance threshold (0.025).
* **Implementation**: `REF_GRA/fetch_crosbi_data.py`, `REF_GRA/build_graph_crosbi_data.py`, `REF_GRA/builder.py`, and `REF_GRA/collab_recommender.py`.
