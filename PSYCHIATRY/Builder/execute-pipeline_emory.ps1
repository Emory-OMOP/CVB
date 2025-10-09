# PowerShell script 

# Step 0:  Load credentials from file for Redshift connection
$credentials = @{}
$credFile = "$env:USERPROFILE\.aws\redshift_win_dw.txt"
Get-Content $credFile | ForEach-Object {
    $key, $value = $_ -split '=', 2
    $credentials[$key] = $value
}

$SQL_DIRECTORY = "./sql"

# Function to run psql commands
function Run-SQL($sqlCommand, $description) {
    if ($description) { Write-Host $description }
    $env:PGPASSWORD = $credentials['password']
    $env:PGCLIENTENCODING = "UTF8"
    & "C:\Program Files\PostgreSQL\17\bin\psql.exe" -h $credentials['host'] -p $credentials['port'] -d $credentials['database'] -U $credentials['user'] --set=sslmode=require @sqlCommand
}

# Step 1: Convert Excel to Parquet
Write-Host "Converting Excel to Parquet..." -ForegroundColor Green
python excel2parquet.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to convert Excel to Parquet"
    exit 1
}

# Step 2:Create tables
Run-SQL @("-f", "$SQL_DIRECTORY/2a_source-ddl.sql") "Creating tables..."
