## How to Run the Pipeline

### Prerequisites
- Python with required packages (pandas, pyarrow, s3fs, boto3)
- PostgreSQL client (psql) installed
- AWS credentials configured in `~/.aws/credentials`
- Redshift credentials in `~/.aws/redshift_win_dw.txt`

### Running the Pipeline

1. **Navigate to the Builder directory:**
   ```powershell
   cd C:\Users\xzhan50\Documents\GitHub\CVB\PSYCHIATRY\Builder
   ```

2. **Run the pipeline script:**
   ```powershell
   ./execute-pipeline_emory.ps1
   ```

   Or if you encounter execution policy issues:
   ```powershell
   powershell -ExecutionPolicy Bypass -File ./execute-pipeline_emory.ps1
   ```

3. **The pipeline will execute the following steps:**
   - Step 3.1: Convert Excel to Parquet and upload to S3
   - Step 3.2: Create Redshift tables
   - Step 3.3: Load data from S3 Parquet file to Redshift
   - Step 3.4: Transform and load data into source_to_update table

### Notes
- Make sure you're in the Builder directory when running the script
- Check AWS credentials are current (they expire periodically)
- Review logs for any errors during execution
