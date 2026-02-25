-- EDIT THIS FILE: Register your vocabulary in the OMOP vocab tables.
--
-- This runs ONCE when the vocabulary is first created.
-- Replace MY_VOCAB / MY_VOCAB_CONCEPT_ID with values from vocab.env.
--
-- VOCAB_ID       -> The vocabulary_id (e.g., 'CARDIOLOGY')
-- VOCAB_CONCEPT_ID -> The concept_id for the vocabulary concept (e.g., 2082499999)

INSERT INTO vocab.concept (concept_id, concept_name, domain_id, vocabulary_id, concept_class_id, standard_concept,
                           concept_code, valid_start_date, valid_end_date, invalid_reason)
VALUES (2082499999, 'MY_VOCAB', 'Metadata', 'Vocabulary', 'Vocabulary', 'S',
        'OMOP generated', now()::date, '2099-12-31', NULL);

INSERT INTO vocab.vocabulary (vocabulary_id, vocabulary_name, vocabulary_reference, vocabulary_version,
                              vocabulary_concept_id)
VALUES ('MY_VOCAB', 'MY_VOCAB Custom Terminology', 'OMOP generated', now()::date, 2082499999);
