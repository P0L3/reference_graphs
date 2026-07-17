import pandas as pd
import numpy as np
from config import COMBINED_DATASET_NAME

# Load global dataset edges
df_edges = pd.read_csv(f"edges_{COMBINED_DATASET_NAME}.csv")

# Filter only co-authorship layer
df_co = df_edges[df_edges['layer'] == 'co-authorship']

# Count edges per context (publication)
edge_counts = df_co['context'].value_counts()

# Calculate the exact number of authors using the complete graph edge formula
author_counts = (1 + np.sqrt(1 + 8 * edge_counts)) / 2

# Filter publications with more than 20 authors
massive_papers = author_counts[author_counts > 20].sort_values(ascending=False)

print(f"Found {len(massive_papers)} publications with > 20 authors:\n")
for context, n_authors in massive_papers.head(10).items():
    pub_id = context.replace("pub_", "")
    print(f"Authors: {int(n_authors):>3} | Context: {context} | URL: https://www.croris.hr/crosbi/publikacija/rad/{pub_id}")