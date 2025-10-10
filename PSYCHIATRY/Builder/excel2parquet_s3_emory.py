# Excel -> Parquet -> Redshift DDL -> COPY
import pandas as pd
import s3fs
import boto3
import os

fl_fd = "../Mappings/Emory/"
fl_name_in = "CustomConcepts_v20250908_final.xlsx"
wb_name = "final_09112025"
input_path = os.path.join(fl_fd, fl_name_in)

s3_parquet_path = "s3://winship-cars/joan/CustomConcepts_Emory.parquet"

# Step 1: Read Excel file
# Define explicit data types for consistent Parquet schema
dtype_mapping = {
    'source_concept_id': 'int64',
    'source_concept_code': 'str',
    'source_vocabulary_id': 'str',
    'source_domain': 'str',
    'source_description': 'str',
    'source_description_synonym': 'str',
    'source_code_provenance': 'str',
    'relationship_id': 'str',
    'predicate_id': 'str',
    'confidence': 'float64',
    'target_concept_id': 'int64',
    'target_concept_name': 'str',  # Keep as string/varchar
    'target_vocabulary_id': 'str',
    'target_domain_id': 'str',
    'mapping_justification': 'str',
    'mapping_predicate': 'str',
    'mapping_date_mm_dd_yy': 'str',
    'mapping_tool': 'str',
    'mapping_tool_version': 'str',
    'author_label': 'str',
    'author_orcid_id': 'str',
    'author_specialty': 'str',
    'author_comment': 'str',
    'reviewer_label': 'str',
    'reviewer_orcid_id': 'str',
    'reviewer_specialty': 'str',
    'review_date_mm_dd_yy': 'str',  # Will convert to date after reading
    'reviewer_comment': 'str',
    'final_decision': 'str',
    'final_comment': 'str'
}

df = pd.read_excel(
    input_path, 
    sheet_name=wb_name,
    na_values=['', 'NA', 'N/A', 'null', 'NULL', 'nan', 'NaN'],
    keep_default_na=True,
    dtype=dtype_mapping
)

# Convert date columns to proper date format (date only, no time)
if 'mapping_date_mm_dd_yy' in df.columns:
    df['mapping_date_mm_dd_yy'] = pd.to_datetime(df['mapping_date_mm_dd_yy'], errors='coerce').dt.date
if 'review_date_mm_dd_yy' in df.columns:
    df['review_date_mm_dd_yy'] = pd.to_datetime(df['review_date_mm_dd_yy'], errors='coerce').dt.date

# Fix columns with all null values to ensure proper Parquet schema
# Fill null values in object columns with empty strings to maintain string schema
object_columns = df.select_dtypes(include=['object']).columns
for col in object_columns:
    if df[col].isnull().all():  # If all values are null
        df[col] = df[col].fillna('')  # Fill with empty string


# Step 2: Write to S3 as Parquet

session = boto3.Session(profile_name='carsanalyst-900040921699')
credentials = session.get_credentials()
fs = s3fs.S3FileSystem(
    key=credentials.access_key,
    secret=credentials.secret_key,
    token=credentials.token
)

# Save to S3
df.to_parquet(
    s3_parquet_path,
    filesystem=fs,
    engine='pyarrow',
    compression='snappy',
    index=False
)


