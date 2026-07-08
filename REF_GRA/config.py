# config.py
#
# Single source of truth for every institution/faculty-related constant used
# across the pipeline (fetch, build, run_pipeline, RQ modules, and all plotting
# scripts). Add, remove, or re-color an institution here ONLY — nothing else
# should hardcode a faculty acronym, color, or marker again.

# ---------------------------------------------------------------------------
# 1. THE INSTITUTION ROSTER
# ---------------------------------------------------------------------------
# Add a new institution by adding one entry here. `crosbi_id` and `mbu` are
# required by fetch_crosbi_data.py to query the CROSBI/CroRIS APIs.
INSTITUTIONS = [
    {"name": "FIDIT", "crosbi_id": 289, "mbu": 318},
    {"name": "FABRI", "crosbi_id": 303, "mbu": 335},
    {"name": "FZF",   "crosbi_id": 288, "mbu": 316},
    {"name": "FM",    "crosbi_id": 290, "mbu": 319},
]

# ---------------------------------------------------------------------------
# 2. DERIVED DATASET LIST
# ---------------------------------------------------------------------------
# The combined/global dataset name is DERIVED from INSTITUTIONS, never typed
# out by hand, so it can't silently drift out of sync (e.g. if an institution
# is added but someone forgets to update a hardcoded "FIDIT_FABRI_FZF_FM").
COMBINED_DATASET_NAME = "_".join(inst["name"] for inst in INSTITUTIONS)

# Every dataset run_pipeline.py / build_graph_crosbi_data.py / visuals.py etc.
# should iterate over: each institution alone, plus the combined university.
DATASETS = [inst["name"] for inst in INSTITUTIONS] + [COMBINED_DATASET_NAME]

# ---------------------------------------------------------------------------
# 3. SENTINEL LABELS
# ---------------------------------------------------------------------------
# The single label for "researcher not affiliated with any of the above
# institutions". Previously this was "External" in most scripts but "Unknown"
# in build_graph_crosbi_data.py's fillna — the two labels didn't merge in any
# groupby/value_counts, silently splitting one category into two.
EXTERNAL_LABEL = "External"

# Some existing exports/plots (built before the above was standardized) may
# still contain literal "Unknown" values on disk. Keep this alias so those
# older CSVs/GraphMLs still map to a defined color/marker instead of KeyError-ing,
# without encouraging any *new* code to write "Unknown" going forward.
LEGACY_UNKNOWN_LABEL = "Unknown"

# ---------------------------------------------------------------------------
# 4. COLOR PALETTE (Okabe-Ito, colorblind-safe)
# ---------------------------------------------------------------------------
OKABE_ITO = {
    "orange":     "#E69F00",
    "sky_blue":   "#56B4E9",
    "green":      "#009E73",
    "yellow":     "#F0E442",
    "blue":       "#0072B2",
    "vermillion": "#D55E00",
    "purple":     "#CC79A7",
    "black":      "#000000",
}

# Keyed by institution acronym (i.e. a per-node "institution" attribute value),
# NOT by dataset name. Every script that colors nodes/bars by institution
# should import this instead of defining its own map.
INSTITUTION_COLORS = {
    "FIDIT": OKABE_ITO["sky_blue"],
    "FABRI": OKABE_ITO["purple"],
    "FZF":   OKABE_ITO["vermillion"],   # tweaked for scatter visibility against the palette above
    "FM":    OKABE_ITO["green"],
    EXTERNAL_LABEL: "grey",
    LEGACY_UNKNOWN_LABEL: "lightgrey",
}

# ---------------------------------------------------------------------------
# 5. MARKER / SHAPE MAP
# ---------------------------------------------------------------------------
# Matplotlib marker codes, also keyed by institution acronym.
INSTITUTION_MARKERS = {
    "FIDIT": "^",   # Triangle Up
    "FABRI": "*",   # Star
    "FZF":   "s",   # Square
    "FM":    "D",   # Diamond
    EXTERNAL_LABEL: "o",   # Circle (fallback)
    LEGACY_UNKNOWN_LABEL: "o",
}