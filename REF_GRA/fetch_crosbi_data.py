import requests
import pandas as pd
import re
from tqdm import tqdm
import networkx as nx
import os
import datetime

# ==========================================
# 1. SETUP: NODE REGISTRY & DATA TABLES
# ==========================================
nodes_registry = {}
edges_table = []
keywords_table = []

# Define the institutions you want to analyze
institutions = [
    {"name": "FIDIT", "crosbi_id": 289, "mbu": 318},
    {"name": "FABRI", "crosbi_id": 303, "mbu": 335},
    {"name": "FZF",   "crosbi_id": 288, "mbu": 316},
    {"name": "FM",    "crosbi_id": 290, "mbu": 319},
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

def get_or_create_node(ime, prezime, croris_id=None, pers_id=None, institution=None):
    """
    Solves Entity Resolution: Matches researchers across APIs using a synthetic key
    and saves their dynamically resolved institution affiliation.
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
            "institution": institution or "Unknown",
            "croris_id": croris_id,
            "pers_id": pers_id
        }
    else:
        # Update IDs if we discover them later in different APIs
        if croris_id: 
            nodes_registry[synth_id]["croris_id"] = croris_id
        if pers_id: 
            nodes_registry[synth_id]["pers_id"] = pers_id
            
        # Overwrite "Unknown" if we have discovered a valid institution
        if institution and nodes_registry[synth_id]["institution"] == "Unknown":
            nodes_registry[synth_id]["institution"] = institution
        
    return synth_id

# Sets to keep track of processed data to prevent duplication in inter-institutional collaborations
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
        
        # Deduplication check
        if pub_url in processed_pubs:
            continue
        processed_pubs.add(pub_url)
        
        pub_resp = requests.get(pub_url)
        
        if pub_resp.status_code == 200:
            pub_data = pub_resp.json()
            pub_id = pub_data.get('crosbiId', 'unknown')
            
            # Safely extract year
            try:
                year = int(pub_data.get('godina', 0))
            except ValueError:
                year = 0
                
            # Skip Co-authorship generation if it is a student's thesis (ocjenski rad)
            is_thesis = "ocjenski" in str(pub_data.get('vrsta', '')).lower()
            
            # Dynamic Institution Resolution from publication metadata
            paper_institutions = []
            if 'ustanoveResources' in pub_data and '_embedded' in pub_data['ustanoveResources']:
                for u in pub_data['ustanoveResources']['_embedded'].get('ustanove', []):
                    u_id = u.get('crorisId') or u.get('id')
                    if u_id in ID_TO_ACRONYM:
                        paper_institutions.append(ID_TO_ACRONYM[u_id])
            
            # If the paper is associated with exactly one known institution, use it.
            # Otherwise, fall back to the queried loop institution.
            fallback_inst = ID_TO_ACRONYM.get(inst['crosbi_id'], "Unknown")
            resolved_inst = paper_institutions[0] if len(paper_institutions) == 1 else fallback_inst
            
            authors = []
            supervisors = []
            
            # 2a. Parse People (Authors & Mentors)
            if 'osobeResources' in pub_data and '_embedded' in pub_data['osobeResources']:
                for osoba in pub_data['osobeResources']['_embedded'].get('osobe', []):
                    print(osoba)
                    role_id = osoba.get('funkcija', {}).get('id')
                    croris_id = osoba.get('crorisId')
                    
                    # Register the node dynamically with resolved institution
                    node_id = get_or_create_node(
                        osoba.get('ime', ''), 
                        osoba.get('prezime', ''), 
                        croris_id=croris_id, 
                        institution=resolved_inst
                    )
                    
                    if role_id == 905: # Author
                        authors.append(node_id)
                    elif role_id == 907: # Supervisor/Mentor
                        supervisors.append(node_id)
                        # Only add supervisor to Layer 1 if this is a real research paper, NOT a student thesis
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
                            "source": sup, # Source is mentor
                            "target": auth, # Target is student/author
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
        
        # Deduplication check
        if proj_id in processed_projects:
            continue
        processed_projects.add(proj_id)
        
        # Safely extract start and end years
        try:
            start_year = int(proj.get('pocetak', '').split('.')[-1])
        except (ValueError, AttributeError):
            start_year = 0
            
        try:
            end_year = int(proj.get('kraj', '').split('.')[-1])
        except (ValueError, AttributeError):
            end_year = 2026 # Assume ongoing if no end date
            
        team_members = []
        
        # Extract People on the project
        if 'osobeResources' in proj and '_embedded' in proj['osobeResources']:
            for osoba in proj['osobeResources']['_embedded'].get('osobe', []):
                pers_id = osoba.get('persId')
                osoba_ust_id = osoba.get('ustanovaId')
                
                # Resolve institution from Project person payload
                resolved_inst = ID_TO_ACRONYM.get(osoba_ust_id)
                if not resolved_inst:
                    # Fallback string parsing for other UNIRI faculties if they show up in cooperation
                    ust_naziv = osoba.get('ustanovaNaziv', '').lower()
                    if "informatik" in ust_naziv or "digitalnih" in ust_naziv:
                        resolved_inst = "FIDIT"
                    elif "biotehnolog" in ust_naziv:
                        resolved_inst = "FABRI"
                    elif "fizik" in ust_naziv:
                        resolved_inst = "FZF"
                    elif "matemat" in ust_naziv:
                        resolved_inst = "FM"
                    else:
                        resolved_inst = ID_TO_ACRONYM.get(inst['mbu'], "Unknown")
                
                # Register node
                node_id = get_or_create_node(
                    osoba.get('ime', ''), 
                    osoba.get('prezime', ''), 
                    pers_id=pers_id, 
                    institution=resolved_inst
                )
                team_members.append(node_id)
                
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
# 4. EXPORT TO PANDAS DATAFRAMES
# ==========================================
df_nodes = pd.DataFrame(list(nodes_registry.values()))
df_edges = pd.DataFrame(edges_table)
df_keywords = pd.DataFrame(keywords_table)

# Generate a filename suffix based on institutions processed
inst_suffix = "_".join([inst['name'] for inst in institutions])

print("\n--- EXTRACTION COMPLETE ---")
print(f"Institutions processed: {', '.join([inst['name'] for inst in institutions])}")
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