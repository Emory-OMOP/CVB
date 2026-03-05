"""Bulk Upload — upload CSV, validate, merge, and save."""

import sys

import pandas as pd
import streamlit as st

from lib.csv_io import load_mapping_csv, save_mapping_csv
from lib.validation import validate_dataframe


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

st.header(f"Bulk Upload — {selected_file.name}")

# ── Upload ───────────────────────────────────────────────────────────────
uploaded = st.file_uploader(
    "Upload a mapping CSV",
    type=["csv"],
    help="CSV with at least the required mapping columns. Workspace columns (ws_*) in existing rows are preserved.",
)

if not uploaded:
    st.info("Upload a CSV file to begin. Required columns: " + ", ".join(sorted(constants.REQUIRED_MAPPING_COLUMNS)))
    st.stop()

# ── Parse upload ─────────────────────────────────────────────────────────
try:
    upload_df = pd.read_csv(uploaded, dtype=str, keep_default_na=False)
    upload_df.columns = [constants.normalize_column_name(c) for c in upload_df.columns]
except Exception as e:
    st.error(f"Failed to parse CSV: {e}")
    st.stop()

st.caption(f"Uploaded: {len(upload_df):,} rows, {len(upload_df.columns)} columns")

# ── Validate ─────────────────────────────────────────────────────────────
errors, warnings = validate_dataframe(upload_df)

if errors:
    st.error(f"{len(errors)} validation error(s)")
    with st.expander("Errors", expanded=True):
        for e in errors:
            st.markdown(f"- {e}")

if warnings:
    st.warning(f"{len(warnings)} warning(s)")
    with st.expander("Warnings"):
        for w in warnings:
            st.markdown(f"- {w}")

if errors:
    st.error("Fix errors before merging.")
    st.stop()

# ── Merge strategy ───────────────────────────────────────────────────────
st.divider()

merge_strategy = st.radio(
    "Merge strategy",
    ["Add new only", "Update existing + add new"],
    help=(
        "**Add new only**: Only adds rows with source_concept_codes not already in the file. "
        "**Update existing + add new**: Updates existing rows (matched by source_concept_code) and adds new ones."
    ),
)

# ── Compute changes ─────────────────────────────────────────────────────
existing_codes = set(df["source_concept_code"].astype(str).str.strip())
upload_codes = upload_df["source_concept_code"].astype(str).str.strip()

new_mask = ~upload_codes.isin(existing_codes)
existing_mask = upload_codes.isin(existing_codes)

new_rows = upload_df[new_mask]
update_rows = upload_df[existing_mask]

st.markdown(f"**Preview**: {len(new_rows):,} new rows, {len(update_rows):,} existing rows to update")

if merge_strategy == "Add new only":
    if new_rows.empty:
        st.info("No new rows to add — all uploaded codes already exist.")
        st.stop()

    st.dataframe(
        new_rows[[c for c in ["source_concept_code", "source_description", "predicate_id", "target_concept_id"] if c in new_rows.columns]],
        use_container_width=True,
        height=300,
    )
else:
    # Show what will be updated
    if not update_rows.empty:
        st.markdown("**Rows to update:**")
        st.dataframe(
            update_rows[[c for c in ["source_concept_code", "source_description", "predicate_id", "target_concept_id"] if c in update_rows.columns]],
            use_container_width=True,
            height=200,
        )
    if not new_rows.empty:
        st.markdown("**New rows to add:**")
        st.dataframe(
            new_rows[[c for c in ["source_concept_code", "source_description", "predicate_id", "target_concept_id"] if c in new_rows.columns]],
            use_container_width=True,
            height=200,
        )

    if new_rows.empty and update_rows.empty:
        st.info("No changes to make.")
        st.stop()

# ── Save ─────────────────────────────────────────────────────────────────
if st.button("Merge and save", type="primary", use_container_width=True):
    result_df = df.copy()

    # Mapping columns to update (exclude ws_* from upload to preserve workspace data)
    upload_mapping_cols = [c for c in upload_df.columns if not c.startswith("ws_")]

    if merge_strategy == "Update existing + add new" and not update_rows.empty:
        # Build a lookup from source_concept_code → row indices in result_df
        code_to_indices: dict[str, list[int]] = {}
        for idx, code in result_df["source_concept_code"].astype(str).str.strip().items():
            code_to_indices.setdefault(code, []).append(idx)

        for _, urow in update_rows.iterrows():
            code = str(urow["source_concept_code"]).strip()
            for idx in code_to_indices.get(code, []):
                for col in upload_mapping_cols:
                    if col in result_df.columns and col in urow.index:
                        result_df.at[idx, col] = urow[col]

    # Add new rows
    if not new_rows.empty:
        # Align columns: add missing columns from existing df
        new_rows = new_rows.copy()
        for col in result_df.columns:
            if col not in new_rows.columns:
                new_rows[col] = ""

        new_rows_aligned = new_rows[result_df.columns]
        result_df = pd.concat([result_df, new_rows_aligned], ignore_index=True)

    try:
        save_mapping_csv(result_df, selected_file)
        st.session_state[cache_key] = result_df
        added = len(new_rows)
        updated = len(update_rows) if merge_strategy == "Update existing + add new" else 0
        st.success(f"Saved: {added} added, {updated} updated. Total rows: {len(result_df):,}")
        st.rerun()
    except Exception as e:
        st.error(f"Save failed: {e}")
