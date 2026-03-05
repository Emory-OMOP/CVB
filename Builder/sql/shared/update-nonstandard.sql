-- Parameterized: pass via psql -v ns_range_min=... -v ns_range_max=...
-- ns_range_min = lower bound of non-standard ID range
-- ns_range_max = upper bound of non-standard ID range (= standard range min)

/*
---------  ----------  ----------  ----------  ----------
CREATE CONCEPT STAGING TABLE FOR NEW NON-STANDARD CONCEPTS (GENERAL MAPPINGS)
---------  ----------  ----------  ----------  ----------
 */

DROP TABLE IF EXISTS vocab.concept_ns_staging;

CREATE TABLE vocab.concept_ns_staging AS (SELECT *
                                          FROM vocab.concept
                                          where concept_id > 2000000000
                                            and standard_concept = 'S'
                                          LIMIT 0);

ALTER TABLE vocab.concept_ns_staging
    ADD COLUMN target_concept_id INTEGER NULL;

ALTER TABLE vocab.concept_ns_staging
    ADD COLUMN synonym text NULL;

ALTER TABLE vocab.concept_ns_staging
    ADD COLUMN predicate_id text NULL;

-- Create ONE non-standard concept per unique source_concept_code.
-- For multi-row items (same source, multiple targets), we pick a
-- representative row for metadata (domain, class) using the first
-- target_concept_id, but all relationship rows are preserved separately.
-- The DISTINCT ON ensures one concept per source code.
INSERT INTO vocab.concept_ns_staging (concept_id,
                                      concept_name,
                                      domain_id,
                                      vocabulary_id,
                                      concept_class_id,
                                      standard_concept,
                                      concept_code,
                                      valid_start_date,
                                      valid_end_date,
                                      invalid_reason,
                                      target_concept_id,
                                      synonym,
                                      predicate_id)
SELECT row_number() OVER (ORDER BY source_concept_code) + (SELECT COALESCE(max(concept_id),:ns_range_min) FROM vocab.concept WHERE concept_id < :ns_range_max AND concept_id > :ns_range_min) AS concept_id,
       LEFT(cc.source_description, 255),
       cd.domain_id,
       cc.source_vocabulary_id,
       cd.concept_class_id,
       NULL,
       UPPER(cc.source_concept_code),
       valid_start,
       '2099-12-31'::date,
       NULL,
       cc.target_concept_id,
       NULLIF(cc.source_description_synonym, ''),
       cc.predicate_id
FROM (
    -- Deduplicate to one row per source_concept_code for concept creation.
    -- Pick the row with the smallest target_concept_id as representative.
    SELECT DISTINCT ON (source_concept_code)
           source_concept_code, source_description, source_vocabulary_id,
           source_concept_class_id, source_description_synonym,
           target_concept_id, valid_start, predicate_id
    FROM temp.concept_check_ns
    ORDER BY source_concept_code, target_concept_id
) cc
INNER JOIN vocab.concept cd ON cc.target_concept_id = cd.concept_id;
-- Note that the inner join above will only create NS concepts for those with a mapping to an existing standard


/*
---------  ----------  ----------  ----------  ----------
CREATE CONCEPT RELATIONSHIP STAGING TABLE FOR NEW NON-STANDARD CONCEPTS (GENERAL MAPPINGS)
---------  ----------  ----------  ----------  ----------
 */

DROP TABLE IF EXISTS vocab.concept_rel_ns_staging;

CREATE TABLE vocab.concept_rel_ns_staging AS (SELECT *
                                              FROM vocab.concept_relationship
                                              where concept_id_1 > 2000000000
                                              LIMIT 0);


/*
 ---------  ----------  ----------  ----------  ----------
 EXPLICIT RELATIONSHIP_ID PATH
 When source_to_update rows have an explicit relationship_id,
 use it directly. This handles compositional items that need
 multiple different relationship types per source concept.
 ---------  ----------  ----------  ----------  ----------
 */
INSERT INTO vocab.concept_rel_ns_staging (concept_id_1,
                                          concept_id_2,
                                          relationship_id,
                                          valid_start_date,
                                          valid_end_date,
                                          invalid_reason)
SELECT b.concept_id,
       a.target_concept_id,
       a.relationship_id,
       now()::date,
       '2099-12-31'::date,
       NULL
FROM temp.concept_check_ns_raw a
    INNER JOIN vocab.concept_ns_staging b
    ON UPPER(TRIM(a.source_concept_code)) = UPPER(TRIM(b.concept_code))
WHERE NULLIF(TRIM(a.relationship_id), '') IS NOT NULL
  AND a.target_concept_id IS NOT NULL
  AND a.target_concept_id != 0;

-- Reverse direction for explicit relationships
INSERT INTO vocab.concept_rel_ns_staging (concept_id_1,
                                          concept_id_2,
                                          relationship_id,
                                          valid_start_date,
                                          valid_end_date,
                                          invalid_reason)
SELECT a.target_concept_id,
       b.concept_id,
       CASE a.relationship_id
           WHEN 'Maps to'          THEN 'Mapped from'
           WHEN 'Is a'             THEN 'Subsumes'
           WHEN 'Subsumes'         THEN 'Is a'
           WHEN 'Has asso proc'    THEN 'Asso proc of'
           WHEN 'Asso proc of'    THEN 'Has asso proc'
           WHEN 'Has asso finding' THEN 'Asso finding of'
           WHEN 'Asso finding of' THEN 'Has asso finding'
           WHEN 'Has measurement'  THEN 'Measurement of'
           WHEN 'Measurement of'  THEN 'Has measurement'
           WHEN 'Has relat context' THEN 'Relat context of'
           WHEN 'Relat context of' THEN 'Has relat context'
           WHEN 'Has finding site' THEN 'Finding site of'
           WHEN 'Finding site of' THEN 'Has finding site'
           ELSE 'Mapped from'
       END,
       now()::date,
       '2099-12-31'::date,
       NULL
FROM temp.concept_check_ns_raw a
    INNER JOIN vocab.concept_ns_staging b
    ON UPPER(TRIM(a.source_concept_code)) = UPPER(TRIM(b.concept_code))
WHERE NULLIF(TRIM(a.relationship_id), '') IS NOT NULL
  AND a.target_concept_id IS NOT NULL
  AND a.target_concept_id != 0;


/*
 ---------  ----------  ----------  ----------  ----------
 DERIVED RELATIONSHIP PATH (legacy — when relationship_id is NULL)
 ---------  ----------  ----------  ----------  ----------
 */

-- exactMatch → Maps to / Mapped from
INSERT INTO vocab.concept_rel_ns_staging (concept_id_1,
                                          concept_id_2,
                                          relationship_id,
                                          valid_start_date,
                                          valid_end_date,
                                          invalid_reason)
SELECT b.concept_id,
       a.target_concept_id,
       'Maps to',
       now()::date,
       '2099-12-31'::date,
       NULL
FROM temp.concept_check_ns_raw a
    INNER JOIN vocab.concept_ns_staging b
    ON UPPER(TRIM(a.source_concept_code)) = UPPER(TRIM(b.concept_code))
WHERE REPLACE(trim(lower(a.predicate_id)), 'skos:', '') = 'exactmatch'
  AND NULLIF(TRIM(a.relationship_id), '') IS NULL;


INSERT INTO vocab.concept_rel_ns_staging (concept_id_1,
                                          concept_id_2,
                                          relationship_id,
                                          valid_start_date,
                                          valid_end_date,
                                          invalid_reason)
SELECT a.target_concept_id,
       b.concept_id,
       'Mapped from',
       now()::date,
       '2099-12-31'::date,
       NULL
FROM temp.concept_check_ns_raw a
    INNER JOIN vocab.concept_ns_staging b
    ON UPPER(TRIM(a.source_concept_code)) = UPPER(TRIM(b.concept_code))
WHERE REPLACE(trim(lower(a.predicate_id)), 'skos:', '') = 'exactmatch'
  AND NULLIF(TRIM(a.relationship_id), '') IS NULL;

-- broadMatch → Is a / Subsumes (no longer gated on exactMatch existing)
INSERT INTO vocab.concept_rel_ns_staging (concept_id_1,
                                          concept_id_2,
                                          relationship_id,
                                          valid_start_date,
                                          valid_end_date,
                                          invalid_reason)
SELECT b.concept_id,
       a.target_concept_id,
       'Is a',
       now()::date,
       '2099-12-31'::date,
       NULL
FROM temp.concept_check_ns_raw a
    INNER JOIN vocab.concept_ns_staging b
        ON UPPER(TRIM(a.source_concept_code)) = UPPER(TRIM(b.concept_code))
WHERE REPLACE(trim(lower(a.predicate_id)), 'skos:', '') = 'broadmatch'
  AND NULLIF(TRIM(a.relationship_id), '') IS NULL;


INSERT INTO vocab.concept_rel_ns_staging (concept_id_1,
                                          concept_id_2,
                                          relationship_id,
                                          valid_start_date,
                                          valid_end_date,
                                          invalid_reason)
SELECT a.target_concept_id,
       b.concept_id,
       'Subsumes',
       now()::date,
       '2099-12-31'::date,
       NULL
FROM temp.concept_check_ns_raw a
    INNER JOIN vocab.concept_ns_staging b
    ON UPPER(TRIM(a.source_concept_code)) = UPPER(TRIM(b.concept_code))
WHERE REPLACE(trim(lower(a.predicate_id)), 'skos:', '') = 'broadmatch'
  AND NULLIF(TRIM(a.relationship_id), '') IS NULL;

-- narrowMatch → Subsumes / Is a
INSERT INTO vocab.concept_rel_ns_staging (concept_id_1,
                                          concept_id_2,
                                          relationship_id,
                                          valid_start_date,
                                          valid_end_date,
                                          invalid_reason)
SELECT b.concept_id,
       a.target_concept_id,
       'Subsumes',
       now()::date,
       '2099-12-31'::date,
       NULL
FROM temp.concept_check_ns_raw a
    INNER JOIN vocab.concept_ns_staging b
    ON UPPER(TRIM(a.source_concept_code)) = UPPER(TRIM(b.concept_code))
WHERE REPLACE(trim(lower(a.predicate_id)), 'skos:', '') = 'narrowmatch'
  AND NULLIF(TRIM(a.relationship_id), '') IS NULL;


INSERT INTO vocab.concept_rel_ns_staging (concept_id_1,
                                          concept_id_2,
                                          relationship_id,
                                          valid_start_date,
                                          valid_end_date,
                                          invalid_reason)
SELECT a.target_concept_id,
       b.concept_id,
       'Is a',
       now()::date,
       '2099-12-31'::date,
       NULL
FROM temp.concept_check_ns_raw a
    INNER JOIN vocab.concept_ns_staging b
    ON UPPER(TRIM(a.source_concept_code)) = UPPER(TRIM(b.concept_code))
WHERE REPLACE(trim(lower(a.predicate_id)), 'skos:', '') = 'narrowmatch'
  AND NULLIF(TRIM(a.relationship_id), '') IS NULL;

-- relatedMatch → domain-specific: Procedure
INSERT INTO vocab.concept_rel_ns_staging (concept_id_1,
                                          concept_id_2,
                                          relationship_id,
                                          valid_start_date,
                                          valid_end_date,
                                          invalid_reason)
SELECT b.concept_id,
       a.target_concept_id,
       'Has asso proc',
       now()::date,
       '2099-12-31'::date,
       NULL
FROM temp.concept_check_ns_raw a
    INNER JOIN vocab.concept_ns_staging b
    ON UPPER(TRIM(a.source_concept_code)) = UPPER(TRIM(b.concept_code))
WHERE REPLACE(trim(lower(a.predicate_id)), 'skos:', '') = 'relatedmatch'
AND a.target_domain_id = 'Procedure'
AND NULLIF(TRIM(a.relationship_id), '') IS NULL;


INSERT INTO vocab.concept_rel_ns_staging (concept_id_1,
                                          concept_id_2,
                                          relationship_id,
                                          valid_start_date,
                                          valid_end_date,
                                          invalid_reason)
SELECT a.target_concept_id,
       b.concept_id,
       'Asso proc of',
       now()::date,
       '2099-12-31'::date,
       NULL
FROM temp.concept_check_ns_raw a
    INNER JOIN vocab.concept_ns_staging b
    ON UPPER(TRIM(a.source_concept_code)) = UPPER(TRIM(b.concept_code))
WHERE REPLACE(trim(lower(a.predicate_id)), 'skos:', '') = 'relatedmatch'
AND a.target_domain_id = 'Procedure'
AND NULLIF(TRIM(a.relationship_id), '') IS NULL;

-- relatedMatch → domain-specific: Condition
INSERT INTO vocab.concept_rel_ns_staging (concept_id_1,
                                          concept_id_2,
                                          relationship_id,
                                          valid_start_date,
                                          valid_end_date,
                                          invalid_reason)
SELECT b.concept_id,
       a.target_concept_id,
       'Has asso finding',
       now()::date,
       '2099-12-31'::date,
       NULL
FROM temp.concept_check_ns_raw a
    INNER JOIN vocab.concept_ns_staging b
    ON UPPER(TRIM(a.source_concept_code)) = UPPER(TRIM(b.concept_code))
WHERE REPLACE(trim(lower(a.predicate_id)), 'skos:', '') = 'relatedmatch'
AND a.target_domain_id = 'Condition'
AND NULLIF(TRIM(a.relationship_id), '') IS NULL;


INSERT INTO vocab.concept_rel_ns_staging (concept_id_1,
                                          concept_id_2,
                                          relationship_id,
                                          valid_start_date,
                                          valid_end_date,
                                          invalid_reason)
SELECT a.target_concept_id,
       b.concept_id,
       'Asso finding of',
       now()::date,
       '2099-12-31'::date,
       NULL
FROM temp.concept_check_ns_raw a
    INNER JOIN vocab.concept_ns_staging b
    ON UPPER(TRIM(a.source_concept_code)) = UPPER(TRIM(b.concept_code))
WHERE REPLACE(trim(lower(a.predicate_id)), 'skos:', '') = 'relatedmatch'
AND a.target_domain_id = 'Condition'
AND NULLIF(TRIM(a.relationship_id), '') IS NULL;

-- relatedMatch → domain-specific: Measurement
INSERT INTO vocab.concept_rel_ns_staging (concept_id_1,
                                          concept_id_2,
                                          relationship_id,
                                          valid_start_date,
                                          valid_end_date,
                                          invalid_reason)
SELECT b.concept_id,
       a.target_concept_id,
       'Has measurement',
       now()::date,
       '2099-12-31'::date,
       NULL
FROM temp.concept_check_ns_raw a
    INNER JOIN vocab.concept_ns_staging b
    ON UPPER(TRIM(a.source_concept_code)) = UPPER(TRIM(b.concept_code))
WHERE REPLACE(trim(lower(a.predicate_id)), 'skos:', '') = 'relatedmatch'
AND a.target_domain_id = 'Measurement'
AND NULLIF(TRIM(a.relationship_id), '') IS NULL;



INSERT INTO vocab.concept_rel_ns_staging (concept_id_1,
                                          concept_id_2,
                                          relationship_id,
                                          valid_start_date,
                                          valid_end_date,
                                          invalid_reason)
SELECT a.target_concept_id,
       b.concept_id,
       'Relat context of',
       now()::date,
       '2099-12-31'::date,
       NULL
FROM temp.concept_check_ns_raw a
    INNER JOIN vocab.concept_ns_staging b
    ON UPPER(TRIM(a.source_concept_code)) = UPPER(TRIM(b.concept_code))
WHERE REPLACE(trim(lower(a.predicate_id)), 'skos:', '') = 'relatedmatch'
AND a.target_domain_id = 'Observation'
AND NULLIF(TRIM(a.relationship_id), '') IS NULL;

INSERT INTO vocab.concept_rel_ns_staging (concept_id_1,
                                          concept_id_2,
                                          relationship_id,
                                          valid_start_date,
                                          valid_end_date,
                                          invalid_reason)
SELECT b.concept_id,
       a.target_concept_id,
       'Has relat context',
       now()::date,
       '2099-12-31'::date,
       NULL
FROM temp.concept_check_ns_raw a
    INNER JOIN vocab.concept_ns_staging b
    ON UPPER(TRIM(a.source_concept_code)) = UPPER(TRIM(b.concept_code))
WHERE REPLACE(trim(lower(a.predicate_id)), 'skos:', '') = 'relatedmatch'
AND a.target_domain_id = 'Observation'
AND NULLIF(TRIM(a.relationship_id), '') IS NULL;


INSERT INTO vocab.concept_rel_ns_staging (concept_id_1,
                                          concept_id_2,
                                          relationship_id,
                                          valid_start_date,
                                          valid_end_date,
                                          invalid_reason)
SELECT a.target_concept_id,
       b.concept_id,
       'Measurement of',
       now()::date,
       '2099-12-31'::date,
       NULL
FROM temp.concept_check_ns_raw a
    INNER JOIN vocab.concept_ns_staging b
    ON UPPER(TRIM(a.source_concept_code)) = UPPER(TRIM(b.concept_code))
WHERE REPLACE(trim(lower(a.predicate_id)), 'skos:', '') = 'relatedmatch'
AND a.target_domain_id = 'Measurement'
AND NULLIF(TRIM(a.relationship_id), '') IS NULL;


-- Non-standard to standard map (NS concept → S concept of same source code)

INSERT INTO vocab.concept_rel_ns_staging (concept_id_1,
                                          concept_id_2,
                                          relationship_id,
                                          valid_start_date,
                                          valid_end_date,
                                          invalid_reason)
SELECT b.concept_id,
       a.concept_id,
       'Maps to',
       now()::date,
       '2099-12-31'::date,
       NULL
FROM vocab.concept_s_staging a
INNER JOIN vocab.concept_ns_staging b
ON a.concept_code = b.concept_code;

INSERT INTO vocab.concept_rel_ns_staging (concept_id_1,
                                          concept_id_2,
                                          relationship_id,
                                          valid_start_date,
                                          valid_end_date,
                                          invalid_reason)
SELECT a.concept_id,
       b.concept_id,
       'Mapped from',
       now()::date,
       '2099-12-31'::date,
       NULL
FROM vocab.concept_s_staging a
INNER JOIN vocab.concept_ns_staging b
ON a.concept_code = b.concept_code;


-- Clean up NULL concept_id references
DELETE
FROM vocab.concept_rel_ns_staging a USING (
    SELECT MIN(ctid) as ctid, concept_id_1, array_agg(concept_id_2), array_agg(relationship_id)
    FROM vocab.concept_rel_ns_staging
    GROUP BY concept_id_1
    HAVING COUNT(*) > 1
) b
WHERE a.concept_id_1 = b.concept_id_1
  AND a.concept_id_2 = 0;

DELETE
FROM vocab.concept_rel_ns_staging a USING (
    SELECT MIN(ctid) as ctid, concept_id_2, array_agg(concept_id_1), array_agg(relationship_id)
    FROM vocab.concept_rel_ns_staging
    GROUP BY concept_id_2
    HAVING COUNT(*) > 1
) b
WHERE a.concept_id_2 = b.concept_id_2
  AND a.concept_id_1 = 0;

-- REMOVE ANY RELATIONSHIPS THAT ALREADY EXIST IN RELATIONSHIP FOLLOWING STANDARD UPDATE
DELETE
FROM vocab.concept_rel_ns_staging a USING (
    SELECT concept_id_1, concept_id_2
    FROM vocab.concept_relationship
    WHERE concept_id_1 > 2000000000
       OR concept_id_2 > 2000000000
) b
WHERE a.concept_id_1 = b.concept_id_1
  AND a.concept_id_2 = b.concept_id_2;

DELETE
FROM vocab.concept_rel_ns_staging
WHERE concept_id_2 IN (SELECT concept_id from vocab.mapping_exceptions)
   OR concept_id_1 IN (SELECT concept_id from vocab.mapping_exceptions);



/*
 ---------  ----------  ----------  ----------  ----------
 SOURCE-TO-CONCEPT-MAP UPDATE FOR NON-STANDARD MAPPINGS
 ----------  ----------  ----------  ----------  ----------
 */


INSERT INTO vocab.s2c_map_staging(source_code,
                                  source_concept_id,
                                  source_vocabulary_id,
                                  source_code_description,
                                  target_concept_id,
                                  target_vocabulary_id,
                                  valid_start_date,
                                  valid_end_date,
                                  invalid_reason)
SELECT replace(trim(ns.source_concept_code), ' ', '_'),
       b.concept_id,
       source_vocabulary_id,
       b.concept_name,
       ns.target_concept_id,
       con.vocabulary_id,
       now()::date,
       '2099-12-31'::date,
       NULL
FROM temp.concept_check_ns_raw ns
    INNER JOIN vocab.concept_ns_staging b
        ON UPPER(TRIM(ns.source_concept_code)) = UPPER(TRIM(b.concept_code))
    INNER JOIN vocab.concept con
        ON ns.target_concept_id = con.concept_id
WHERE con.standard_concept = 'S'
      AND b.concept_id IS NOT NULL
      AND REPLACE(trim(lower(ns.predicate_id)), 'skos:', '') = 'exactmatch'
      AND NULLIF(TRIM(ns.relationship_id), '') IS NULL;

-- For explicit relationship_id rows, also create s2c entries for "Maps to" relationships
INSERT INTO vocab.s2c_map_staging(source_code,
                                  source_concept_id,
                                  source_vocabulary_id,
                                  source_code_description,
                                  target_concept_id,
                                  target_vocabulary_id,
                                  valid_start_date,
                                  valid_end_date,
                                  invalid_reason)
SELECT replace(trim(ns.source_concept_code), ' ', '_'),
       b.concept_id,
       source_vocabulary_id,
       b.concept_name,
       ns.target_concept_id,
       con.vocabulary_id,
       now()::date,
       '2099-12-31'::date,
       NULL
FROM temp.concept_check_ns_raw ns
    INNER JOIN vocab.concept_ns_staging b
        ON UPPER(TRIM(ns.source_concept_code)) = UPPER(TRIM(b.concept_code))
    INNER JOIN vocab.concept con
        ON ns.target_concept_id = con.concept_id
WHERE con.standard_concept = 'S'
      AND b.concept_id IS NOT NULL
      AND NULLIF(TRIM(ns.relationship_id), '') IS NOT NULL
      AND TRIM(ns.relationship_id) = 'Maps to';

INSERT INTO vocab.s2c_map_staging(source_code,
                                  source_concept_id,
                                  source_vocabulary_id,
                                  source_code_description,
                                  target_concept_id,
                                  target_vocabulary_id,
                                  valid_start_date,
                                  valid_end_date,
                                  invalid_reason)
SELECT LEFT(replace(trim(a.concept_code), ' ', '_'), 50),
       b.concept_id,
       b.vocabulary_id,
       replace(a.concept_name, '''', ''),
       a.concept_id,
       a.vocabulary_id,
       now()::date,
       '2099-12-31'::date,
       NULL
FROM vocab.concept_s_staging a
INNER JOIN vocab.concept_ns_staging b
ON a.concept_code = b.concept_code;


DELETE
FROM vocab.s2c_map_staging a USING (
    SELECT source_concept_id,
           target_concept_id
    FROM vocab.source_to_concept_map) b
WHERE a.source_concept_id = b.source_concept_id
  AND a.target_concept_id = b.target_concept_id;


-- DEDUPLICATE ON SOURCE TO TARGET
DELETE
FROM vocab.s2c_map_staging a USING (
    SELECT MIN(ctid) as ctid, source_concept_id, target_concept_id
    FROM vocab.s2c_map_staging
    GROUP BY source_concept_id, target_concept_id
    HAVING COUNT(*) > 1
) b
WHERE a.source_concept_id = b.source_concept_id
  AND a.target_concept_id = b.target_concept_id
  AND a.ctid <> b.ctid;

-- DEDUPLICATE ON SOURCE CODE TO TARGET
DELETE
FROM vocab.s2c_map_staging a USING (
    SELECT MIN(ctid) as ctid, source_code, target_concept_id
    FROM vocab.s2c_map_staging
    GROUP BY source_code, target_concept_id
    HAVING COUNT(*) > 1
) b
WHERE a.source_code = b.source_code
  AND a.target_concept_id = b.target_concept_id
  AND a.ctid <> b.ctid;

DELETE
FROM vocab.s2c_map_staging
WHERE target_concept_id IN (SELECT concept_id from vocab.mapping_exceptions);

DELETE FROM vocab.concept_rel_ns_staging
WHERE concept_id_1 IS NULL OR concept_id_2 IS NULL;


DROP TABLE IF EXISTS vocab.mapping_metadata_staging;

CREATE TABLE vocab.mapping_metadata_staging
(
    mapping_concept_id    INTEGER NOT NULL,
    mapping_concept_code  TEXT    NOT NULL,
    confidence            FLOAT   NOT NULL,
    predicate_id          TEXT    NOT NULL,
    mapping_justification TEXT    NOT NULL,
    mapping_provider      TEXT    NOT NULL,
    author_id             INTEGER NOT NULL,
    author_label          TEXT    NOT NULL,
    reviewer_id           INTEGER NULL,
    reviewer_label        TEXT NULL,
    mapping_tool          TEXT NULL,
    mapping_tool_version  TEXT NULL
);

INSERT INTO vocab.mapping_metadata_staging
SELECT row_number() OVER (ORDER BY source_concept_code) + (SELECT count(*) FROM vocab.mapping_metadata) AS mapping_concept_id,
       CONCAT(source_concept_code, '|| - ||', source_vocabulary_id, '|| - ||', con.concept_code, '|| - ||', con.vocabulary_id) AS mapping_concept_code,
       COALESCE(confidence, 0),
       COALESCE(predicate_id, 'missing'),
       'sempav:manualMappingCuration',
       'CVB Local Pipeline' AS mapping_provider,
       1,
       COALESCE(stu.reviewer_name, 'Unknown'),
       COALESCE(rid.id, 0),
       reviewer_name,
       'CVB Pipeline',
       'v1.0'
FROM temp.source_to_update stu
    LEFT JOIN vocab.concept con
        ON con.concept_id = stu.target_concept_id
    LEFT JOIN vocab.review_ids rid
        ON trim(lower(stu.reviewer_name)) = trim(lower(rid.name))
WHERE CONCAT(source_concept_code, '|| - ||', source_vocabulary_id, '|| - ||', con.concept_code, '|| - ||', con.vocabulary_id)
          NOT IN (SELECT mapping_concept_code FROM vocab.mapping_metadata)
;




/*
 ---------  ----------  ----------  ----------  ----------
 CONCEPT_RELATIONSHIP_METADATA (OHDSI-aligned)
 Populate for all relationship predicates (excludes noMatch rows which have no relationship)
 ----------  ----------  ----------  ----------  ----------
 */

DROP TABLE IF EXISTS vocab.concept_relationship_metadata_staging;

CREATE TABLE vocab.concept_relationship_metadata_staging
(
    concept_id_1              INTEGER      NOT NULL,
    concept_id_2              INTEGER      NOT NULL,
    relationship_id           VARCHAR(20)  NOT NULL,
    relationship_predicate_id VARCHAR(20),
    relationship_group        INTEGER,
    mapping_source            VARCHAR(50),
    confidence                FLOAT,
    mapping_tool              VARCHAR(50),
    mapper                    VARCHAR(50),
    reviewer                  VARCHAR(50)
);

-- For rows with explicit relationship_id, use it directly
INSERT INTO vocab.concept_relationship_metadata_staging
SELECT
    b.concept_id                                    AS concept_id_1,
    stu.target_concept_id                           AS concept_id_2,
    COALESCE(NULLIF(TRIM(stu.relationship_id), ''), 'Maps to') AS relationship_id,
    CASE
        WHEN REPLACE(trim(lower(stu.predicate_id)), 'skos:', '') IN ('exactmatch', 'eq')   THEN 'exactMatch'
        WHEN REPLACE(trim(lower(stu.predicate_id)), 'skos:', '') IN ('broadmatch', 'up')   THEN 'broadMatch'
        WHEN REPLACE(trim(lower(stu.predicate_id)), 'skos:', '') IN ('narrowmatch', 'down') THEN 'narrowMatch'
        ELSE trim(stu.predicate_id)
    END                                             AS relationship_predicate_id,
    NULL                                            AS relationship_group,
    CONCAT('CVB:', stu.source_vocabulary_id)        AS mapping_source,
    COALESCE(stu.confidence, 0)                     AS confidence,
    'MM_C'                                          AS mapping_tool,
    COALESCE(stu.author_label, 'Unknown')           AS mapper,
    stu.reviewer_name                               AS reviewer
FROM temp.source_to_update stu
    INNER JOIN vocab.concept_ns_staging b
        ON UPPER(TRIM(stu.source_concept_code)) = UPPER(TRIM(b.concept_code))
WHERE REPLACE(trim(lower(stu.predicate_id)), 'skos:', '') NOT IN ('nomatch')
  AND stu.target_concept_id IS NOT NULL
  AND stu.target_concept_id != 0;

-- Deduplicate on composite key
DELETE FROM vocab.concept_relationship_metadata_staging a USING (
    SELECT MIN(ctid) as ctid, concept_id_1, concept_id_2, relationship_id
    FROM vocab.concept_relationship_metadata_staging
    GROUP BY concept_id_1, concept_id_2, relationship_id
    HAVING COUNT(*) > 1
) b
WHERE a.concept_id_1 = b.concept_id_1
  AND a.concept_id_2 = b.concept_id_2
  AND a.relationship_id = b.relationship_id
  AND a.ctid <> b.ctid;

INSERT INTO temp.vocab_logger(log_desc, log_count)
SELECT 'Number of Concept Relationship Metadata Entries to Create:',
       (SELECT count(*) FROM vocab.concept_relationship_metadata_staging);


INSERT INTO temp.vocab_logger(log_desc, log_count)
SELECT 'Smallest Non-Standard Concept Id Assigned in Update:',
       (SELECT COALESCE(min(concept_id)::text, 'NONE') FROM vocab.concept_ns_staging);

INSERT INTO temp.vocab_logger(log_desc, log_count)
SELECT 'Largest Non-Standard Concept Id Assigned in Update:',
       (SELECT COALESCE(max(concept_id)::text, 'NONE') FROM vocab.concept_ns_staging);

INSERT INTO temp.vocab_logger(log_desc, log_count)
SELECT 'Number of Non-Standard Concept Ids to Assign:',
       (SELECT count(*) FROM vocab.concept_ns_staging);

INSERT INTO temp.vocab_logger(log_desc, log_count)
SELECT 'Number of Mapping Metadata Entries to Create:',
       (SELECT count(*) FROM vocab.mapping_metadata_staging);
