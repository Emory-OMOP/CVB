# CVB Mapping Contributor

Streamlit app for mapping CVB vocabulary items to OMOP concepts.

## Setup

```bash
cd apps/mapping-contributor
uv pip install -r requirements.txt
```

## Usage

```bash
cd apps/mapping-contributor
uv run streamlit run app.py
```

### Browse & Map

1. Select a vocabulary and mapping file in the sidebar
2. Filter by assignment, predicate, status, or description search
3. Click a row to select it
4. Search for OMOP concepts (requires local Docker DB running)
5. Set predicate, confidence, mapping tool, and save

### Bulk Upload

1. Upload a CSV with at least the required mapping columns
2. Fix any validation errors shown
3. Choose merge strategy (add new only, or update + add)
4. Review the preview and save

### Concept search

Concept search queries the local Postgres vocabulary DB (`docker-compose up db`).
If the DB is offline, concept search is disabled but CSV editing still works — you can
enter target fields manually.

## Environment variables

- `CVB_REPO_ROOT` — override auto-detection of the repo root directory
