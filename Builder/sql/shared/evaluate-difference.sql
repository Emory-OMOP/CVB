-- Parameterized: pass via psql -v id_range_min=... -v id_range_max=...

-- CHECK STANDARD CUSTOM CONCEPTS USING SUGGESTED NAME (WITHOUT REFERENCE)
DROP TABLE IF EXISTS temp.CONCEPT_CHECK_S;
DROP TABLE IF EXISTS temp.SRC_DESC_MATCH;
DROP TABLE IF EXISTS temp.CONCEPT_CHECK_S_RAW;
DROP TABLE IF EXISTS temp.CONCEPT_CHECK_NS_RAW;


-- CONCEPT_CHECK_S: items that need a NEW Standard custom concept.
-- These are noMatch items, OR items whose source_concept_code has NO
-- exactMatch row AND no explicit relationship_id (i.e. unmapped items
-- that the pipeline should create a standard concept for).
-- Items with an explicit relationship_id (e.g. compositional mappings)
-- are handled as non-standard concepts with explicit relationships.
CREATE TABLE temp.CONCEPT_CHECK_S AS
    (SELECT *
     FROM (SELECT * FROM temp.source_to_update sc
              LEFT JOIN (SELECT *
                         FROM vocab.CONCEPT
                         WHERE (concept_id > :id_range_min AND concept_id < :id_range_max)
                           AND standard_concept = 'S') co
                        ON TRIM(UPPER(sc.source_concept_code)) = TRIM(UPPER(co.concept_code))) a
     WHERE REPLACE(trim(lower(a.predicate_id)), 'skos:', '') = 'nomatch'
     OR (a.source_description NOT IN (SELECT source_description FROM temp.source_to_update WHERE REPLACE(trim(lower(predicate_id)), 'skos:', '') = 'exactmatch')
         AND NULLIF(TRIM(a.relationship_id), '') IS NULL));


-- TRACK ALL CUSTOM REQUESTS
CREATE TABLE temp.SRC_DESC_MATCH AS (
    SELECT *
    FROM temp.CONCEPT_CHECK_S
);

CREATE TABLE temp.CONCEPT_CHECK_S_RAW AS (
    SELECT *
    FROM temp.CONCEPT_CHECK_S
);

-- RETAIN ONLY UNIQUE SOURCE CODES FOR STANDARD ID ASSIGNMENT
-- Use source_concept_code (not source_description) so multi-target rows
-- for the same item don't create duplicate concepts.
DELETE
FROM temp.CONCEPT_CHECK_S a USING (
    SELECT MIN(ctid) as ctid, source_concept_code
    FROM temp.CONCEPT_CHECK_S
    GROUP BY source_concept_code
    HAVING COUNT(*) > 1
) b
WHERE a.source_concept_code = b.source_concept_code
  AND a.ctid <> b.ctid;



-- REMOVE UNIQUE STANDARDS FROM SUGGESTED NAME DUPLICATES

DELETE
FROM temp.SRC_DESC_MATCH a USING (
    SELECT source_concept_id
    FROM temp.CONCEPT_CHECK_S
) b
WHERE a.source_concept_id = b.source_concept_id;

-- REMOVE ALL PREVIOUS MAPPINGS FROM SUGGESTED NAME DUPLICATES (ONLY INCLUDE THOSE THAT ARE NEW WITH DUPLICATED S N)

DELETE
FROM temp.SRC_DESC_MATCH a USING (
    SELECT concept_id
    FROM vocab.concept
    WHERE concept_id > 2000000000
) b
WHERE a.source_concept_id = b.concept_id;



-- CONCEPT_CHECK_S NOW REPRESENTS ANY STANDARD CUSTOM ROWS THAT DO NOT EXIST IN MASTER VOCAB VERSION

DROP TABLE IF EXISTS temp.CONCEPT_CHECK_NS;

-- CONCEPT_CHECK_NS: items that map to existing standard concepts.
-- This includes all rows from source_to_update (multi-row items will
-- have multiple rows here — one per target relationship).
CREATE TABLE temp.CONCEPT_CHECK_NS AS
    (SELECT *
     FROM temp.source_to_update sc
              LEFT JOIN (SELECT *
                         FROM vocab.CONCEPT
                         WHERE (concept_id > :id_range_min AND concept_id < :id_range_max)
                           AND standard_concept IS NULL) co
                        ON TRIM(UPPER(sc.source_concept_code)) = TRIM(UPPER(co.concept_code)));

CREATE TABLE temp.concept_check_ns_raw AS
    SELECT * FROM temp.concept_check_ns;

-- Deduplicate NS concepts on (source_concept_code, target_concept_id) pair.
-- This preserves multi-target rows (same source, different targets) while
-- removing true duplicates (same source + same target repeated).
DELETE
FROM temp.CONCEPT_CHECK_NS a USING (
    SELECT MIN(ctid) as ctid, source_concept_code, target_concept_id
    FROM temp.CONCEPT_CHECK_NS
    GROUP BY source_concept_code, target_concept_id
    HAVING COUNT(*) > 1
) b
WHERE a.source_concept_code = b.source_concept_code
  AND a.target_concept_id = b.target_concept_id
  AND a.ctid <> b.ctid;

DELETE
FROM temp.CONCEPT_CHECK_NS
WHERE concept_name IS NOT NULL;
