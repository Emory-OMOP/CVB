"""Browse & Map — filter, select, map, and save individual rows."""

import sys

import pandas as pd
import streamlit as st

from lib.csv_io import save_mapping_csv
from lib.db import search_concepts


def _get_constants():
    from lib.vocab_discovery import find_repo_root
    repo_root = find_repo_root()
    scripts_dir = str(repo_root / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import cvb_constants
    return cvb_constants


constants = _get_constants()

# --- Get shared state ---
cache_key = st.session_state.get("cache_key")
if not cache_key or cache_key not in st.session_state:
    st.error("No mapping file loaded. Select a file in the sidebar.")
    st.stop()

df: pd.DataFrame = st.session_state[cache_key]
selected_file = st.session_state["selected_file"]
selected_vocab = st.session_state["selected_vocab"]
assignment_filter = st.session_state.get("assignment_filter")
db_available = st.session_state.get("db_available", False)

# ── Filters ──────────────────────────────────────────────────────────────
st.header(f"Browse & Map — {selected_file.name}")

filter_cols = st.columns([1, 1, 1, 2, 1])

with filter_cols[0]:
    all_predicates = sorted(df["predicate_id"].unique()) if "predicate_id" in df.columns else []
    predicate_filter = st.multiselect(
        "Predicate",
        all_predicates,
        default=["noMatch"] if "noMatch" in all_predicates else [],
    )

with filter_cols[1]:
    all_statuses = sorted(df["status"].unique()) if "status" in df.columns else []
    status_filter = st.multiselect("Status", all_statuses)

with filter_cols[2]:
    sort_options = {
        "Frequency (desc)": ("ws_frequency", False),
        "Description (asc)": ("source_description", True),
        "Code": ("source_concept_code", True),
    }
    # Only show frequency sort if column exists
    available_sorts = {
        k: v for k, v in sort_options.items()
        if v[0] in df.columns
    }
    if not available_sorts:
        available_sorts = {"Code": ("source_concept_code", True)}
    sort_by = st.selectbox("Sort by", list(available_sorts.keys()))

with filter_cols[3]:
    desc_search = st.text_input("Search description", placeholder="Type to filter...")

with filter_cols[4]:
    st.write("")  # spacer
    st.write("")
    show_mapped = st.checkbox("Include mapped", value=False)

# ── Apply filters ────────────────────────────────────────────────────────
filtered = df.copy()

# Assignment filter from sidebar
if assignment_filter and "ws_assignment_code" in filtered.columns:
    filtered = filtered[filtered["ws_assignment_code"] == assignment_filter]

# Predicate filter
if predicate_filter and "predicate_id" in filtered.columns:
    filtered = filtered[filtered["predicate_id"].isin(predicate_filter)]

# Status filter
if status_filter and "status" in filtered.columns:
    filtered = filtered[filtered["status"].isin(status_filter)]

# Description search
if desc_search:
    mask = filtered["source_description"].str.contains(desc_search, case=False, na=False)
    if "source_description_synonym" in filtered.columns:
        mask = mask | filtered["source_description_synonym"].str.contains(desc_search, case=False, na=False)
    filtered = filtered[mask]

# Exclude already mapped unless checkbox
if not show_mapped and "predicate_id" in filtered.columns:
    already_mapped = constants.VALID_RELATIONSHIP_PREDICATES
    filtered = filtered[~filtered["predicate_id"].isin(already_mapped)]

# Sort
sort_col, sort_asc = available_sorts[sort_by]
if sort_col in filtered.columns:
    if sort_col == "ws_frequency":
        filtered = filtered.copy()
        filtered["_sort_freq"] = pd.to_numeric(filtered["ws_frequency"], errors="coerce").fillna(0)
        filtered = filtered.sort_values("_sort_freq", ascending=sort_asc).drop(columns=["_sort_freq"])
    else:
        filtered = filtered.sort_values(sort_col, ascending=sort_asc)

st.caption(f"{len(filtered):,} of {len(df):,} rows")

# ── Data table ───────────────────────────────────────────────────────────
display_cols = [
    c for c in [
        "source_concept_code", "source_description", "predicate_id",
        "target_concept_id", "target_concept_name", "confidence",
        "ws_frequency", "status",
    ] if c in filtered.columns
]

event = st.dataframe(
    filtered[display_cols].reset_index(drop=True),
    use_container_width=True,
    height=400,
    on_select="rerun",
    selection_mode="single-row",
    key="mapping_table",
)

# ── Mapping form ─────────────────────────────────────────────────────────
selected_rows = event.selection.rows if event.selection else []
if not selected_rows:
    st.info("Select a row above to edit its mapping.")
    st.stop()

# Get the actual DataFrame index for the selected row
selected_display_idx = selected_rows[0]
selected_row = filtered.iloc[selected_display_idx]
original_idx = filtered.index[selected_display_idx]

st.divider()
st.subheader("Edit Mapping")

col_left, col_right = st.columns(2)

# ── Left: source details (read-only) ────────────────────────────────────
with col_left:
    st.markdown("**Source Details**")
    detail_fields = [
        ("Code", "source_concept_code"),
        ("Description", "source_description"),
        ("Synonym", "source_description_synonym"),
        ("Domain", "source_domain"),
        ("Frequency", "ws_frequency"),
        ("Assignment", "ws_assignment_code"),
        ("Notes", "ws_notes"),
    ]
    for label, col in detail_fields:
        val = selected_row.get(col, "")
        if val:
            if col == "ws_frequency":
                try:
                    val = f"{int(float(val)):,}"
                except (ValueError, TypeError):
                    pass
            st.text_input(label, value=val, disabled=True, key=f"src_{col}")

# ── Right: editable mapping fields ───────────────────────────────────────
with col_right:
    st.markdown("**Mapping Fields**")

    # Predicate selector
    predicate_options = sorted(constants.VALID_PREDICATES)
    current_pred = selected_row.get("predicate_id", "noMatch")
    if current_pred not in predicate_options:
        current_pred = constants.PREDICATE_ALIASES.get(current_pred, current_pred)
    pred_idx = predicate_options.index(current_pred) if current_pred in predicate_options else 0

    new_predicate = st.selectbox(
        "predicate_id",
        predicate_options,
        index=pred_idx,
        key="edit_predicate",
    )

    is_no_match = new_predicate == "noMatch"

    # Concept search
    if db_available and not is_no_match:
        search_term = st.text_input(
            "Search OMOP concepts",
            placeholder="Type concept name or code...",
            key="concept_search",
        )
        if search_term and len(search_term) >= 2:
            results = search_concepts(selected_vocab["path"], search_term)
            if results:
                concept_options = {
                    f"{r['concept_id']} — {r['concept_name']} ({r['vocabulary_id']})": r
                    for r in results
                }
                selected_concept_label = st.selectbox(
                    "Select concept",
                    list(concept_options.keys()),
                    key="concept_select",
                )
                selected_concept = concept_options[selected_concept_label]
            else:
                st.caption("No matching concepts found.")
                selected_concept = None
        else:
            selected_concept = None
    elif not db_available and not is_no_match:
        st.caption("DB offline — enter target fields manually below.")
        selected_concept = None
    else:
        selected_concept = None

    # Target fields — always editable; noMatch overrides to 0 at save time
    if is_no_match:
        st.caption("Target fields will be cleared on save (noMatch).")

    default_tid = selected_concept["concept_id"] if selected_concept else selected_row.get("target_concept_id", "")
    default_tname = selected_concept["concept_name"] if selected_concept else selected_row.get("target_concept_name", "")
    default_tvocab = selected_concept["vocabulary_id"] if selected_concept else selected_row.get("target_vocabulary_id", "")
    default_tdomain = selected_concept["domain_id"] if selected_concept else selected_row.get("target_domain_id", "")

    new_target_id = st.text_input("target_concept_id", value=str(default_tid), key="edit_tid")
    new_target_name = st.text_input("target_concept_name", value=str(default_tname), key="edit_tname")
    new_target_vocab = st.text_input("target_vocabulary_id", value=str(default_tvocab), key="edit_tvocab")
    new_target_domain = st.text_input("target_domain_id", value=str(default_tdomain), key="edit_tdomain")

    # Confidence
    current_conf = selected_row.get("confidence", "0")
    try:
        conf_val = float(current_conf) if current_conf else 0.0
    except ValueError:
        conf_val = 0.0
    new_confidence = st.number_input(
        "confidence",
        min_value=0.0,
        max_value=1.0,
        value=conf_val,
        step=0.1,
        key="edit_confidence",
    )

    # Mapping tool
    tool_options = [""] + sorted(constants.VALID_MAPPING_TOOLS)
    current_tool = selected_row.get("mapping_tool", "")
    tool_idx = tool_options.index(current_tool) if current_tool in tool_options else 0
    new_tool = st.selectbox("mapping_tool", tool_options, index=tool_idx, key="edit_tool")

    # Author
    new_author = st.text_input(
        "author_label",
        value=selected_row.get("author_label", ""),
        key="edit_author",
    )

    # Justification
    new_justification = st.text_area(
        "mapping_justification",
        value=selected_row.get("mapping_justification", ""),
        key="edit_justification",
    )

    # Status
    status_options = ["pending", "ready_for_review", "reviewed", "approved", "rejected"]
    current_status = selected_row.get("status", "pending")
    status_idx = status_options.index(current_status) if current_status in status_options else 0
    new_status = st.selectbox("status", status_options, index=status_idx, key="edit_status")

# ── Save button ──────────────────────────────────────────────────────────
if st.button("Save mapping", type="primary", use_container_width=True):
    # Update the row in the session DataFrame
    updates = {
        "predicate_id": new_predicate,
        "confidence": str(new_confidence),
        "mapping_tool": new_tool,
        "author_label": new_author,
        "mapping_justification": new_justification,
        "status": new_status,
    }

    if is_no_match:
        updates["target_concept_id"] = "0"
        updates["target_concept_name"] = ""
        updates["target_vocabulary_id"] = ""
        updates["target_domain_id"] = ""
    else:
        updates["target_concept_id"] = new_target_id
        updates["target_concept_name"] = new_target_name
        updates["target_vocabulary_id"] = new_target_vocab
        updates["target_domain_id"] = new_target_domain

    for col, val in updates.items():
        if col in df.columns:
            df.at[original_idx, col] = val

    # Save to disk
    try:
        save_mapping_csv(df, selected_file)
        st.session_state[cache_key] = df
        st.success(f"Saved mapping for {selected_row.get('source_concept_code', 'row')}.")
        st.rerun()
    except Exception as e:
        st.error(f"Save failed: {e}")
