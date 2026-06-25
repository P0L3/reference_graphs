import requests
import pandas as pd

BASE_URL = "https://www.croris.hr/znanstvenici-api"
headers = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0"
}

# Your input table
df = pd.DataFrame([
    {"node_id": "matijašević_maja", "name": "Maja", "surname": "Matijašević", "institution": "FIDIT", "croris_id": 8666, "pers_id": None},
    {"node_id": "ipšić_ivo", "name": "Ivo", "surname": "Ipšić", "institution": "FIDIT", "croris_id": 5033, "pers_id": 5033},
    {"node_id": "pavlić_mile", "name": "Mile", "surname": "Pavlić", "institution": "FIDIT", "croris_id": 8822, "pers_id": 8822},
])

def fetch_all_scientists(page_size=100):
    """Paginated fetch from /znanstvenik"""
    page = 1
    all_items = []

    while True:
        url = f"{BASE_URL}/znanstvenik"
        params = {"pageNumber": page, "pageSize": page_size}

        r = requests.get(url, params=params, headers=headers)
        r.raise_for_status()
        data = r.json()

        items = data.get("_embedded", {}).get("znanstvenici", [])
        if not items:
            break

        all_items.extend(items)

        if len(items) < page_size:
            break

        page += 1

    return all_items


def extract_institution(scientist):
    """Get current institution from employment records"""
    zapos = scientist.get("zaposlenjeResources", {}).get("_embedded", {}).get("zaposlenja", [])

    # Prefer active employment
    active = [z for z in zapos if z.get("aktivno") is True]

    if active:
        return active[0].get("ustanova", {}).get("naziv")

    # fallback: any employment
    if zapos:
        return zapos[0].get("ustanova", {}).get("naziv")

    return None


def build_index(scientists):
    """Index by (name, surname)"""
    index = {}
    for s in scientists:
        key = (s.get("ime", "").strip().lower(),
               s.get("prezime", "").strip().lower())
        index[key] = s
    return index


# 1. fetch API data
scientists = fetch_all_scientists()

# 2. index for matching
index = build_index(scientists)

# 3. enrich dataframe
institutions = []

for _, row in df.iterrows():
    key = (row["name"].strip().lower(), row["surname"].strip().lower())

    scientist = index.get(key)

    if scientist:
        inst = extract_institution(scientist)
    else:
        inst = None

    institutions.append(inst)

df["resolved_institution"] = institutions

print(df)