-- ==========================================================================
-- CVB Pipeline Unit Test: Multi-row compositional mappings
--
-- Tests the pipeline with 3 real EU2_Flowsheets items:
--   1. Breath Sounds Left (1120100008) — COMPOSITIONAL: 2 explicit relationships
--      Maps to → 4278456 (Breath sounds - finding)
--      Has finding site → 4300877 (Left)
--   2. Pulse (8) — ATOMIC: legacy exactMatch, 1 target
--      exactMatch → 3027018 (Heart rate)
--   3. MEWS Difference from Baseline (14950) — noMatch
--
-- Run with:
--   psql -d test_cvb -f Builder/sql/tests/test_multirow_pipeline.sql
--
-- Expects a fresh database. Creates and tears down its own schemas.
-- ==========================================================================

\set ON_ERROR_STOP on
\set QUIET on

-- ==========================================================================
-- SETUP: Schema + seed data
-- ==========================================================================

DROP SCHEMA IF EXISTS vocab CASCADE;
DROP SCHEMA IF EXISTS temp CASCADE;
CREATE SCHEMA vocab;
CREATE SCHEMA temp;

-- Core OMOP tables (minimal from 01-create-vocab-schema.sql)
CREATE TABLE vocab.concept (
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

CREATE TABLE vocab.concept_relationship (
    concept_id_1     INTEGER,
    concept_id_2     INTEGER,
    relationship_id  VARCHAR(20),
    valid_start_date DATE,
    valid_end_date   DATE,
    invalid_reason   VARCHAR(1),
    PRIMARY KEY (concept_id_1, concept_id_2, relationship_id)
);

CREATE TABLE vocab.concept_ancestor (
    ancestor_concept_id      INTEGER,
    descendant_concept_id    INTEGER,
    min_levels_of_separation INTEGER,
    max_levels_of_separation INTEGER,
    PRIMARY KEY (ancestor_concept_id, descendant_concept_id)
);

CREATE TABLE vocab.concept_synonym (
    concept_id           INTEGER,
    concept_synonym_name VARCHAR(1000),
    language_concept_id  INTEGER
);

CREATE TABLE vocab.vocabulary (
    vocabulary_id         VARCHAR(20) PRIMARY KEY,
    vocabulary_name       VARCHAR(255),
    vocabulary_reference  VARCHAR(255),
    vocabulary_version    VARCHAR(255),
    vocabulary_concept_id INTEGER,
    latest_update         DATE,
    dev_schema_name       TEXT,
    vocabulary_params     JSONB
);

CREATE TABLE vocab.concept_class (
    concept_class_id         VARCHAR(25) PRIMARY KEY,
    concept_class_name       VARCHAR(255),
    concept_class_concept_id INTEGER
);

CREATE TABLE vocab.domain (
    domain_id         VARCHAR(25) PRIMARY KEY,
    domain_name       VARCHAR(255),
    domain_concept_id INTEGER
);

CREATE TABLE vocab.relationship (
    relationship_id         VARCHAR(20) PRIMARY KEY,
    relationship_name       VARCHAR(255),
    is_hierarchical         INTEGER,
    defines_vocabulary      SMALLINT,
    reverse_relationship_id VARCHAR(20),
    relationship_concept_id INTEGER
);

CREATE TABLE vocab.source_to_concept_map (
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

CREATE TABLE vocab.mapping_metadata (
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

CREATE TABLE vocab.concept_relationship_metadata (
    concept_id_1                INTEGER      NOT NULL,
    concept_id_2                INTEGER      NOT NULL,
    relationship_id             VARCHAR(20)  NOT NULL,
    relationship_predicate_id   VARCHAR(20),
    relationship_group          INTEGER,
    mapping_source              VARCHAR(50),
    confidence                  FLOAT,
    mapping_tool                VARCHAR(50),
    mapper                      VARCHAR(50),
    reviewer                    VARCHAR(50),
    UNIQUE (concept_id_1, concept_id_2, relationship_id)
);

CREATE TABLE vocab.mapping_exceptions (concept_id INTEGER);
CREATE TABLE vocab.review_ids (name TEXT, id INTEGER);

-- Seed: standard OMOP concepts that our test items map TO
INSERT INTO vocab.concept VALUES
    (3027018,  'Heart rate',                  'Measurement', 'LOINC',   'Clinical Observation', 'S', '8867-4',   '2020-01-01', '2099-12-31', NULL),
    (4278456,  'Breath sounds - finding',     'Observation', 'SNOMED',  'Clinical Finding',     'S', '48348007', '2020-01-01', '2099-12-31', NULL),
    (4300877,  'Left',                        'Observation', 'SNOMED',  'Qualifier Value',      'S', '7771000',  '2020-01-01', '2099-12-31', NULL);

-- Seed: concept_ancestor for breath sounds (needed for ancestor building)
INSERT INTO vocab.concept_ancestor VALUES
    (4278456, 4278456, 0, 0);

-- Seed: vocabulary entry
INSERT INTO vocab.vocabulary VALUES
    ('EU2_Flowsheets', 'EU2 Flowsheets Custom Terminology', 'OMOP generated', '2026-03-04', 2001499999, NULL, NULL, NULL);


-- ==========================================================================
-- PIPELINE STEP 1-2: Create staging + load test mapping data
-- ==========================================================================

-- source-ddl.sql equivalent
CREATE TABLE temp.mapping (
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
    mapping_tool               TEXT,
    author_label               TEXT,
    review_date                TEXT,
    reviewer_name              TEXT,
    reviewer_specialty         TEXT,
    status                     TEXT
);

CREATE TABLE temp.source_to_update (
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
    change_required            TEXT,
    author_label               TEXT
);

CREATE TABLE temp.vocab_logger (
    log_desc  TEXT NULL,
    log_count TEXT NULL
);

-- Load test data: 4 rows representing 3 items
--
-- Item 1: Pulse (atomic, legacy exactMatch, no explicit relationship_id)
INSERT INTO temp.mapping VALUES
    ('8', 0, 'EU2_Flowsheets', 'Measurement', 'Suppl Concept',
     'Pulse', 'PULSE', NULL, 'exactMatch', 0.9,
     '3027018', 'Heart rate', 'LOINC', 'Measurement',
     'Pulse maps to Heart rate', 'AM-tool_U', 'Joan', NULL, NULL, NULL, 'pending');

-- Item 2: Breath Sounds Left (compositional, 2 rows with explicit relationship_id)
INSERT INTO temp.mapping VALUES
    ('1120100008', 0, 'EU2_Flowsheets', 'Observation', 'Suppl Concept',
     'Breath Sounds Left', NULL, 'Maps to', 'broadMatch', 0.8,
     '4278456', 'Breath sounds - finding', 'SNOMED', 'Observation',
     'FCA compositional: assessment', NULL, 'FCA-pipeline', NULL, NULL, NULL, 'pending');

INSERT INTO temp.mapping VALUES
    ('1120100008', 0, 'EU2_Flowsheets', 'Observation', 'Suppl Concept',
     'Breath Sounds Left', NULL, 'Has finding site', 'broadMatch', 0.8,
     '4300877', 'Left', 'SNOMED', 'Observation',
     'FCA compositional: qualifier', NULL, 'FCA-pipeline', NULL, NULL, NULL, 'pending');

-- Item 3: MEWS Difference from Baseline (noMatch)
INSERT INTO temp.mapping VALUES
    ('14950', 0, 'EU2_Flowsheets', 'Measurement', 'Suppl Concept',
     'MEWS Difference from Baseline', 'R EHC BH MEWS BASELINE DIFFERENCE',
     NULL, 'noMatch', 0, '0', NULL, NULL, NULL,
     NULL, NULL, 'Joan', NULL, NULL, NULL, 'pending');


-- ==========================================================================
-- PIPELINE STEP 3: load-source.sql equivalent — transform to source_to_update
-- ==========================================================================

INSERT INTO temp.source_to_update (
    source_concept_code, source_concept_id, source_vocabulary_id,
    source_domain_id, source_concept_class_id, source_description,
    source_description_synonym, valid_start, relationship_id,
    predicate_id, confidence, target_concept_id, target_concept_code,
    target_concept_name, target_vocabulary_id, target_domain_id,
    decision, review_date, reviewer_name, reviewer_specialty,
    reviewer_comment, orcid_id, reviewer_affiliation_name,
    status, author_comment, change_required, author_label
)
SELECT TRIM(LEFT(source_concept_code, 50)),
       NULL,
       source_vocabulary_id,
       COALESCE(target_domain_id, 'Metadata'),
       COALESCE(source_concept_class_id, 'Suppl Concept'),
       LEFT(source_description, 255),
       LEFT(source_description_synonym, 255),
       CURRENT_DATE,
       relationship_id,
       predicate_id,
       confidence::FLOAT,
       target_concept_id::integer,
       NULL,
       target_concept_name,
       target_vocabulary_id,
       INITCAP(target_domain_id),
       NULL::int,
       review_date::date,
       reviewer_name,
       reviewer_specialty,
       NULL, NULL, NULL,
       status, NULL, NULL,
       author_label
FROM temp.mapping
WHERE NULLIF(TRIM(LEFT(source_concept_code, 50)), '') IS NOT NULL
  AND NULLIF(TRIM(LEFT(source_description, 50)), '') IS NOT NULL;


-- ==========================================================================
-- ASSERT: source_to_update has 4 rows (3 items, item 2 has 2 rows)
-- ==========================================================================
DO $$
DECLARE
    cnt INTEGER;
BEGIN
    SELECT count(*) INTO cnt FROM temp.source_to_update;
    ASSERT cnt = 4, format('FAIL: source_to_update should have 4 rows, got %s', cnt);
    RAISE NOTICE 'PASS: source_to_update has 4 rows';
END $$;


-- ==========================================================================
-- PIPELINE STEP 4: revert-id-sequence.sql
-- ==========================================================================
\set id_range_min 2001000000
\set id_range_max 2001500000
\set id_range_start 2001499885

DROP SEQUENCE IF EXISTS vocab.master_id_assignment;
CREATE SEQUENCE vocab.master_id_assignment
    INCREMENT -1
    MINVALUE :id_range_min
    MAXVALUE :id_range_max
    START :id_range_start
    OWNED BY vocab.concept.concept_id;

SELECT setval('vocab.master_id_assignment',
              (SELECT COALESCE(min(concept_id), :id_range_start + 1)
               FROM vocab.concept
               WHERE concept_id > :id_range_min AND concept_id < :id_range_max
                 AND standard_concept = 'S'));


-- ==========================================================================
-- PIPELINE STEP 5: evaluate-difference.sql
-- ==========================================================================
\set ns_range_min 2001500000
\set ns_range_max 2002000000

\i /workspace/Builder/sql/shared/evaluate-difference.sql


-- ==========================================================================
-- ASSERT: CONCEPT_CHECK_S should have 1 item (noMatch: MEWS)
-- Pulse has exactMatch → goes to NS path. Breath Sounds Left has
-- explicit relationship_id → excluded from S path.
-- ==========================================================================
DO $$
DECLARE
    cnt INTEGER;
    codes TEXT[];
BEGIN
    SELECT count(*) INTO cnt FROM temp.concept_check_s;
    ASSERT cnt = 1, format('FAIL: concept_check_s should have 1 row (noMatch only), got %s', cnt);

    SELECT array_agg(DISTINCT source_concept_code) INTO codes FROM temp.concept_check_s;
    ASSERT codes = ARRAY['14950'], format('FAIL: concept_check_s should contain 14950, got %s', codes);
    RAISE NOTICE 'PASS: concept_check_s has 1 noMatch item (14950)';
END $$;


-- ==========================================================================
-- ASSERT: CONCEPT_CHECK_NS has rows for all 3 items (4 total):
--   Pulse (1 row), Breath Sounds Left (2 rows), MEWS (1 row with target=0)
--   MEWS will survive here but won't create an NS concept (INNER JOIN filters it)
-- ==========================================================================
DO $$
DECLARE
    cnt INTEGER;
    bsl_cnt INTEGER;
BEGIN
    SELECT count(*) INTO cnt FROM temp.concept_check_ns;
    ASSERT cnt = 4, format('FAIL: concept_check_ns should have 4 rows, got %s', cnt);

    SELECT count(*) INTO bsl_cnt FROM temp.concept_check_ns
    WHERE source_concept_code = '1120100008';
    ASSERT bsl_cnt = 2, format('FAIL: concept_check_ns should have 2 rows for Breath Sounds Left, got %s', bsl_cnt);

    RAISE NOTICE 'PASS: concept_check_ns has 4 rows (Pulse=1, BSL=2, MEWS=1)';
END $$;


-- ==========================================================================
-- PIPELINE STEP 6: update-standard.sql
-- ==========================================================================
\i /workspace/Builder/sql/shared/update-standard.sql


-- ==========================================================================
-- ASSERT: concept_s_staging should have 1 Standard concept (MEWS noMatch)
-- ==========================================================================
DO $$
DECLARE
    cnt INTEGER;
    mews_code TEXT;
BEGIN
    SELECT count(*) INTO cnt FROM vocab.concept_s_staging;
    ASSERT cnt = 1, format('FAIL: concept_s_staging should have 1 row, got %s', cnt);

    SELECT concept_code INTO mews_code FROM vocab.concept_s_staging LIMIT 1;
    ASSERT mews_code = '14950', format('FAIL: S concept should be 14950, got %s', mews_code);

    RAISE NOTICE 'PASS: concept_s_staging has 1 Standard concept (14950 MEWS)';
END $$;


-- ==========================================================================
-- PIPELINE STEP 7: update-nonstandard.sql
-- ==========================================================================
\i /workspace/Builder/sql/shared/update-nonstandard.sql


-- ==========================================================================
-- ASSERT: concept_ns_staging should have 2 NS concepts
--   (Pulse + Breath Sounds Left — NOT one per row, one per source_concept_code)
-- ==========================================================================
DO $$
DECLARE
    cnt INTEGER;
    codes TEXT[];
BEGIN
    SELECT count(*) INTO cnt FROM vocab.concept_ns_staging;
    ASSERT cnt = 2, format('FAIL: concept_ns_staging should have 2 rows (one per source item), got %s', cnt);

    SELECT array_agg(concept_code ORDER BY concept_code) INTO codes FROM vocab.concept_ns_staging;
    ASSERT codes = ARRAY['1120100008', '8'],
        format('FAIL: NS concepts should be [1120100008, 8], got %s', codes);

    RAISE NOTICE 'PASS: concept_ns_staging has 2 NS concepts (Pulse + BSL)';
END $$;


-- ==========================================================================
-- ASSERT: concept_rel_ns_staging has correct relationships
--
-- Pulse (exactMatch, no explicit rel_id):
--   NS_pulse → 3027018 'Maps to'
--   3027018 → NS_pulse 'Mapped from'
--
-- Breath Sounds Left (explicit relationship_id):
--   NS_bsl → 4278456 'Maps to'
--   4278456 → NS_bsl 'Mapped from'
--   NS_bsl → 4300877 'Has finding site'
--   4300877 → NS_bsl 'Finding site of'
--
-- Plus NS→S maps (if S concept exists for same code — not in this case)
-- ==========================================================================
DO $$
DECLARE
    total_rels INTEGER;
    bsl_id INTEGER;
    pulse_id INTEGER;
    bsl_maps_to INTEGER;
    bsl_finding_site INTEGER;
    pulse_maps_to INTEGER;
BEGIN
    SELECT concept_id INTO bsl_id FROM vocab.concept_ns_staging WHERE concept_code = '1120100008';
    SELECT concept_id INTO pulse_id FROM vocab.concept_ns_staging WHERE concept_code = '8';

    -- Breath Sounds Left: Maps to → Breath sounds - finding
    SELECT count(*) INTO bsl_maps_to FROM vocab.concept_rel_ns_staging
    WHERE concept_id_1 = bsl_id AND concept_id_2 = 4278456 AND relationship_id = 'Maps to';
    ASSERT bsl_maps_to = 1,
        format('FAIL: BSL should have 1 "Maps to" → 4278456, got %s', bsl_maps_to);

    -- Breath Sounds Left: Has finding site → Left
    SELECT count(*) INTO bsl_finding_site FROM vocab.concept_rel_ns_staging
    WHERE concept_id_1 = bsl_id AND concept_id_2 = 4300877 AND relationship_id = 'Has finding site';
    ASSERT bsl_finding_site = 1,
        format('FAIL: BSL should have 1 "Has finding site" → 4300877, got %s', bsl_finding_site);

    -- Pulse: Maps to → Heart rate
    SELECT count(*) INTO pulse_maps_to FROM vocab.concept_rel_ns_staging
    WHERE concept_id_1 = pulse_id AND concept_id_2 = 3027018 AND relationship_id = 'Maps to';
    ASSERT pulse_maps_to = 1,
        format('FAIL: Pulse should have 1 "Maps to" → 3027018, got %s', pulse_maps_to);

    -- Check reverse relationships exist
    ASSERT (SELECT count(*) FROM vocab.concept_rel_ns_staging
            WHERE concept_id_1 = 4278456 AND concept_id_2 = bsl_id AND relationship_id = 'Mapped from') = 1,
        'FAIL: Missing reverse "Mapped from" for BSL Maps to';

    ASSERT (SELECT count(*) FROM vocab.concept_rel_ns_staging
            WHERE concept_id_1 = 4300877 AND concept_id_2 = bsl_id AND relationship_id = 'Finding site of') = 1,
        'FAIL: Missing reverse "Finding site of" for BSL Has finding site';

    ASSERT (SELECT count(*) FROM vocab.concept_rel_ns_staging
            WHERE concept_id_1 = 3027018 AND concept_id_2 = pulse_id AND relationship_id = 'Mapped from') = 1,
        'FAIL: Missing reverse "Mapped from" for Pulse Maps to';

    RAISE NOTICE 'PASS: All relationships correct for BSL (Maps to + Has finding site) and Pulse (Maps to)';
    RAISE NOTICE '  BSL concept_id=%  Pulse concept_id=%', bsl_id, pulse_id;
END $$;


-- ==========================================================================
-- PIPELINE STEP 8: update-synonym.sql
-- ==========================================================================
\i /workspace/Builder/sql/shared/update-synonym.sql


-- ==========================================================================
-- PIPELINE STEP 9: deprecate-and-update.sql (no existing mappings to diff)
-- ==========================================================================
\i /workspace/Builder/sql/shared/deprecate-and-update.sql


-- ==========================================================================
-- PIPELINE STEP 10: pre-update.sql
-- ==========================================================================
\i /workspace/Builder/sql/shared/pre-update.sql


-- ==========================================================================
-- ASSERT: After pre-update dedup, BSL still has both relationships
-- ==========================================================================
DO $$
DECLARE
    bsl_id INTEGER;
    bsl_rel_cnt INTEGER;
BEGIN
    SELECT concept_id INTO bsl_id FROM vocab.concept_ns_staging WHERE concept_code = '1120100008';

    SELECT count(*) INTO bsl_rel_cnt FROM vocab.concept_rel_ns_staging
    WHERE concept_id_1 = bsl_id;
    ASSERT bsl_rel_cnt >= 2,
        format('FAIL: BSL should have >= 2 forward rels after dedup, got %s', bsl_rel_cnt);

    RAISE NOTICE 'PASS: pre-update dedup preserved BSL multi-target relationships (% forward rels)', bsl_rel_cnt;
END $$;


-- ==========================================================================
-- PIPELINE STEP 11: execute-core-update.sql
-- ==========================================================================
\set vocab_id 'EU2_Flowsheets'
\set vocab_concept_id 2001499999

\i /workspace/Builder/sql/shared/execute-core-update.sql


-- ==========================================================================
-- FINAL ASSERTIONS: Check the actual vocab tables
-- ==========================================================================

-- Assert: 3 new concepts in vocab.concept (1 S + 2 NS)
DO $$
DECLARE
    cnt INTEGER;
BEGIN
    SELECT count(*) INTO cnt FROM vocab.concept WHERE concept_id > 2000000000;
    ASSERT cnt = 3, format('FAIL: Should have 3 custom concepts (1S + 2NS), got %s', cnt);
    RAISE NOTICE 'PASS: 3 custom concepts created in vocab.concept';
END $$;

-- Assert: Breath Sounds Left has BOTH relationship types in vocab.concept_relationship
DO $$
DECLARE
    bsl_id INTEGER;
    maps_to_cnt INTEGER;
    finding_site_cnt INTEGER;
BEGIN
    SELECT concept_id INTO bsl_id FROM vocab.concept
    WHERE concept_id > 2000000000 AND concept_code = '1120100008' AND standard_concept IS NULL;

    ASSERT bsl_id IS NOT NULL, 'FAIL: BSL NS concept not found in vocab.concept';

    SELECT count(*) INTO maps_to_cnt FROM vocab.concept_relationship
    WHERE concept_id_1 = bsl_id AND concept_id_2 = 4278456 AND relationship_id = 'Maps to'
      AND invalid_reason IS NULL;
    ASSERT maps_to_cnt = 1,
        format('FAIL: BSL should have "Maps to" → 4278456 in concept_relationship, got %s', maps_to_cnt);

    SELECT count(*) INTO finding_site_cnt FROM vocab.concept_relationship
    WHERE concept_id_1 = bsl_id AND concept_id_2 = 4300877 AND relationship_id = 'Has finding site'
      AND invalid_reason IS NULL;
    ASSERT finding_site_cnt = 1,
        format('FAIL: BSL should have "Has finding site" → 4300877 in concept_relationship, got %s', finding_site_cnt);

    RAISE NOTICE 'PASS: BSL (%) has both "Maps to" and "Has finding site" in vocab.concept_relationship', bsl_id;
END $$;

-- Assert: Pulse has a standard Maps to in concept_relationship
DO $$
DECLARE
    pulse_id INTEGER;
    maps_to_cnt INTEGER;
BEGIN
    SELECT concept_id INTO pulse_id FROM vocab.concept
    WHERE concept_id > 2000000000 AND concept_code = '8' AND standard_concept IS NULL;

    ASSERT pulse_id IS NOT NULL, 'FAIL: Pulse NS concept not found in vocab.concept';

    SELECT count(*) INTO maps_to_cnt FROM vocab.concept_relationship
    WHERE concept_id_1 = pulse_id AND concept_id_2 = 3027018 AND relationship_id = 'Maps to'
      AND invalid_reason IS NULL;
    ASSERT maps_to_cnt = 1,
        format('FAIL: Pulse should have "Maps to" → 3027018, got %s', maps_to_cnt);

    RAISE NOTICE 'PASS: Pulse (%) has "Maps to" → 3027018', pulse_id;
END $$;

-- Assert: MEWS has a Standard concept (maps to itself)
DO $$
DECLARE
    mews_id INTEGER;
    self_map INTEGER;
BEGIN
    SELECT concept_id INTO mews_id FROM vocab.concept
    WHERE concept_id > 2000000000 AND concept_code = '14950' AND standard_concept = 'S';

    ASSERT mews_id IS NOT NULL, 'FAIL: MEWS S concept not found in vocab.concept';

    SELECT count(*) INTO self_map FROM vocab.concept_relationship
    WHERE concept_id_1 = mews_id AND concept_id_2 = mews_id AND relationship_id = 'Maps to';
    ASSERT self_map = 1,
        format('FAIL: MEWS should have self-referencing "Maps to", got %s', self_map);

    RAISE NOTICE 'PASS: MEWS (%) has Standard concept with self-referencing Maps to', mews_id;
END $$;

-- Assert: concept_relationship_metadata has entries for BSL's both relationships
DO $$
DECLARE
    bsl_id INTEGER;
    meta_cnt INTEGER;
BEGIN
    SELECT concept_id INTO bsl_id FROM vocab.concept
    WHERE concept_id > 2000000000 AND concept_code = '1120100008' AND standard_concept IS NULL;

    SELECT count(*) INTO meta_cnt FROM vocab.concept_relationship_metadata
    WHERE concept_id_1 = bsl_id;
    ASSERT meta_cnt >= 2,
        format('FAIL: BSL should have >= 2 metadata entries, got %s', meta_cnt);

    RAISE NOTICE 'PASS: BSL has % concept_relationship_metadata entries', meta_cnt;
END $$;

-- Print summary
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '====================================';
    RAISE NOTICE 'ALL ASSERTIONS PASSED';
    RAISE NOTICE '====================================';
    RAISE NOTICE '';
END $$;

-- Show final state for manual inspection
\echo '\n--- Custom concepts created ---'
SELECT concept_id, concept_name, standard_concept, concept_code
FROM vocab.concept WHERE concept_id > 2000000000 ORDER BY concept_id;

\echo '\n--- Custom concept relationships ---'
SELECT cr.concept_id_1, c1.concept_name as source_name,
       cr.relationship_id,
       cr.concept_id_2, c2.concept_name as target_name,
       cr.invalid_reason
FROM vocab.concept_relationship cr
JOIN vocab.concept c1 ON cr.concept_id_1 = c1.concept_id
JOIN vocab.concept c2 ON cr.concept_id_2 = c2.concept_id
WHERE cr.concept_id_1 > 2000000000 OR cr.concept_id_2 > 2000000000
ORDER BY cr.concept_id_1, cr.relationship_id;

\echo '\n--- Source to concept map ---'
SELECT * FROM vocab.source_to_concept_map ORDER BY source_concept_id;

\echo '\n--- Concept relationship metadata ---'
SELECT * FROM vocab.concept_relationship_metadata ORDER BY concept_id_1;


-- ==========================================================================
-- TEARDOWN
-- ==========================================================================
DROP SCHEMA temp CASCADE;
DROP SCHEMA vocab CASCADE;
