"""Mapping Contributor — Streamlit app for CVB mapping workflows."""

import streamlit as st

from lib.vocab_discovery import find_repo_root, discover_vocabs, discover_mapping_files
from lib.csv_io import load_mapping_csv
from lib.db import check_db_status
from lib.constants import ASSIGNMENT_LABELS


def main():
    st.set_page_config(
        page_title="CVB Mapping Contributor",
        page_icon=":material/edit_note:",
        layout="wide",
    )

    # --- Discover vocabs ---
    try:
        repo_root = find_repo_root()
    except FileNotFoundError as e:
        st.error(str(e))
        st.stop()

    vocabs = discover_vocabs(repo_root)
    if not vocabs:
        st.error("No vocabularies with Mappings/ directories found.")
        st.stop()

    # --- Sidebar ---
    with st.sidebar:
        st.title("CVB Mapping Contributor")

        # Vocab selector
        vocab_names = [v["name"] for v in vocabs]
        selected_vocab_name = st.selectbox("Vocabulary", vocab_names)
        selected_vocab = next(v for v in vocabs if v["name"] == selected_vocab_name)

        # File selector
        mapping_files = discover_mapping_files(selected_vocab["mappings_dir"])
        if not mapping_files:
            st.warning("No CSV files in this vocabulary's Mappings/ directory.")
            st.stop()

        file_names = [f.name for f in mapping_files]
        selected_file_name = st.selectbox("Mapping file", file_names)
        selected_file = next(f for f in mapping_files if f.name == selected_file_name)

        # Assignment filter
        st.divider()
        assignment = st.radio(
            "Assignment filter",
            list(ASSIGNMENT_LABELS.keys()),
            horizontal=True,
        )

        # DB status
        st.divider()
        db_ok, db_name = check_db_status(selected_vocab["path"])
        if db_ok:
            st.success(f"DB: {db_name}", icon=":material/database:")
        else:
            st.info("DB offline — concept search disabled", icon=":material/cloud_off:")

    # --- Load CSV into session state ---
    cache_key = f"df_{selected_file}"
    if cache_key not in st.session_state or st.session_state.get("_loaded_file") != str(selected_file):
        st.session_state[cache_key] = load_mapping_csv(selected_file)
        st.session_state["_loaded_file"] = str(selected_file)

    # Store references for pages
    st.session_state["repo_root"] = repo_root
    st.session_state["selected_vocab"] = selected_vocab
    st.session_state["selected_file"] = selected_file
    st.session_state["cache_key"] = cache_key
    st.session_state["assignment_filter"] = ASSIGNMENT_LABELS[assignment]
    st.session_state["db_available"] = db_ok

    # --- Page navigation ---
    browse_page = st.Page("pages/browse_and_map.py", title="Browse & Map", icon=":material/search:", default=True)
    upload_page = st.Page("pages/bulk_upload.py", title="Bulk Upload", icon=":material/upload_file:")

    nav = st.navigation([browse_page, upload_page])
    nav.run()


if __name__ == "__main__":
    main()
