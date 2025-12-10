
-- 3b_load-source.sql
-- Purpose: Apply minor transformations to the public.psych_mapping_emory table

-- Insert transformed data into source_to_update table
INSERT INTO public.source_to_update (
    source_concept_id,
    source_code,
    source_vocabulary_id,
    source_domain,
    source_concept_class_id,
    source_description,
    source_description_synonym,
    source_code_provenance,
    relationship_id,
    predicate_id,
    confidence,
    target_concept_id,
    target_concept_name,
    target_vocabulary_id,
    target_domain_id,
    mapping_justification,
    mapping_date_mm_dd_yy,
    mapping_tool,
    mapping_tool_version,
    author_label,
    author_orcid_id,
    author_specialty,
    author_comment ,
    author_affiliation,
    reviewer_label,
    reviewer_orcid_id,
    reviewer_specialty,
    review_date_mm_dd_yy,
    reviewer_comment,
    reviewer_affiliation,
    final_decision,
    final_comment,
    change_required,
    status 
)
WITH all_mappings AS (
    SELECT    
    source_concept_id,
    -- Truncate source_concept_code to 50 chars if needed
    CASE 
        WHEN LENGTH(source_code) > 50 
        THEN LEFT(source_code::VARCHAR, 50) 
        ELSE source_code::VARCHAR 
    END AS source_code,

    source_vocabulary_id,
    COALESCE(target_domain_id::VARCHAR, 'Metadata') AS source_domain, 
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
    
    source_code_provenance,
    relationship_id,
    predicate_id,
    confidence,
    target_concept_id,
    target_concept_name,
    target_vocabulary_id,

    -- Capitalize target_domain_id, default to 'Metadata' if null/empty
    COALESCE(
        NULLIF(INITCAP(target_domain_id::VARCHAR), ''), 
        'Metadata'
    ) AS target_domain_id,

    mapping_justification,
    mapping_date_mm_dd_yy,
    mapping_tool,
    mapping_tool_version,
    author_label,
    author_orcid_id,
    author_specialty,
    author_comment,
    author_affiliation,
    reviewer_label,
    reviewer_orcid_id,
    reviewer_specialty,
    review_date_mm_dd_yy,
    reviewer_comment,
    reviewer_affiliation,
    final_decision,
    final_comment,
    NULL::VARCHAR AS change_required,
    NULL::VARCHAR AS status  
 
FROM public.psych_mapping_emory
)
SELECT 
    source_concept_id,
    source_code,
    source_vocabulary_id,
    source_domain,
    source_concept_class_id,
    source_description,
    source_description_synonym,
    source_code_provenance,
    relationship_id,
    predicate_id,
    confidence,
    target_concept_id,
    target_concept_name,
    target_vocabulary_id,
    target_domain_id,
    mapping_justification,
    mapping_date_mm_dd_yy,
    mapping_tool,
    mapping_tool_version,
    author_label,
    author_orcid_id,
    author_specialty,
    author_comment ,
    author_affiliation,
    reviewer_label,
    reviewer_orcid_id,
    reviewer_specialty,
    review_date_mm_dd_yy,
    reviewer_comment,
    reviewer_affiliation,
    final_decision,
    final_comment,
    change_required,
    status 
FROM all_mappings;


