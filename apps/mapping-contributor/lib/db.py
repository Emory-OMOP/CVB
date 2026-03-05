"""Postgres concept search for OMOP vocabulary lookups."""

from pathlib import Path

import streamlit as st


def _parse_vocab_env(vocab_dir: Path) -> dict:
    """Parse vocab.env for DB_NAME."""
    env_file = vocab_dir / "vocab.env"
    env = {}
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                env[key.strip()] = val.strip().strip('"').strip("'")
    return env


@st.cache_resource
def get_connection(db_name: str):
    """Get a cached Postgres connection. Returns None if unavailable."""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            dbname=db_name,
            user="postgres",
            password="cvb_local",
        )
        conn.autocommit = True
        return conn
    except Exception:
        return None


def check_db_status(vocab_dir: Path) -> tuple[bool, str]:
    """Check if the DB is reachable. Returns (is_connected, db_name)."""
    env = _parse_vocab_env(vocab_dir)
    db_name = env.get("DB_NAME", "cvb_local")
    conn = get_connection(db_name)
    return conn is not None, db_name


def search_concepts(
    vocab_dir: Path,
    term: str,
    limit: int = 50,
    standard_only: bool = True,
) -> list[dict]:
    """Search vocab.concept for matching concepts.

    Returns list of dicts with concept_id, concept_name, vocabulary_id, domain_id, concept_code.
    Returns empty list if DB is unavailable.
    """
    env = _parse_vocab_env(vocab_dir)
    db_name = env.get("DB_NAME", "cvb_local")
    conn = get_connection(db_name)
    if conn is None:
        return []

    try:
        with conn.cursor() as cur:
            query = """
                SELECT concept_id, concept_name, vocabulary_id, domain_id, concept_code
                FROM vocab.concept
                WHERE (concept_name ILIKE %s OR concept_code ILIKE %s)
            """
            params = [f"%{term}%", f"%{term}%"]

            if standard_only:
                query += " AND standard_concept = 'S'"

            query += " ORDER BY concept_name LIMIT %s"
            params.append(limit)

            cur.execute(query, params)
            columns = ["concept_id", "concept_name", "vocabulary_id", "domain_id", "concept_code"]
            return [dict(zip(columns, row)) for row in cur.fetchall()]
    except Exception:
        return []
