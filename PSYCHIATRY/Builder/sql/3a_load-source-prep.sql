-- =============================================================================
-- Load Parquet data from S3 into Redshift psych_mapping_emory table
-- =============================================================================
-- 
-- Source: s3://winship-cars/joan/CustomConcepts_Emory.parquet
-- Credentials: Injected dynamically by PowerShell script
-- Format: Parquet with Snappy compression
--

-- Clear existing data to avoid duplicates
TRUNCATE TABLE public.psych_mapping_emory;

-- Load data from S3 Parquet file
COPY public.psych_mapping_emory 
FROM 's3://winship-cars/joan/CustomConcepts_Emory.parquet'
-- Using IAM credentials (temporary keys injected by script)
CREDENTIALS 'aws_access_key_id={ACCESS_KEY};aws_secret_access_key={SECRET_KEY};token={SESSION_TOKEN}'

-- Alternatively, using IAM_ROLE is easier and more secure, but you need to ask your DBA to set it up:
-- IAM_ROLE 'arn:aws:iam::123456789012:role/YourRedshiftRole'
FORMAT AS PARQUET;