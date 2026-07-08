import pandas as pd
import numpy as np
from itertools import combinations
import warnings
warnings.filterwarnings('ignore')

# --- CONFIGURATION ---
FILE_PATH = "edges_FIDIT_FABRI_FZF_FM.csv"
CURRENT_YEAR = 2026
DIVORCE_BUFFER = 3  # Years of silence required to declare a collaboration "dead"
PHD_WINDOW = 6      # Standard PhD lifecycle in years

print("==========================================================")
print("  M-ONA TEMPORAL DYNAMICS & SOCIOLOGICAL EVOLUTION ENGINE")
print("==========================================================\n")

def norm_edge(u, v):
    return tuple(sorted([str(u), str(v)]))

try:
    print("Loading temporal edge data...")
    df = pd.read_csv(FILE_PATH)
    df = df.dropna(subset=['source', 'target', 'year_start'])
    df['year_start'] = pd.to_numeric(df['year_start'], errors='coerce').fillna(CURRENT_YEAR)
    df['year_end'] = pd.to_numeric(df['year_end'], errors='coerce').fillna(CURRENT_YEAR)
    
    # Layer specific dataframes
    df_co = df[df['layer'] == 'co-authorship'].copy()
    df_proj = df[df['layer'] == 'project'].copy()
    df_ment = df[df['layer'] == 'mentorship'].copy()
    
    df_co['edge'] = df_co.apply(lambda x: norm_edge(x['source'], x['target']), axis=1)
    df_proj['edge'] = df_proj.apply(lambda x: norm_edge(x['source'], x['target']), axis=1)

    # ---------------------------------------------------------
    # 1. ACADEMIC DIVORCE & COLLABORATION HALF-LIFE
    # ---------------------------------------------------------
    print("\n--- 1. ACADEMIC DIVORCE (Independent Survival) ---")
    # Get last publication year for every pair
    last_collab = df_co.groupby('edge')['year_start'].max().to_dict()
    # Get last publication year for every individual researcher
    last_pub_node = pd.concat([df_co[['source', 'year_start']].rename(columns={'source':'node'}), 
                               df_co[['target', 'year_start']].rename(columns={'target':'node'})])
    last_pub_node = last_pub_node.groupby('node')['year_start'].max().to_dict()
    
    total_collabs = len(last_collab)
    dead_collabs = 0
    true_divorces = 0
    project_linked_deaths = 0

    proj_end_dates = df_proj.groupby('edge')['year_end'].max().to_dict()

    for edge, final_year in last_collab.items():
        u, v = edge
        if final_year <= CURRENT_YEAR - DIVORCE_BUFFER:
            dead_collabs += 1
            # Did they independently survive? (Both published with OTHERS recently)
            if last_pub_node.get(u, 0) > final_year and last_pub_node.get(v, 0) > final_year:
                true_divorces += 1
                # Was this tied to a project ending?
                if edge in proj_end_dates:
                    p_end = proj_end_dates[edge]
                    if abs(p_end - final_year) <= 2:  # Project ended within 2 years of last paper
                        project_linked_deaths += 1

    print(f"Total historical collaborations evaluated: {total_collabs}")
    print(f"Inactive collaborations (no papers since {CURRENT_YEAR - DIVORCE_BUFFER}): {dead_collabs}")
    print(f"True Academic Divorces (tie severed, but BOTH researchers still active): {true_divorces}")
    if true_divorces > 0:
        print(f"  -> Divorces tightly coupled to a Project expiring: {project_linked_deaths} ({(project_linked_deaths/true_divorces)*100:.1f}%)")

    # ---------------------------------------------------------
    # 2. THE MENTORSHIP LIFECYCLE (Attrition vs Emancipation)
    # ---------------------------------------------------------
    print("\n--- 2. THE MENTORSHIP LIFECYCLE (6-Year Window) ---")
    # Identify T_start for mentorships
    first_mentorship = df_ment.groupby(['source', 'target'])['year_start'].min().reset_index()
    
    exodus, trapped, emancipated = 0, 0, 0
    evaluated_students = 0

    for _, row in first_mentorship.iterrows():
        mentor, student, t_start = row['source'], row['target'], row['year_start']
        t_eval = t_start + PHD_WINDOW
        
        if t_eval <= CURRENT_YEAR: # Only evaluate students who theoretically finished
            evaluated_students += 1
            # Student's publications AFTER the 6-year mark
            student_future_pubs = df_co[(df_co['source'] == student) | (df_co['target'] == student)]
            student_future_pubs = student_future_pubs[student_future_pubs['year_start'] >= t_eval]
            
            if student_future_pubs.empty:
                exodus += 1
            else:
                # Did they publish WITHOUT the mentor?
                future_coauthors = set(student_future_pubs['source']).union(set(student_future_pubs['target'])) - {student}
                if mentor in future_coauthors and len(future_coauthors) == 1:
                    trapped += 1
                else:
                    emancipated += 1

    print(f"Evaluated complete mentorship lifecycles (started before {CURRENT_YEAR - PHD_WINDOW}): {evaluated_students}")
    if evaluated_students > 0:
        print(f"  Brain Drain / Exodus (0 papers after 6 yrs): {exodus} ({(exodus/evaluated_students)*100:.1f}%)")
        print(f"  Trapped (Only publishes with Mentor): {trapped} ({(trapped/evaluated_students)*100:.1f}%)")
        print(f"  Emancipated (Independent publishing network): {emancipated} ({(emancipated/evaluated_students)*100:.1f}%)")

    # ---------------------------------------------------------
    # 3. ADMINISTRATIVE PARASITISM (Trophy PIs)
    # ---------------------------------------------------------
    print("\n--- 3. ADMINISTRATIVE PARASITISM (The Trophy PI) ---")
    projects = df_proj.groupby('context')
    total_proj_members = 0
    parasite_members = 0
    
    for context, group in projects:
        members = set(group['source']).union(set(group['target']))
        if len(members) >= 3:
            p_start = group['year_start'].min()
            p_end = group['year_end'].max()
            
            # Find co-authorships DURING the project window
            active_co = df_co[(df_co['year_start'] >= p_start) & (df_co['year_start'] <= p_end)]
            active_edges = set(active_co['edge'])
            
            for m in members:
                total_proj_members += 1
                # Did 'm' co-author with ANY other project member during the grant?
                co_authored_internally = any(norm_edge(m, peer) in active_edges for peer in members if peer != m)
                if not co_authored_internally:
                    parasite_members += 1

    print(f"Total member-project assignments evaluated (teams >= 3): {total_proj_members}")
    if total_proj_members > 0:
        print(f"Administratively funded but scientifically inactive members (Trophy PIs): {parasite_members} ({(parasite_members/total_proj_members)*100:.1f}%)")

    # ---------------------------------------------------------
    # 4. CROSS-LAYER GRANGER CAUSALITY (Genesis of Integration)
    # ---------------------------------------------------------
    print("\n--- 4. CROSS-LAYER CAUSALITY (Genesis of Ties) ---")
    overlap_edges = set(df_proj['edge']).intersection(set(df_co['edge']))
    
    proj_leads, paper_leads, simultaneous = 0, 0, 0
    
    for edge in overlap_edges:
        min_p = df_proj[df_proj['edge'] == edge]['year_start'].min()
        min_c = df_co[df_co['edge'] == edge]['year_start'].min()
        
        if min_p < min_c: proj_leads += 1
        elif min_c < min_p: paper_leads += 1
        else: simultaneous += 1
            
    total_genesis = proj_leads + paper_leads + simultaneous
    if total_genesis > 0:
        print(f"Structurally overlapping ties analyzed: {total_genesis}")
        print(f"  Funding preceded Science (Project -> Paper): {proj_leads} ({(proj_leads/total_genesis)*100:.1f}%)")
        print(f"  Science preceded Funding (Paper -> Project): {paper_leads} ({(paper_leads/total_genesis)*100:.1f}%)")

    # ---------------------------------------------------------
    # 5. GOLDEN HANDCUFFS (Topological Rigidification)
    # ---------------------------------------------------------
    print("\n--- 5. GOLDEN HANDCUFFS (Neighborhood Exploration) ---")
    # For a subset of highly active nodes, check their exploration rate
    node_paper_counts = pd.concat([df_co['source'], df_co['target']]).value_counts()
    active_nodes = node_paper_counts[node_paper_counts >= 10].index.tolist()
    
    on_proj_rates = []
    off_proj_rates = []

    for node in active_nodes:
        # Get active project years
        node_projs = df_proj[(df_proj['source'] == node) | (df_proj['target'] == node)]
        active_proj_years = set()
        for _, row in node_projs.iterrows():
            active_proj_years.update(range(int(row['year_start']), int(row['year_end']) + 1))
            
        # Get first year they published with each specific co-author
        node_co = df_co[(df_co['source'] == node) | (df_co['target'] == node)]
        new_ties_per_year = {}
        for _, row in node_co.iterrows():
            coauthor = row['target'] if row['source'] == node else row['source']
            yr = row['year_start']
            if coauthor not in new_ties_per_year or yr < new_ties_per_year[coauthor]:
                new_ties_per_year[coauthor] = yr
                
        # Count new ties per year
        yr_counts = pd.Series(list(new_ties_per_year.values())).value_counts().to_dict()
        
        if active_proj_years and len(yr_counts) > 0:
            on_proj_new = [yr_counts.get(y, 0) for y in active_proj_years if y <= CURRENT_YEAR]
            all_pub_years = set(node_co['year_start'])
            off_proj_years = all_pub_years - active_proj_years
            off_proj_new = [yr_counts.get(y, 0) for y in off_proj_years if y <= CURRENT_YEAR]
            
            if on_proj_new: on_proj_rates.append(np.mean(on_proj_new))
            if off_proj_new: off_proj_rates.append(np.mean(off_proj_new))

    print(f"Evaluated highly active researchers (>= 10 papers): {len(active_nodes)}")
    print(f"  Avg new unique co-authors per year while ON active projects: {np.mean(on_proj_rates):.2f}")
    print(f"  Avg new unique co-authors per year while OFF active projects: {np.mean(off_proj_rates):.2f}")

except Exception as e:
    print(f"Error executing script: {e}")