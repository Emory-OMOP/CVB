-- FCA Master Extract: Template → Group → Row hierarchy (deduplicated)
-- Run in Clarity SQL client, export results as CSV
-- Output: EU2_Flowsheets/raw_for_fca/fca_master_extract.csv

WITH latest_version AS (
    SELECT ID, MAX(CONTACT_DATE_REAL) AS max_cdr
    FROM clarity_ehc.dbo.IP_FLO_MEASUREMNTS
    GROUP BY ID
)
SELECT
    t.TEMPLATE_ID, t.TEMPLATE_NAME, t.DISPLAY_NAME AS template_display,
    c.LINE AS comp_line, c.START_REMOVED_YN, c.REQUIRED_STATUS_C,
    g.FLO_MEAS_ID AS group_id, g.DISP_NAME AS group_name,
    m.LINE AS row_line, m.MEASUREMENT_ID AS row_id,
    r.DISP_NAME AS row_name, r.ROW_TYP_C, r.VAL_TYPE_C,
    r.UNITS, r.MINVALUE, r.MAX_VAL,
    r.INTAKE_TYP_C, r.OUTPUT_TYP_C,
    r.MIN_AGE, r.MAX_AGE, r.SEX_C
FROM clarity_ehc.dbo.IP_FLT_DATA t
JOIN clarity_ehc.dbo.IP_FLT_COMPS c ON t.TEMPLATE_ID = c.TEMPLATE_ID
JOIN clarity_ehc.dbo.IP_FLO_MEASUREMNTS m ON c.FLO_MEAS_ID = m.ID
JOIN latest_version lv ON m.ID = lv.ID AND m.CONTACT_DATE_REAL = lv.max_cdr
JOIN clarity_ehc.dbo.IP_FLO_GP_DATA g ON c.FLO_MEAS_ID = g.FLO_MEAS_ID
JOIN clarity_ehc.dbo.IP_FLO_GP_DATA r ON m.MEASUREMENT_ID = r.FLO_MEAS_ID
WHERE t.RECORD_STATE_C IS NULL
  AND (r.RECORD_STATE_C IS NULL OR r.RECORD_STATE_C = 0)
ORDER BY t.TEMPLATE_ID, c.LINE, m.LINE;
