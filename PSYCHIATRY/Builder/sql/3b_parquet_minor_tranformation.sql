-- 3b_parquet_minor_transformation.sql
-- Purpose: Apply minor transformations to the public.parquet_test_jz table

-- Combined transformation: Update all columns in a single statement
UPDATE public.parquet_test_jz
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

-- Verify the transformations
SELECT 
    target_domain_id,
    COUNT(*) as count
FROM public.parquet_test_jz 
GROUP BY target_domain_id
ORDER BY target_domain_id;

-- Verify column lengths after truncation
SELECT 
    'source_code' as column_name,
    MAX(LENGTH(source_code)) as max_length,
    MIN(LENGTH(source_code)) as min_length,
    COUNT(*) as total_rows
FROM public.parquet_test_jz
WHERE source_code IS NOT NULL AND source_code != ''

UNION ALL

SELECT 
    'source_description' as column_name,
    MAX(LENGTH(source_description)) as max_length,
    MIN(LENGTH(source_description)) as min_length,
    COUNT(*) as total_rows
FROM public.parquet_test_jz
WHERE source_description IS NOT NULL AND source_description != ''

UNION ALL

SELECT 
    'source_description_synonym' as column_name,
    MAX(LENGTH(source_description_synonym)) as max_length,
    MIN(LENGTH(source_description_synonym)) as min_length,
    COUNT(*) as total_rows
FROM public.parquet_test_jz
WHERE source_description_synonym IS NOT NULL AND source_description_synonym != ''

ORDER BY column_name;

