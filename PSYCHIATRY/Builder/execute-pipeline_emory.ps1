# PowerShell script for Emory Data Pipeline
# Converts Excel -> Parquet -> S3 -> Redshift

# =============================================================================
# CONFIGURATION VARIABLES and DATABASE CONNECTION
# =============================================================================
# step 1.1: Python script
$PYTHON_SCRIPT = "excel2parquet_s3_emory.py"

# step 1.2: File paths for database and cloud service connection files
$SQL_DIRECTORY = "./sql"
$REDSHIFT_CRED_FILE = "$env:USERPROFILE\.aws\redshift_win_dw.txt"
$AWS_CRED_FILE = "$env:USERPROFILE\.aws\credentials"

# step 1.3: Read Redshift credentials
$AWS_PROFILE = "carsanalyst-900040921699"

# step 1.4: Read Redshift credentials
$credentials = @{}
Get-Content $REDSHIFT_CRED_FILE | ForEach-Object {
    $key, $value = $_ -split '=', 2
    $credentials[$key] = $value
}

# =============================================================================
# FUNCTIONS
# =============================================================================
# step 2.1: Function to read AWS credentials from credentials file
function Get-AWSCredentials($profile) {
    $credentials = @{}
    $inProfile = $false
    
    Get-Content $AWS_CRED_FILE | ForEach-Object {
        if ($_ -match "^\[$profile\]") {
            $inProfile = $true
        } elseif ($_ -match "^\[.*\]") {
            $inProfile = $false
        } elseif ($inProfile -and $_ -match "^(.+?)\s*=\s*(.+)$") {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            $credentials[$key] = $value
        }
    }
    return $credentials
}

# step 2.2: Function to run psql commands
function Run-SQL($sqlCommand, $description) {
    if ($description) { Write-Host $description }
    $env:PGPASSWORD = $credentials['password']
    $env:PGCLIENTENCODING = "UTF8"
    & "C:\Program Files\PostgreSQL\17\bin\psql.exe" -h $credentials['host'] -p $credentials['port'] -d $credentials['database'] -U $credentials['user'] --set=sslmode=require @sqlCommand
}

# step 2.3: Function to run SQL with AWS credentials substitution
function Run-SQL-WithAWS($sqlFile, $description, $awsCredentials) {
    if ($description) { Write-Host $description }
    
    # Read the SQL file and substitute placeholders
    $sqlContent = Get-Content $sqlFile -Raw
    $sqlContent = $sqlContent -replace '\{ACCESS_KEY\}', $awsCredentials['aws_access_key_id']
    $sqlContent = $sqlContent -replace '\{SECRET_KEY\}', $awsCredentials['aws_secret_access_key']
    $sqlContent = $sqlContent -replace '\{SESSION_TOKEN\}', $awsCredentials['aws_session_token']
    
    # Execute the SQL
    $env:PGPASSWORD = $credentials['password']
    $env:PGCLIENTENCODING = "UTF8"
    $sqlContent | & "C:\Program Files\PostgreSQL\17\bin\psql.exe" -h $credentials['host'] -p $credentials['port'] -d $credentials['database'] -U $credentials['user'] --set=sslmode=require
}

# =============================================================================
# PIPELINE EXECUTION                                                          # 
# =============================================================================

# step 3.1:Convert Excel to Parquet and save it to S3
Write-Host "Converting Excel to Parquet..." -ForegroundColor Green
python $PYTHON_SCRIPT
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to convert Excel to Parquet"
    exit 1
}

# step 3.2: Creating general concepts tables (run only on first execution)
# Run-SQL @("-f", "$SQL_DIRECTORY/1_create_general_concepts_ddl.sql")

# step 3.3: Create tables for source mapping files
Run-SQL @("-f", "$SQL_DIRECTORY/2a_source-ddl.sql") "Creating tables..."

# step 3.4: Load data from S3 Parquet into psych_mapping_emory table
Write-Host "Loading data from S3 Parquet..." -ForegroundColor Green
$awsCredentials = Get-AWSCredentials $AWS_PROFILE
Run-SQL-WithAWS "$SQL_DIRECTORY/3a_load-source-prep.sql" "Loading S3 data..." $awsCredentials

# step 3.5: Convert raw mappings to source tables
Run-SQL @("-f", "$SQL_DIRECTORY/3b_load-source.sql") "Loading raw mappings into source tables..."
