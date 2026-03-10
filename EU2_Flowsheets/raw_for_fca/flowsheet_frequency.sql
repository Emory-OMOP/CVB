-- Flowsheet row frequency counts for ws_frequency column in mapping.csv
-- Run in Clarity SQL client, export results as CSV
-- Join to mapping.csv on source_concept_code = source_concept_code

SELECT CAST(FLO_MEAS_ID AS VARCHAR) AS source_concept_code,
       COUNT(*)                      AS ws_frequency
FROM clarity_onprem_omop.ip_flwsht_meas
GROUP BY FLO_MEAS_ID
ORDER BY ws_frequency DESC;
