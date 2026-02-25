-- Parameterized: pass via psql -v id_range_min=... -v id_range_max=... -v id_range_start=...
DROP SEQUENCE IF EXISTS vocab.master_id_assignment;

-- Note - I usually give a small buffer (100 uids or so) for admin/special custom ids
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
