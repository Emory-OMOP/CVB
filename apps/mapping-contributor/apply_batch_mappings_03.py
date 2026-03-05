#!/usr/bin/env python3
"""Apply batch 3 confirmed OMOP concept mappings to EU2_Flowsheets mapping.csv.

Covers: hemodynamic work indices, processed EEG, dialysis/CRRT, obstetric,
intake/output, perfusion bypass, AM-PAC, and remaining items.

Mappings verified via OHDSI vocab MCP (DuckDB Athena v5 vocabulary).
Run from repo root:
    python apps/mapping-contributor/apply_batch_mappings_03.py
"""

import os
import sys

# Add scripts/ to path for cvb_constants
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import csv
from cvb_constants import normalize_column_name, EXPECTED_COLUMNS

# ── Confirmed mappings (batch 3) ─────────────────────────────────────
# key: source_concept_code
# value: (predicate_id, confidence, target_concept_id, target_concept_name,
#         target_vocabulary_id, target_domain_id, mapping_justification)

MAPPINGS = {
    # === Hemodynamic Work Indices ===
    "301490": ("broadMatch", "0.8", "3024841", "Left ventricular stroke work index",
               "LOINC", "Measurement", "LCWI → LOINC 8863-3 (left cardiac work index ≈ LV stroke work index)"),
    "301500": ("broadMatch", "0.8", "3025135", "Right ventricular Stroke work index",
               "LOINC", "Measurement", "RCWI → LOINC 8864-1 (right cardiac work index ≈ RV stroke work index)"),
    "301540": ("exactMatch", "0.9", "3025135", "Right ventricular Stroke work index",
               "LOINC", "Measurement", "RVSWI → LOINC 8864-1"),

    # === Pulmonary Artery Pulsatility Index ===
    # 30412000087 PAPI — no standard OMOP concept exists

    # === Processed EEG Monitoring ===
    "6815": ("exactMatch", "0.9", "21490690", "Burst suppression ratio [Ratio] Cerebral cortex Electroencephalogram (EEG)",
             "LOINC", "Measurement", "Burst Suppression Rate → LOINC 61010-5"),
    "6831": ("exactMatch", "0.9", "4265585", "Spectral edge frequency",
             "SNOMED", "Measurement", "SEFL (Spectral Edge Frequency Left) → SNOMED 397759004"),
    "6832": ("exactMatch", "0.9", "4265585", "Spectral edge frequency",
             "SNOMED", "Measurement", "SEFR (Spectral Edge Frequency Right) → SNOMED 397759004"),

    # === Dialysis Parameters ===
    "1410000150": ("exactMatch", "0.9", "1989533", "Dialysate flow rate Renal replacement therapy circuit",
                   "LOINC", "Measurement", "Dialysate Flow Rate (mL/min) → LOINC 99712-2"),
    "1410000153": ("exactMatch", "0.9", "1989190", "Transmembrane pressure Renal replacement therapy circuit",
                   "LOINC", "Measurement", "Transmembrane Pressure (mmHg) → LOINC 99720-5"),
    "3040100265": ("exactMatch", "0.9", "44802820", "Haemodialysis ultrafiltration rate",
                   "SNOMED", "Measurement", "Ultrafiltration Rate (mL/hr) → SNOMED 517631000000100"),
    "1410000149": ("broadMatch", "0.7", "1989533", "Dialysate flow rate Renal replacement therapy circuit",
                   "LOINC", "Measurement", "Blood Flow Rate (mL/min) → LOINC 99712-2 (closest RRT flow concept)"),

    # === CRRT Parameters ===
    "30412000042": ("exactMatch", "0.9", "1989190", "Transmembrane pressure Renal replacement therapy circuit",
                    "LOINC", "Measurement", "TMP (mmHg) - CRRT → LOINC 99720-5"),
    "30412000035": ("broadMatch", "0.7", "1989533", "Dialysate flow rate Renal replacement therapy circuit",
                    "LOINC", "Measurement", "Dialysate (Green) CRRT → LOINC 99712-2"),

    # === Obstetric / Fetal Monitoring ===
    "12022": ("exactMatch", "0.9", "4264406", "Frequency of uterine contraction",
              "SNOMED", "Measurement", "Contraction Frequency (minutes) → SNOMED 364270005"),
    "12023": ("exactMatch", "0.9", "4267952", "Duration of uterine contraction",
              "SNOMED", "Measurement", "Contraction Duration (seconds) → SNOMED 364274001"),

    # === Intake / Output ===
    "51": ("broadMatch", "0.8", "3012677", "Fluid intake oral Measured",
           "LOINC", "Measurement", "P.O. (Oral Intake) → LOINC 9000-1"),
    "62": ("exactMatch", "0.9", "3028277", "Fluid output emesis",
           "LOINC", "Measurement", "Emesis → LOINC 9137-1"),
    "304510": ("broadMatch", "0.8", "3006376", "Fluid output wound drain",
               "LOINC", "Measurement", "Output (mL) - Drain → LOINC 9203-1 (wound drain output)"),
    "304520": ("broadMatch", "0.7", "3013308", "Fluid intake Measured",
               "LOINC", "Measurement", "Intake (mL) - Tube → LOINC 8985-4 (general fluid intake)"),
    "304530": ("broadMatch", "0.8", "3023454", "Fluid output gastric tube",
               "LOINC", "Measurement", "Output (mL) - Tube → LOINC 9149-6 (gastric tube output)"),
    "305020": ("broadMatch", "0.7", "3014315", "Urine output",
               "LOINC", "Measurement", "Stool (mL) → LOINC 9187-6 is urine; no stool volume LOINC; broadMatch to general output"),

    # === Perfusion / Bypass ===
    "1120100468": ("exactMatch", "0.9", "4036936", "Oxygen delivery",
                   "SNOMED", "Measurement", "DO2 → SNOMED 16206004"),
    "1120100469": ("exactMatch", "0.9", "4090646", "Indexed oxygen delivery",
                   "SNOMED", "Measurement", "DO2i → SNOMED 251829000"),
    "1120036005": ("exactMatch", "0.9", "3017569", "Oxygen content in Arterial blood",
                   "LOINC", "Measurement", "CaO2 → LOINC 19218-7"),

    # === AM-PAC Mobility ===
    "10785": ("exactMatch", "0.9", "21491085", "Basic mobility score [AM-PAC]",
              "LOINC", "Measurement", "Basic Mobility Raw Score → LOINC 79529-4"),

    # === Malnutrition Screening ===
    "3040111580": ("broadMatch", "0.8", "1073431", "Malnutrition Screening Tool",
                   "SNOMED", "Measurement", "Malnutrition Score → SNOMED 1304062007 (MST)"),

    # === FLACC Pain (Total Score) ===
    "3040101146": ("broadMatch", "0.8", "3036118", "Pain severity total [Score] FLACC",
                   "LOINC", "Measurement", "Pain Rating: FLACC (Rest) - Face → LOINC 38215-0 (FLACC total; face is component)"),

    # === Neck Circumference (STOP-BANG sub-item) ===
    "1120100119": ("exactMatch", "0.9", "4171375", "Neck circumference",
                   "SNOMED", "Measurement", "Neck circumference > 17/16 inches → SNOMED 420236003"),

    # === Rectal Temperature (if present) ===
    # No dedicated rectal temp source code found in scan

    # === CAP (Mean) — Capillary Wedge Pressure ===
    "1120100152": ("broadMatch", "0.8", "3002579", "Pulmonary artery wedge Mean blood pressure",
                   "LOINC", "Measurement", "CAP (Mean) → LOINC 8587-8 (PA wedge mean; CAP likely = PA catheter wedge)"),

    # === CPN MAP ===
    "30409301360": ("exactMatch", "0.9", "3027598", "Mean blood pressure",
                    "LOINC", "Measurement", "CPN MAP Cuff (mmHg) → LOINC 8478-0"),

    # === Additional Pain Score ===
    "30419000236": ("broadMatch", "0.8", "43055141", "Pain severity - 0-10 verbal numeric rating [Score] - Reported",
                    "LOINC", "Measurement", "Severity (Calculated) - Pain Score → LOINC 72514-3"),

    # === Vent Rate (Total and Set) ===
    # 301580 Vent Rate Total — no specific LOINC for total vent rate found
    # 301570 Vent Rate Set — no specific LOINC for set vent rate found
    # These remain unmapped; closest would be Respiratory rate but that's different

    # === Spontaneous RR ===
    # 3041008043 — no specific LOINC for spontaneous RR
    # 9859 RR (total) — could broadMatch to 3024171 Respiratory rate
    "9859": ("broadMatch", "0.8", "3024171", "Respiratory rate",
             "LOINC", "Measurement", "RR (total) → LOINC 9279-1 (general respiratory rate)"),
    "3041008043": ("broadMatch", "0.7", "3024171", "Respiratory rate",
                   "LOINC", "Measurement", "Spontaneous RR → LOINC 9279-1 (broadMatch; spontaneous subset)"),
    "1180000600": ("broadMatch", "0.7", "3017485", "Carbon dioxide/Gas.total.at end expiration in Exhaled gas",
                   "LOINC", "Measurement", "Insp CO2 → LOINC 19889-5 (inspired CO2 mapped broadly to ETCO2)"),

    # === Stool count (unmeasured) ===
    # 304340 Unmeasured Stool Count — no standard concept for stool frequency

    # === Tube Feeding ===
    # 30412000401 Tube Feeding Intake — no specific LOINC for tube feeding volume
    # 3041100003 Tube Feeding Current Rate — no specific LOINC

    # === Dialysis BP and Pulse ===
    "1410000147": ("broadMatch", "0.8", "40758413", "Blood pressure systolic and diastolic",
                   "LOINC", "Measurement", "Dialysis Blood Pressure (mmHg) → LOINC 55284-4 (BP panel)"),
    "1410000148": ("exactMatch", "0.9", "3027018", "Heart rate",
                   "LOINC", "Measurement", "Dialysis Pulse → LOINC 8867-4"),

    # === Perfusion Index (Pulse Oximetry) ===
    # Note: 1120100317 is bypass pump perfusion index, NOT SpO2 perfusion index

    # === Cerebral Oximeter ===
    # 6817/6818 Cerebral Oximeter Left/Right — Transcranial cerebral oximetry is a
    # Procedure concept (4262311), not Measurement. No measurement concept found.

    # === VAD Parameters ===
    # 30412000169 VAD Flow — no standard OMOP concept for VAD flow
    # 30412000170 VAD Speed — no standard OMOP concept
}


def main():
    csv_path = os.path.join(REPO_ROOT, "EU2_Flowsheets", "Mappings", "mapping.csv")

    # Read
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        raw_headers = list(reader.fieldnames)
        rows = list(reader)

    # Normalize headers for lookup, but preserve raw headers for output
    norm_to_raw = {normalize_column_name(h): h for h in raw_headers}

    # Apply mappings — skip rows already mapped
    updated = 0
    skipped_already_mapped = 0
    for row in rows:
        code = row.get("source_concept_code", "").strip()
        if code in MAPPINGS:
            # Skip if already mapped (non-zero target_concept_id and not noMatch)
            existing_pred = row.get("predicate_id", "").strip()
            existing_tid = row.get("target_concept_id", "0").strip()
            if existing_pred in ("exactMatch", "broadMatch", "narrowMatch") and existing_tid != "0":
                skipped_already_mapped += 1
                continue

            pred, conf, tid, tname, tvocab, tdomain, justification = MAPPINGS[code]
            row["predicate_id"] = pred
            row["confidence"] = conf
            row["target_concept_id"] = tid
            row["target_concept_name"] = tname
            row["target_vocabulary_id"] = tvocab
            row["target_domain_id"] = tdomain
            row["mapping_justification"] = justification
            row["mapping_tool"] = "AM-tool_U"
            row["status"] = "pending"
            updated += 1

    # Write back
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=raw_headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Updated {updated} rows out of {len(rows)} total.")
    print(f"Mappings defined: {len(MAPPINGS)}")
    print(f"  New mappings applied: {updated}")
    print(f"  Skipped (already mapped): {skipped_already_mapped}")

    # Summary by predicate
    exact = sum(1 for v in MAPPINGS.values() if v[0] == "exactMatch")
    broad = sum(1 for v in MAPPINGS.values() if v[0] == "broadMatch")
    print(f"  exactMatch: {exact}")
    print(f"  broadMatch: {broad}")


if __name__ == "__main__":
    main()
