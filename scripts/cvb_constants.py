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

# Registered extension columns (sheet columns 22+).
#
# Columns 1-21 are the canonical CVB pipeline columns; anything beyond is an
# extension that rides in the sheet and is trimmed before the Builder load.
# Registering a column here means the validator knows how to check it and the
# release step knows whether to publish it. An unregistered extra column warns
# in CI — it is silently dropped downstream, so drift stays visible.
KNOWN_EXTENSION_COLUMNS = {
    "valid_start_date",
    "valid_end_date",
    "source_frequency",
    "ws_frequency",  # EU2_Flowsheets file drift; registered so its CI stays green
}

# The release artifact consumed by omop_etl.src_mapping_sssom: the canonical 21
# plus the two date extensions, in this order. Workspace columns (frequency)
# inform curation only and do not cross into the warehouse contract.
RELEASE_COLUMNS = EXPECTED_COLUMNS + ["valid_start_date", "valid_end_date"]

# Extension columns validated as ISO dates. Ordered pairs are range-checked
# (start <= end) when both are present.
DATE_EXTENSION_COLUMNS = ["valid_start_date", "valid_end_date"]
DATE_RANGE_PAIRS = [("valid_start_date", "valid_end_date")]

# Extension columns validated as numeric.
NUMERIC_EXTENSION_COLUMNS = ["source_frequency", "ws_frequency"]

# Row identity for the duplicate check (ADR D9 layer 1). Multi-mapping to
# distinct targets is legitimate, and *_VAL vocabularies legitimately repeat a
# source code across description-keyed value rows (audit finding 11) — the
# description is a join key there, not a label. Only a fully identical tuple is
# a duplicate.
ROW_IDENTITY_COLUMNS = [
    "source_vocabulary_id",
    "source_concept_code",
    "source_description",
    "target_concept_id",
]

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
