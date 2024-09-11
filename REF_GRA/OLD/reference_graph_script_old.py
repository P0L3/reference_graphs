import networkx as nx
import pandas as pd

# Load dataset
DIR = "./DATA/enerpol_full.pickle"
df = pd.read_pickle(DIR)

# Dataset info
# Filter no references

df = df[df["References"] != "no_references"]
df = df[df["Authors"] != "no_author"]

df.info()


print(df["Authors"].sample(1).tolist()[0])
for a in df["DOI"].sample(1).tolist()[0]:
    print(a)
    

DOI_list = [a[0][1:] for a in df["DOI"].tolist()]
print(DOI_list)


from pyvis.network import Network
from time import time

def pyvis_show(graf, phi=False, name="Default"):
    net = Network()
    net.from_nx(graf)
    net.toggle_physics(phi)
    net.show("{}_{}.html".format(name, time()))

def networkx_plot(graf, name="Default"):
    node_sizes = [50*len(graf.edges(n)) for n in graf.nodes()]
    edges = graf.edges()
    #weights = [graf[u][v]['weight']/100 for u,v in edges]
    nx.draw_networkx(graf, pos=nx.kamada_kawai_layout(graf), node_size=node_sizes)
    plt.show() 
    

import matplotlib.pyplot as plt
import networkx as nx

from semanticscholar import SemanticScholar
sch = SemanticScholar()
list_of_paper_ids = DOI_list[::5]
results = sch.get_papers(list_of_paper_ids)
print(results[0])
exit()
# Create a graph
G = nx.Graph()
N = 50
for k, item in enumerate(results):
    

    authors = [author['name'] for author in item.authors]

    for i, author1 in enumerate(authors):
        for j, author2 in enumerate(authors):
            if i != j:
                G.add_edge(author1, author2)
                
    if k > N:
        break
# Plot the graph
networkx_plot(G)