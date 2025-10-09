-- =============================================================================
-- Load Parquet data from S3 into Redshift psych_mapping table
-- =============================================================================
-- 
-- Source: s3://winship-cars/joan/CustomConcepts_Emory.parquet
-- Credentials: Injected dynamically by PowerShell script
-- Format: Parquet with Snappy compression
--

-- Clear existing data to avoid duplicates
TRUNCATE TABLE public.psych_mapping;

-- Load data from S3 Parquet file
COPY public.psych_mapping 
FROM 's3://winship-cars/joan/CustomConcepts_Emory.parquet'
CREDENTIALS 'aws_access_key_id={ACCESS_KEY};aws_secret_access_key={SECRET_KEY};token={SESSION_TOKEN}'
FORMAT AS PARQUET;