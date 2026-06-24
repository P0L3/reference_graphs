#!/usr/bin/env python
# coding: utf-8

# Environment
# 
# ```shell
# 
# conda create -n refgra python=3.10
# 
# conda activate refgra
# 
# conda install pandas networkx matplotlib pyvis ipykernel requests tqdm -y
# ```

# ## Libraries

# In[3]:


import requests
import pandas as pd
from tqdm import tqdm
import networkx as nx

from matplotlib import pyplot as plt
from time import time

from pyvis.network import Network

import re

from copy import deepcopy


# ### Helper functions

# In[4]:


# Helper functions

def pyvis_show_c(graf, phi=False, name="Default"):
    net = Network()
    net.from_nx(graf)
    net.toggle_physics(phi)

    # Normalize weights to control alpha transparency
    weights = [data.get("weight", 1) for _, _, data in graf.edges(data=True)]
    min_w, max_w = min(weights), max(weights)
    range_w = max_w - min_w if max_w != min_w else 1

    for u, v, data in graf.edges(data=True):
        weight = data.get("weight", 1)
        # Normalize weight to 0–1
        normalized = (weight - min_w) / range_w
        # Map to alpha: low weight = more transparent, high weight = more opaque
        alpha = 0.2 + 0.8 * normalized  # Keep a minimum alpha to prevent invisibility
        alpha = min(max(alpha, 0.2), 1.0)

        rgba_color = f"rgba(0,0,0,{alpha:.2f})"
        data["color"] = rgba_color  # Set the edge color in the original graph

    net.from_nx(graf)  # Re-import the modified graph with edge colors
    net.show(f"{name}_{int(time())}.html", notebook=False)

    


def networkx_plot(graf, name="Default"):
    node_sizes = [50*len(graf.edges(n)) for n in graf.nodes()]
    edges = graf.edges()
    #weights = [graf[u][v]['weight']/100 for u,v in edges]
    nx.draw_networkx(graf, pos=nx.kamada_kawai_layout(graf), node_size=node_sizes)
    plt.show() 
    
def authorstringlist2dict(stringlist):
    """
    Converts a string of authors (formatted as 'surname, name', separated by semicolons) 
    into a list of dictionaries with 'name', 'surname', 'authorId', and 'role'.

    Args:
        stringlist (str): Authors in the format 'surname, name', separated by ';'.

    Returns:
        list: List of dictionaries, each containing author details.
    """
    authorlist = []
    if ";" in stringlist:
        for author in stringlist.split(";"):
            authorlist.append({"name": author.split(",")[1], "surname": author.split(",")[0], "authorId": author.replace(",", "").replace(" ", ""), "role": {'id': 905, 'naziv': 'autor/i'}})
    else:
        for author in [stringlist]:
            try:
                authorlist.append({"name": author.split(",")[1], "surname": author.split(",")[0], "authorId": author.replace(",", "").replace(" ", ""), "role": {'id': 905, 'naziv': 'autor/i'}})
            except IndexError:
                authorlist.append({"name": author.split(" ")[1], "surname": author.split(" ")[0], "authorId": author.replace(",", "").replace(" ", ""), "role": {'id': 905, 'naziv': 'autor/i'}})
        
    return authorlist

def process_authors(authors):
    """
    Processes a list of authors by removing duplicates based on name and surname similarity.
    Authors are listed first, followed by supervisors (role ID 907).

    Args:
        authors (list): A list of dictionaries, each containing 'name', 'surname', 'authorId', and 'role' info.

    Returns:
        list: A list of unique authors with supervisors appended at the end.
    """
    # Deep copy of the list to avoid modifying the original input
    result_d = deepcopy(authors)
    
    # Remove duplicates by comparing names and surnames
    for i, author1 in enumerate(authors):
        for author2 in authors[i+1:]:
            if author1["name"].strip().lower() == author2["name"].strip().lower() and isinstance(author2["authorId"], str):
                surname1 = re.split(r"[ -]", author1["surname"])
                surname2 = re.split(r"[ -]", author2["surname"])
                
                if bool(set(surname1) & set(surname2)):  # Check if surnames overlap
                    result_d.remove(author2)
                    continue
    
    # Separate authors and supervisors
    authors_final = []
    supervisers = []

    for author in result_d:
        if author["role"]["id"] == 907:  # If the role is supervisor
            supervisers.append(author)
        else:  # If the role is author
            authors_final.append(author)
    
    # Append supervisors to the end of the authors list
    authors_final.extend(supervisers)
    
    return authors_final


# ## Data gathering from Croris API

# In[5]:


# Step 1: Get the list of publications for the institution
institution_url = "https://www.croris.hr/crosbi-api/ustanova/289"

# Fetch the list of publications
response = requests.get(institution_url)
if response.status_code == 200:
    data = response.json()
    publications = data['_links']['publikacije']  # Get the list of publications
else:
    print(f"Error fetching data from {institution_url}. Status code: {response.status_code}")

data_list = []
# Step 2: Loop through each publication and fetch details
for publication in tqdm(publications):
    publication_url = publication['href']  # URL for each publication
    pub_response = requests.get(publication_url)
    
    # print(pub_response.json())
    
    if pub_response.status_code == 200:
        pub_data = pub_response.json()
        # Process each publication (e.g., get the authors)
        # print(f"Title: {pub_data.get('naslov')}")
        title = pub_data.get('naslov')
        authors = []
        if 'osobeResources' in pub_data:
            superviser_flag = False
            for author in pub_data['osobeResources']['_embedded']['osobe']:
                if author['funkcija']['id'] in [905, 907]:
                    if author['funkcija']['id'] == 907:
                        superviser_flag = True
                    # print(f" - {author['ime']} {author['prezime']} {author['crorisId']}")
                    authors.append({"name": author['ime'], "surname": author['prezime'], "authorId": author['crorisId'], "role": author['funkcija']})
                    
        else:
            print("No authors found")
        
        # Add authors with no ID in the database (students)
        if superviser_flag:
            authors.extend(authorstringlist2dict(pub_data.get('autori')))
        
        if len(authors) < 1:
            authors.append("no_authors")
            
        year = pub_data.get('godina')
        DOI = pub_data.get('crosbiId')
        
        if not "no_authors" in authors:
            authors = process_authors(authors)
        
        paper_data = {
            "Title": title,
            "DOI": DOI,
            "Authors": authors
        }
        
        data_list.append(paper_data)
        
    else:
        print(f"Error fetching data from {publication_url}. Status code: {pub_response.status_code}")
        
df = pd.DataFrame(data_list)


# ### Data info

# In[15]:


df[df["Authors"].apply(lambda x: x != ["no_authors"])]


# In[6]:


print(df.info())
# Calculate the percentage of rows where the "Authors" column contains the list ["no_authors"]
percentage = len(df[df["Authors"].apply(lambda x: x == ["no_authors"])]) / len(df) * 100

# Print the percentage
print(f"\nPercentage of papers with no aparent authors: {percentage:.2f} %\n")
print(df[df["Authors"].apply(lambda x: x == ["no_authors"])])


# ### Data export

# In[7]:


df.to_csv(f"./DATA/crosbi_data_{len(df)}_2.csv")
df.to_pickle(f"./DATA/crosbi_data_{len(df)}_2.pickle")


# ## Data loading

# In[8]:


DIR = "./DATA/crosbi_data_1215_2.pickle"

df = pd.read_pickle(DIR)


# In[9]:


# Create a graph
G = nx.Graph()
N = 1200
for k, item in enumerate(df.iterrows()):
    if item[1]["Authors"][0] == "no_authors":
        continue
    
    print(item[1]["Authors"][0]['authorId'])
    

    authors = [(author['authorId'], author['name'] + " " + author['surname']) for author in item[1]["Authors"]]
    print(authors)
    
    for i, author1 in enumerate(authors):
        for j, author2 in enumerate(authors):
            if i != j:
                G.add_node(author1[0], label=author1[1])
                G.add_node(author2[0], label=author2[1])
                
                if G.has_edge(author1[0], author2[0]):
                    G[author1[0]][author2[0]]['weight'] += 1
                elif G.has_edge(author2[0], author1[0]):
                    G[author2[0]][author1[0]]['weight'] += 1
                else:
                    G.add_edge(author1[0], author2[0], weight=1)    
    if k > N:
        break
# Plot the graph
pyvis_show_c(G, phi=True, name="author_reference_graph")


# In[11]:


nx.write_graphml(G, "author_reference_graph_crosbi_240626.graphml")

