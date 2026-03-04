"""
CVB shared constants — OHDSI Vocabulary WG aligned.

Used by excel-to-csv.py, validate-mapping-csv.py, and mapping-coverage.py.
"""

REQUIRED_MAPPING_COLUMNS = {
    "source_concept_code",
    "source_vocabulary_id",
    "source_description",
    "predicate_id",
    "confidence",
    "target_concept_id",
}

EXPECTED_COLUMNS = [
    "source_concept_code",
    "source_concept_id",
    "source_vocabulary_id",
    "source_domain",
    "source_concept_class_id",
    "source_description",
    "source_description_synonym",
    "relationship_id",
    "predicate_id",
    "confidence",
    "target_concept_id",
    "target_concept_name",
    "target_vocabulary_id",
    "target_domain_id",
    "mapping_justification",
    "mapping_tool",
    "author_label",
    "review_date",
    "reviewer_name",
    "reviewer_specialty",
    "status",
]

COLUMN_ALIASES = {
    "source_code": "source_concept_code",
}

# OHDSI-aligned predicates (relationship predicates only)
VALID_RELATIONSHIP_PREDICATES = {
    "exactMatch", "broadMatch", "narrowMatch",  # SSSOM names (emerging standard)
    "eq", "up", "down",                          # OHDSI short codes (current standard)
}

# Pipeline directives (not relationship predicates — excluded from concept_relationship_metadata)
VALID_PIPELINE_DIRECTIVES = {
    "noMatch",  # signals "create new custom concept, no mapping relationship"
}

# Combined: all valid values for predicate_id column in mapping CSVs
VALID_PREDICATES = VALID_RELATIONSHIP_PREDICATES | VALID_PIPELINE_DIRECTIVES

# Normalize skos: prefix and legacy forms
PREDICATE_ALIASES = {
    "skos:exactMatch": "exactMatch",
    "skos:broadMatch": "broadMatch",
    "skos:narrowMatch": "narrowMatch",
    "skos:noMatch": "noMatch",
}

# OHDSI mapping_tool taxonomy
VALID_MAPPING_TOOLS = {
    "MM_C",       # Manual mapping, curated/reviewed
    "MM_U",       # Manual mapping, uncurated
    "AM-lib_C",   # Automapping via library, curated
    "AM-lib_U",   # Automapping via library, uncurated
    "AM-tool_C",  # Automapping via tool, curated
    "AM-tool_U",  # Automapping via tool, uncurated
}


def normalize_column_name(name: str) -> str:
    """Normalize column names: lowercase, strip, replace spaces/hyphens with underscores."""
    normalized = name.strip().lower().replace(" ", "_").replace("-", "_")
    return COLUMN_ALIASES.get(normalized, normalized)
