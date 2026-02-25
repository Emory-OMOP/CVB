-- CVB: OMOP Vocabulary Schema
-- Creates the vocab schema with all tables needed by the CVB pipeline.
-- Derived from MIMIC/Builder/sql/delta-tables-ddl.sql and existing pipeline SQL.
--
-- NOTE: Base OMOP vocabulary data (Athena) must be loaded separately (licensed).
-- This schema is empty by default.

CREATE SCHEMA IF NOT EXISTS vocab;
CREATE SCHEMA IF NOT EXISTS temp;

-- concept
CREATE TABLE IF NOT EXISTS vocab.concept
(
    concept_id       INTEGER PRIMARY KEY,
    concept_name     VARCHAR(255),
    domain_id        VARCHAR(25),
    vocabulary_id    VARCHAR(20),
    concept_class_id VARCHAR(25),
    standard_concept VARCHAR(1),
    concept_code     VARCHAR(50),
    valid_start_date DATE,
    valid_end_date   DATE,
    invalid_reason   VARCHAR(1)
);

-- concept_relationship
CREATE TABLE IF NOT EXISTS vocab.concept_relationship
(
    concept_id_1     INTEGER,
    concept_id_2     INTEGER,
    relationship_id  VARCHAR(20),
    valid_start_date DATE,
    valid_end_date   DATE,
    invalid_reason   VARCHAR(1),
    PRIMARY KEY (concept_id_1, concept_id_2, relationship_id)
);

-- concept_ancestor
CREATE TABLE IF NOT EXISTS vocab.concept_ancestor
(
    ancestor_concept_id      INTEGER,
    descendant_concept_id    INTEGER,
    min_levels_of_separation INTEGER,
    max_levels_of_separation INTEGER,
    PRIMARY KEY (ancestor_concept_id, descendant_concept_id)
);

-- concept_synonym
CREATE TABLE IF NOT EXISTS vocab.concept_synonym
(
    concept_id           INTEGER,
    concept_synonym_name VARCHAR(1000),
    language_concept_id  INTEGER
);

-- vocabulary
CREATE TABLE IF NOT EXISTS vocab.vocabulary
(
    vocabulary_id         VARCHAR(20) PRIMARY KEY,
    vocabulary_name       VARCHAR(255),
    vocabulary_reference  VARCHAR(255),
    vocabulary_version    VARCHAR(255),
    vocabulary_concept_id INTEGER,
    latest_update         DATE,
    dev_schema_name       TEXT,
    vocabulary_params     JSONB
);

-- concept_class
CREATE TABLE IF NOT EXISTS vocab.concept_class
(
    concept_class_id         VARCHAR(25) PRIMARY KEY,
    concept_class_name       VARCHAR(255),
    concept_class_concept_id INTEGER
);

-- domain
CREATE TABLE IF NOT EXISTS vocab.domain
(
    domain_id         VARCHAR(25) PRIMARY KEY,
    domain_name       VARCHAR(255),
    domain_concept_id INTEGER
);

-- relationship
CREATE TABLE IF NOT EXISTS vocab.relationship
(
    relationship_id         VARCHAR(20) PRIMARY KEY,
    relationship_name       VARCHAR(255),
    is_hierarchical         INTEGER,
    defines_vocabulary      SMALLINT,
    reverse_relationship_id VARCHAR(20),
    relationship_concept_id INTEGER
);

-- source_to_concept_map
CREATE TABLE IF NOT EXISTS vocab.source_to_concept_map
(
    source_code             VARCHAR(50)  NOT NULL,
    source_concept_id       INTEGER,
    source_vocabulary_id    VARCHAR(20)  NOT NULL,
    source_code_description VARCHAR(255),
    target_concept_id       INTEGER      NOT NULL,
    target_vocabulary_id    VARCHAR(20)  NOT NULL,
    valid_start_date        DATE         NOT NULL,
    valid_end_date          DATE         NOT NULL,
    invalid_reason          VARCHAR(1)
);

-- mapping_metadata
CREATE TABLE IF NOT EXISTS vocab.mapping_metadata
(
    mapping_concept_id    INTEGER,
    mapping_concept_code  VARCHAR(255),
    confidence            FLOAT,
    predicate_id          VARCHAR(255),
    mapping_justification VARCHAR(255),
    mapping_provider      VARCHAR(255),
    author_id             INTEGER,
    author_label          VARCHAR(255),
    reviewer_id           INTEGER,
    reviewer_label        VARCHAR(255),
    mapping_tool          VARCHAR(255),
    mapping_tool_version  VARCHAR(255)
);

-- mapping_exceptions
CREATE TABLE IF NOT EXISTS vocab.mapping_exceptions
(
    concept_id INTEGER
);

-- review_ids
CREATE TABLE IF NOT EXISTS vocab.review_ids
(
    name TEXT,
    id   INTEGER
);
