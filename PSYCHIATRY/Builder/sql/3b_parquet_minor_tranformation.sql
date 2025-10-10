-- 3b_parquet_minor_transformation.sql
-- Purpose: Apply minor transformations to the public.parquet_test_jz table

-- Combined transformation: Update all columns in a single statement
UPDATE public.psych_mapping_emory
SET 
    target_domain_id = COALESCE(
        NULLIF(INITCAP(target_domain_id), ''), 
        'Metadata'
    ),
    source_code = CASE 
        WHEN LENGTH(source_code) > 50 
        THEN LEFT(source_code, 50) 
        ELSE source_code 
    END,
    source_description = CASE 
        WHEN LENGTH(source_description) > 255 
        THEN LEFT(source_description, 255) 
        ELSE source_description 
    END,
    source_description_synonym = CASE 
        WHEN LENGTH(source_description_synonym) > 255 
        THEN LEFT(source_description_synonym, 255) 
        ELSE source_description_synonym 
    END;



