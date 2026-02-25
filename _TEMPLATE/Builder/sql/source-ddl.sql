-- EDIT THIS FILE: Define staging tables for your vocabulary's mapping CSVs.
--
-- This file creates the temp schema tables that hold raw mapping data
-- before it is transformed by load-source.sql.
--
-- The table name(s) here must match STAGING_TABLES in vocab.env.
-- The columns must match your mapping CSV headers.

CREATE SCHEMA IF NOT EXISTS temp;
DROP TABLE IF EXISTS temp.source_to_update;
DROP TABLE IF EXISTS temp.vocab_logger;
DROP TABLE IF EXISTS temp.mapping;

-- Raw mapping table — columns match mapping.csv
CREATE TABLE temp.mapping
(
    source_concept_code        TEXT,
    source_concept_id          INTEGER,
    source_vocabulary_id       TEXT,
    source_domain              TEXT,
    source_concept_class_id    TEXT,
    source_description         TEXT,
    source_description_synonym TEXT,
    relationship_id            TEXT,
    predicate_id               TEXT,
    confidence                 FLOAT,
    target_concept_id          TEXT,
    target_concept_name        TEXT,
    target_vocabulary_id       TEXT,
    target_domain_id           TEXT,
    mapping_justification      TEXT,
    author_label               TEXT,
    review_date                TEXT,
    reviewer_name              TEXT,
    reviewer_specialty         TEXT,
    status                     TEXT
);

-- Normalized staging table used by the shared pipeline SQL
CREATE TABLE temp.source_to_update
(
    source_concept_code        TEXT,
    source_concept_id          INTEGER,
    source_vocabulary_id       TEXT,
    source_domain_id           TEXT,
    source_concept_class_id    TEXT,
    source_description         TEXT,
    source_description_synonym TEXT,
    valid_start                DATE,
    relationship_id            TEXT,
    predicate_id               TEXT,
    confidence                 FLOAT8,
    target_concept_id          INTEGER,
    target_concept_code        TEXT,
    target_concept_name        TEXT,
    target_vocabulary_id       TEXT,
    target_domain_id           TEXT,
    decision                   INTEGER,
    review_date                DATE,
    reviewer_name              TEXT,
    reviewer_specialty         TEXT,
    reviewer_comment           TEXT,
    orcid_id                   TEXT,
    reviewer_affiliation_name  TEXT,
    status                     TEXT,
    author_comment             TEXT,
    change_required            TEXT
);

CREATE TABLE temp.vocab_logger
(
    log_desc  TEXT NULL,
    log_count TEXT NULL
);

CREATE TABLE IF NOT EXISTS vocab.mapping_exceptions
(
    concept_id INTEGER
);

CREATE TABLE IF NOT EXISTS vocab.review_ids
(
    name TEXT,
    id   INTEGER
);
