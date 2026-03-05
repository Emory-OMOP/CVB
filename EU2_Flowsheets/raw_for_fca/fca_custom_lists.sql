-- FCA Custom List Values Export
-- Run in Clarity SQL client, export results as CSV
-- Output: EU2_Flowsheets/raw_for_fca/fca_custom_lists.csv

SELECT id, line, cust_list_abbr, cust_list_value, cust_list_map_value, cust_list_abnorml_yn
FROM clarity_ehc.dbo.IP_FLO_CUSTOM_LIST
ORDER BY id, line;
