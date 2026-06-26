import requests
import pandas as pd
import re
from tqdm import tqdm
import networkx as nx
import os
from datetime import datetime

# ==========================================
# 1. SETUP: NODE REGISTRY & DATA TABLES
# ==========================================
nodes_registry = {}
edges_table = []
keywords_table = []

# Define the institutions you want to analyze
institutions = [
    {"name": "FIDIT", "crosbi_id": 289, "mbu": 318},
    # {"name": "FABRI", "crosbi_id": 303, "mbu": 335},
    # {"name": "FZF",   "crosbi_id": 288, "mbu": 316},
    # {"name": "FM",    "crosbi_id": 290, "mbu": 319},
]

# Central Map to translate CroRIS IDs and MBUs to acronyms
ID_TO_ACRONYM = {
    # CROSBI Institution IDs
    289: "FIDIT",
    303: "FABRI",
    288: "FZF",
    290: "FM",
    # MBU IDs (Projects API)
    318: "FIDIT",
    335: "FABRI",
    316: "FZF",
    319: "FM"
}

def get_or_create_node(ime, prezime, croris_id=None, pers_id=None):
    """
    Solves Entity Resolution and initializes voting and resolution metadata.
    """
    ime = str(ime).strip()
    prezime = str(prezime).strip()
    # Create a synthetic ID (e.g., "pavlić_mile")
    synth_id = f"{prezime.lower()}_{ime.lower()}"
    
    if synth_id not in nodes_registry:
        nodes_registry[synth_id] = {
            "node_id": synth_id,
            "name": ime,
            "surname": prezime,
            "croris_id": croris_id,
            "pers_id": pers_id,
            # Resolution meta fields (removed before saving to CSV)
            "project_institution": None,
            "publication_votes": {},
            "external_institution_name": None
        }
    else:
        # Update IDs if we discover them later in different APIs
        if croris_id: 
            nodes_registry[synth_id]["croris_id"] = croris_id
        if pers_id: 
            nodes_registry[synth_id]["pers_id"] = pers_id
        
    return synth_id

# Sets to keep track of processed data to prevent duplication
processed_pubs = set()
processed_projects = set()

# ==========================================
# 2. EXTRACT LAYERS 1, 2, & 3 (CROSBI API)
# ==========================================
print("Fetching Publications from CROSBI...")

for inst in institutions:
    institution_url = f"https://www.croris.hr/crosbi-api/ustanova/{inst['crosbi_id']}"
    response = requests.get(institution_url)

    if response.status_code == 200:
        publications = response.json().get('_links', {}).get('publikacije', [])
    else:
        publications = []
        print(f"Error fetching publications list for {inst['name']}.")

    # Iterate through publications
    for pub in tqdm(publications, desc=f"Pubs {inst['name']}"):
        pub_url = pub['href']
        
        if pub_url in processed_pubs:
            continue
        processed_pubs.add(pub_url)
        
        pub_resp = requests.get(pub_url)
        
        if pub_resp.status_code == 200:
            pub_data = pub_resp.json()
            pub_id = pub_data.get('crosbiId', 'unknown')
            
            try:
                year = int(pub_data.get('godina', 0))
            except ValueError:
                year = 0
                
            # Skip Co-authorship generation if it is a student's thesis (ocjenski rad)
            is_thesis = "ocjenski" in str(pub_data.get('vrsta', '')).lower()
            
            authors = []
            supervisors = []
            
            # 2a. Parse People (Authors & Mentors)
            if 'osobeResources' in pub_data and '_embedded' in pub_data['osobeResources']:
                for osoba in pub_data['osobeResources']['_embedded'].get('osobe', []):
                    role_id = osoba.get('funkcija', {}).get('id')
                    croris_id = osoba.get('crorisId')
                    
                    # Register the node
                    node_id = get_or_create_node(osoba.get('ime', ''), osoba.get('prezime', ''), croris_id=croris_id)
                    
                    # Log a vote for this queried institution (Solution 1)
                    votes = nodes_registry[node_id]["publication_votes"]
                    votes[inst['name']] = votes.get(inst['name'], 0) + 1
                    
                    if role_id == 905: # Author
                        authors.append(node_id)
                    elif role_id == 907: # Supervisor/Mentor
                        supervisors.append(node_id)
                        if not is_thesis:
                            authors.append(node_id)
            
            # 2b. Build Layer 1: Co-authorship Edges
            for i in range(len(authors)):
                for j in range(i + 1, len(authors)):
                    edges_table.append({
                        "source": authors[i],
                        "target": authors[j],
                        "layer": "co-authorship",
                        "weight": 1,
                        "year_start": year,
                        "year_end": year,
                        "context": f"pub_{pub_id}"
                    })
                    
            # 2c. Build Layer 2: Mentorship Edges (Directed)
            for sup in supervisors:
                for auth in authors:
                    if sup != auth:
                        edges_table.append({
                            "source": sup,
                            "target": auth,
                            "layer": "mentorship",
                            "weight": 1,
                            "year_start": year,
                            "year_end": year,
                            "context": f"pub_{pub_id}"
                        })
                        
            # 2d. Build Layer 3: Keyword Associations
            if 'kljucneRijeci' in pub_data:
                for kr in pub_data['kljucneRijeci']:
                    naziv = kr.get('naziv', '')
                    kw_list = [k.strip().lower() for k in re.split(r'[;,]', naziv) if k.strip()]
                    
                    for kw in kw_list:
                        for auth in authors:
                            keywords_table.append({
                                "node_id": auth,
                                "keyword": kw,
                                "year": year,
                                "context": f"pub_{pub_id}"
                            })

# ==========================================
# 3. EXTRACT LAYER 4 (PROJEKTI API)
# ==========================================
print("\nFetching Projects from CRORIS...")

for inst in institutions:
    projects_url = f"https://www.croris.hr/projekti-api/projekt/ustanova/{inst['mbu']}"
    proj_resp = requests.get(projects_url)

    if proj_resp.status_code == 200:
        projects_data = proj_resp.json().get('_embedded', {}).get('projekti', [])
    else:
        projects_data = []
        print(f"Error fetching projects for {inst['name']}.")

    for proj in tqdm(projects_data, desc=f"Proj {inst['name']}"):
        proj_id = proj.get('id', 'unknown')
        
        if proj_id in processed_projects:
            continue
        processed_projects.add(proj_id)
        
        try:
            start_year = int(proj.get('pocetak', '').split('.')[-1])
        except (ValueError, AttributeError):
            start_year = 0
            
        try:
            end_year = int(proj.get('kraj', '').split('.')[-1])
        except (ValueError, AttributeError):
            end_year = 2026
            
        team_members = []
        
        # Extract People on the project
        if 'osobeResources' in proj and '_embedded' in proj['osobeResources']:
            for osoba in proj['osobeResources']['_embedded'].get('osobe', []):
                pers_id = osoba.get('persId')
                osoba_ust_id = osoba.get('ustanovaId')
                osoba_ust_name = osoba.get('ustanovaNaziv', 'External')
                
                # Register node
                node_id = get_or_create_node(osoba.get('ime', ''), osoba.get('prezime', ''), pers_id=pers_id)
                team_members.append(node_id)
                
                # Resolve primary institution (Solution 2 - High Trust Projects Metadata) [1]
                resolved_inst = ID_TO_ACRONYM.get(osoba_ust_id)
                if resolved_inst:
                    # Lock in their core target institution affiliation [1]
                    nodes_registry[node_id]["project_institution"] = resolved_inst
                else:
                    # Mark them as External and capture their actual faculty name (Solution 3) [1]
                    nodes_registry[node_id]["project_institution"] = "External"
                    nodes_registry[node_id]["external_institution_name"] = osoba_ust_name
                
        # Build Layer 4: Project Co-participation
        for i in range(len(team_members)):
            for j in range(i + 1, len(team_members)):
                edges_table.append({
                    "source": team_members[i],
                    "target": team_members[j],
                    "layer": "project",
                    "weight": 1,
                    "year_start": start_year,
                    "year_end": end_year,
                    "context": f"proj_{proj_id}"
                })

# ==========================================
# 4. EXPORT TO PANDAS DATAFRAMES & DYNAMIC AFFILIATION RESOLUTION
# ==========================================
print("\nResolving dynamic institutional affiliations (Tiered Strategy)...")

# Process final institution metadata using our hierarchy rule [1]
for node_id, data in nodes_registry.items():
    # Rule 1: Project metadata is absolute truth (includes explicit External labeling) [1]
    if data["project_institution"] is not None:
        data["institution"] = data["project_institution"]
        if data["institution"] == "External" and data["external_institution_name"]:
            # We can optionally keep the detailed name in a secondary field for researchers to analyze
            data["ext_affiliation"] = data["external_institution_name"]
            
    # Rule 2: Fallback to majority voting on publications queries [1]
    elif data["publication_votes"]:
        # Assign the queried institution they appeared in most frequently [1]
        best_inst = max(data["publication_votes"], key=data["publication_votes"].get)
        data["institution"] = best_inst
        
    # Rule 3: No programmatic overlap - Mark as External
    else:
        data["institution"] = "External"
        
    # Clean up voting helper variables so they are omitted from CSV
    del data["publication_votes"]
    del data["project_institution"]
    del data["external_institution_name"]

# Construct DataFrames
df_nodes = pd.DataFrame(list(nodes_registry.values()))
df_edges = pd.DataFrame(edges_table)
df_keywords = pd.DataFrame(keywords_table)

inst_suffix = "_".join([inst['name'] for inst in institutions])

print("\n" + "="*42)
print("  EXTRACTION COMPLETE & DISAMBIGUATED")
print("="*42)
print(f"Institutions analyzed: {', '.join([inst['name'] for inst in institutions])}")
print(f"Total Unique Nodes (Researchers): {len(df_nodes)}")
print(f"Total Edge Records: {len(df_edges)}")
print(f"Total Keyword Associations: {len(df_keywords)}")

# Define filenames
nodes_file = f"nodes_{inst_suffix}.csv"
edges_file = f"edges_{inst_suffix}.csv"
keywords_file = f"keywords_{inst_suffix}.csv"

# Save to CSV
df_nodes.to_csv(nodes_file, index=False)
df_edges.to_csv(edges_file, index=False)
df_keywords.to_csv(keywords_file, index=False)

print(f"\nFiles saved successfully:")
print(f" - {nodes_file}")
print(f" - {edges_file}")
print(f" - {keywords_file}")