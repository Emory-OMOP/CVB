# PowerShell script for Redshift connection

# Load credentials from file
$credentials = @{}
Get-Content "C:\Users\xzhan50\.aws\redshift_win_dw.txt" | ForEach-Object {
    $key, $value = $_ -split '=', 2
    $credentials[$key] = $value
}

$SQL_DIRECTORY = "C:/Users/xzhan50/Documents/GitHub/CVB/PSYCHIATRY/Builder/sql"

# Function to run psql commands
function Run-SQL($sqlCommand, $description) {
    if ($description) { Write-Host $description }
    $env:PGPASSWORD = $credentials['password']
    $env:PGCLIENTENCODING = "UTF8"
    & "C:\Program Files\PostgreSQL\17\bin\psql.exe" -h $credentials['host'] -p $credentials['port'] -d $credentials['database'] -U $credentials['user'] --set=sslmode=require @sqlCommand
}

# Create tables
Run-SQL @("-f", "$SQL_DIRECTORY/2a_source-ddl.sql") "Creating tables..."
