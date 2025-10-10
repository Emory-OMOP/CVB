DROP TABLE if EXISTS public.psych_mapping_emory;
DROP TABLE if EXISTS public.source_to_update;
DROP TABLE if EXISTS public.vocab_logger;
DROP TABLE if EXISTS public.mapping_exceptions;
DROP TABLE if EXISTS public.review_ids;

CREATE TABLE public.psych_mapping_emory
(
    source_concept_id       BIGINT               ENCODE az64,
    source_code                 VARCHAR(255)         ENCODE lzo,
    source_vocabulary_id        VARCHAR(255)         ENCODE lzo,
    source_domain               VARCHAR(255)         ENCODE lzo,
    source_description          VARCHAR(255)         ENCODE lzo,
    source_description_synonym  VARCHAR(255)         ENCODE lzo,
    source_code_provenance      VARCHAR(255)         ENCODE lzo,
    relationship_id             VARCHAR(255)         ENCODE lzo,
    predicate_id                VARCHAR(255)         ENCODE lzo,
    confidence                  DOUBLE PRECISION     ENCODE raw,
    target_concept_id           BIGINT               ENCODE az64,
    target_concept_name         VARCHAR(255)         ENCODE lzo,
    target_vocabulary_id        VARCHAR(255)         ENCODE lzo,
    target_domain_id            VARCHAR(255)         ENCODE lzo,
    mapping_justification       VARCHAR(255)         ENCODE lzo,
    mapping_predicate           VARCHAR(255)         ENCODE lzo,
    mapping_date_mm_dd_yy       DATE                 ENCODE az64,
    mapping_tool                VARCHAR(255)         ENCODE lzo,
    mapping_tool_version        VARCHAR(255)         ENCODE lzo,
    author_label                VARCHAR(255)         ENCODE lzo,
    author_orcid_id             VARCHAR(255)         ENCODE lzo,
    author_specialty            VARCHAR(255)         ENCODE lzo,
    author_comments             VARCHAR(255)         ENCODE lzo,
    reviewer_label              VARCHAR(255)         ENCODE lzo,
    reviewer_orcid_id           VARCHAR(255)         ENCODE lzo,
    reviewer_specialty          VARCHAR(255)         ENCODE lzo,
    review_date_mm_dd_yy        DATE                 ENCODE az64,
    reviewer_comments           VARCHAR(255)         ENCODE lzo,
    final_decision              VARCHAR(255)         ENCODE lzo,
    final_comment               VARCHAR(255)         ENCODE lzo
);

CREATE TABLE public.source_to_update
(
    source_concept_code            VARCHAR(255)         ENCODE lzo,
    source_concept_id              BIGINT               ENCODE az64,
    source_vocabulary_id           VARCHAR(255)         ENCODE lzo,
    source_domain_id               VARCHAR(255)         ENCODE lzo,
    source_concept_class_id        VARCHAR(255)         ENCODE lzo,
    source_description             VARCHAR(255)         ENCODE lzo,
    source_description_synonym     VARCHAR(255)         ENCODE lzo,
    valid_start                    DATE                 ENCODE az64,
    relationship_id                VARCHAR(255)         ENCODE lzo,
    predicate_id                   VARCHAR(255)         ENCODE lzo,
    confidence                     DOUBLE PRECISION     ENCODE raw,
    target_concept_id              BIGINT               ENCODE az64,
    target_concept_code            VARCHAR(255)         ENCODE lzo,
    target_concept_name            VARCHAR(255)         ENCODE lzo,
    target_vocabulary_id           VARCHAR(255)         ENCODE lzo,
    target_domain_id               VARCHAR(255)         ENCODE lzo,
    decision                       BIGINT               ENCODE az64,
    review_date                    DATE                 ENCODE az64,
    reviewer_name                  VARCHAR(255)         ENCODE lzo,
    reviewer_specialty             VARCHAR(255)         ENCODE lzo,
    reviewer_comment               VARCHAR(255)         ENCODE lzo,
    orcid_id                       VARCHAR(255)         ENCODE lzo,
    reviewer_affiliation_name      VARCHAR(255)         ENCODE lzo,
    status                         VARCHAR(255)         ENCODE lzo,
    author_comment                 VARCHAR(255)         ENCODE lzo,
    change_required                VARCHAR(255)         ENCODE lzo
);

CREATE TABLE public.vocab_logger
(
    log_desc  VARCHAR(255) ENCODE lzo NULL,
    log_count VARCHAR(255) ENCODE lzo NULL
);


CREATE TABLE IF NOT EXISTS public.mapping_exceptions
(
    concept_id BIGINT ENCODE az64
);

CREATE TABLE IF NOT EXISTS public.review_ids
(
    name    VARCHAR(255)         ENCODE lzo,
    id      INTEGER              ENCODE az64
);