
-- 3b_load-source.sql
-- Purpose: Apply minor transformations to the public.psych_mapping_emory table

-- Insert transformed data into source_to_update table
INSERT INTO public.source_to_update (
    source_concept_code,
    source_concept_id,
    source_vocabulary_id,
    source_domain_id,
    source_concept_class_id,
    source_description,
    source_description_synonym,
    valid_start,
    relationship_id,
    predicate_id,
    confidence,
    target_concept_id,
    target_concept_code,
    target_concept_name,
    target_vocabulary_id,
    target_domain_id,
    decision,
    review_date,
    reviewer_name,
    reviewer_specialty,
    reviewer_comment,
    orcid_id,
    reviewer_affiliation_name,
    status,
    author_comment,
    change_required
)
WITH all_mappings AS (
    SELECT                     
    -- Truncate source_concept_code to 50 chars if needed
    CASE 
        WHEN LENGTH(source_concept_code) > 50 
        THEN LEFT(source_concept_code::VARCHAR, 50) 
        ELSE source_concept_code::VARCHAR 
    END AS source_concept_code,

    source_concept_id,
    source_vocabulary_id,

    COALESCE(target_domain_id::VARCHAR, 'Metadata') AS source_domain_id, -- note "fixme" from the original one, need to figure it out what we need here - jz 10/10/2025
     
     'Suppl Concept'::VARCHAR AS source_concept_class_id,

    -- Truncate source_description to 255 chars if needed
    CASE 
        WHEN LENGTH(source_description) > 255 
        THEN LEFT(source_description::VARCHAR, 255) 
        ELSE source_description::VARCHAR 
    END AS source_description,

    -- Truncate source_description_synonym to 255 chars if needed
    CASE 
        WHEN LENGTH(source_description_synonym) > 255 
        THEN LEFT(source_description_synonym::VARCHAR, 255) 
        ELSE source_description_synonym::VARCHAR 
    END AS source_description_synonym,

    CURRENT_DATE AS valid_start,

    relationship_id,
    predicate_id,
    confidence,
    target_concept_id,

    NULL::VARCHAR AS target_concept_code,
    
    target_concept_name,
    target_vocabulary_id,

    -- Capitalize target_domain_id, default to 'Metadata' if null/empty
    COALESCE(
        NULLIF(INITCAP(target_domain_id::VARCHAR), ''), 
        'Metadata'
    ) AS target_domain_id,

    final_decision as decision,
    review_date_mm_dd_yy as review_date,
    reviewer_label as reviewer_name,
    reviewer_specialty,
    reviewer_comment,
    reviewer_orcid_id as orcid_id,

    NULL::VARCHAR AS reviewer_affiliation_name,
    NULL::VARCHAR AS status,

    author_comment,

    NULL::VARCHAR as change_required

FROM public.psych_mapping_emory
)
SELECT 
    source_concept_code,
    source_concept_id,
    source_vocabulary_id,
    source_domain_id,
    source_concept_class_id,
    source_description,
    source_description_synonym,
    valid_start,
    relationship_id,
    predicate_id,
    confidence,
    target_concept_id,
    target_concept_code,
    target_concept_name,
    target_vocabulary_id,
    target_domain_id,
    decision,
    review_date,
    reviewer_name,
    reviewer_specialty,
    reviewer_comment,
    orcid_id,
    reviewer_affiliation_name,
    status,
    author_comment,
    change_required
FROM all_mappings;


