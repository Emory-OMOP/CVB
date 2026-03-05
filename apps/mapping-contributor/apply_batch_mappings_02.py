#!/usr/bin/env python3
"""Apply batch 2 confirmed OMOP concept mappings to EU2_Flowsheets mapping.csv.

Mappings verified via OHDSI vocab MCP (DuckDB Athena v5 vocabulary).
Run from repo root:
    python apps/mapping-contributor/apply_batch_mappings_02.py
"""

import os
import sys

# Add scripts/ to path for cvb_constants
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import csv
from cvb_constants import normalize_column_name, EXPECTED_COLUMNS

# ── Confirmed mappings (batch 2) ─────────────────────────────────────
# key: source_concept_code
# value: (predicate_id, confidence, target_concept_id, target_concept_name,
#         target_vocabulary_id, target_domain_id, mapping_justification)

MAPPINGS = {
    # === Glasgow Coma Scale ===
    "1570490029": ("exactMatch", "0.9", "3007194", "Glasgow coma score total",
                   "LOINC", "Measurement", "GCS Total → LOINC 9269-2"),
    "1570490025": ("exactMatch", "0.9", "3016335", "Glasgow coma score eye opening",
                   "LOINC", "Measurement", "Best Eye Response → LOINC 9267-6"),
    "1570490026": ("exactMatch", "0.9", "3009094", "Glasgow coma score verbal",
                   "LOINC", "Measurement", "Best Verbal Response → LOINC 9270-0"),
    "1570490027": ("exactMatch", "0.9", "3008223", "Glasgow coma score motor",
                   "LOINC", "Measurement", "Best Motor Response → LOINC 9268-4"),

    # === Arterial Line Blood Pressure ===
    "301260": ("broadMatch", "0.8", "21490853", "Invasive Systolic blood pressure",
               "LOINC", "Measurement", "Arterial Line BP 1 → LOINC 76215-3 (invasive systolic as primary component)"),
    "21838": ("broadMatch", "0.8", "21490853", "Invasive Systolic blood pressure",
              "LOINC", "Measurement", "Arterial Line BP 2 → LOINC 76215-3 (invasive systolic as primary component)"),
    "301250": ("exactMatch", "0.9", "21490852", "Invasive Mean blood pressure",
               "LOINC", "Measurement", "Arterial Line MAP 1 → LOINC 76214-6"),
    "21837": ("exactMatch", "0.9", "21490852", "Invasive Mean blood pressure",
              "LOINC", "Measurement", "Arterial Line MAP 2 → LOINC 76214-6"),
    "306270": ("exactMatch", "0.9", "21490852", "Invasive Mean blood pressure",
               "LOINC", "Measurement", "Arterial Line MAP 2 (duplicate code) → LOINC 76214-6"),
    "1120100288": ("broadMatch", "0.7", "21490853", "Invasive Systolic blood pressure",
                   "LOINC", "Measurement", "Arterial Line Pressure → invasive systolic BP as primary"),

    # === Central Venous Pressure ===
    "1120100055": ("exactMatch", "0.9", "3000333", "Central venous pressure (CVP) Mean",
                   "LOINC", "Measurement", "CVP (Mean) → LOINC 8591-0"),
    "1797": ("exactMatch", "0.9", "3000333", "Central venous pressure (CVP) Mean",
             "LOINC", "Measurement", "CVP (mean) → LOINC 8591-0"),

    # === Pulmonary Artery Pressure ===
    "1120100023": ("broadMatch", "0.8", "4353611", "Pulmonary artery pressure",
                   "SNOMED", "Measurement", "PAP → SNOMED 250767002 (general PA pressure)"),
    "450100": ("broadMatch", "0.8", "4353611", "Pulmonary artery pressure",
               "SNOMED", "Measurement", "PAP → SNOMED 250767002"),
    "1120100146": ("exactMatch", "0.9", "3028074", "Pulmonary artery Mean blood pressure",
                   "LOINC", "Measurement", "PAP (Mean) → LOINC 8414-5"),
    "1815": ("exactMatch", "0.9", "3028074", "Pulmonary artery Mean blood pressure",
             "LOINC", "Measurement", "PAP (Mean) → LOINC 8414-5"),

    # === Pulmonary Artery Wedge Pressure ===
    # (if PAWP rows exist — common PA catheter measurement)

    # === Cardiac Output / Index ===
    "301410": ("exactMatch", "0.9", "4221102", "Cardiac output",
               "SNOMED", "Measurement", "CO (L/min) → SNOMED 82799009"),
    "1120100054": ("exactMatch", "0.9", "4221102", "Cardiac output",
                   "SNOMED", "Measurement", "CO → SNOMED 82799009"),
    "301420": ("exactMatch", "0.9", "4208254", "Cardiac index",
               "SNOMED", "Measurement", "CI (L/min/m2) → SNOMED 54993008"),

    # === Stroke Volume / Index ===
    "301470": ("exactMatch", "0.9", "3036518", "Left ventricular Stroke volume",
               "LOINC", "Measurement", "SV (mL) → LOINC 20562-5"),
    "301480": ("exactMatch", "0.9", "21490880", "Left ventricular Stroke volume index",
               "LOINC", "Measurement", "SVI → LOINC 76297-1"),

    # === Systemic Vascular Resistance ===
    "1825": ("exactMatch", "0.9", "3035146", "Systemic vascular Resistance",
             "LOINC", "Measurement", "SVR (Using ABP Mean) → LOINC 8831-0"),
    "30412000085": ("exactMatch", "0.9", "3008047", "Systemic vascular Resistance index",
                    "LOINC", "Measurement", "SVRI (Using ABP Mean) → LOINC 8837-7"),

    # === Cerebral Perfusion Pressure ===
    "30412000071": ("exactMatch", "0.9", "21490695", "Cerebral perfusion pressure",
                    "LOINC", "Measurement", "CPP 1 (NIBP Mean) → LOINC 61017-0"),

    # === Femoral Line Pressures ===
    "1120100227": ("broadMatch", "0.7", "21490853", "Invasive Systolic blood pressure",
                   "LOINC", "Measurement", "FEM (femoral arterial line) → invasive systolic as primary"),
    "1120100228": ("broadMatch", "0.7", "21490852", "Invasive Mean blood pressure",
                   "LOINC", "Measurement", "FEM (Mean) → LOINC 76214-6 invasive mean BP"),

    # === Dialysis/Hemodialysis Heart Rate & BP ===
    "1180000006": ("exactMatch", "0.9", "3027018", "Heart rate",
                   "LOINC", "Measurement", "Dialysis Heart Rate → LOINC 8867-4"),
    "1180000007": ("broadMatch", "0.8", "3004249", "Systolic blood pressure",
                   "LOINC", "Measurement", "Dialysis Systolic Pressure → LOINC 8480-6"),
    "1180000008": ("broadMatch", "0.8", "3012888", "Diastolic blood pressure",
                   "LOINC", "Measurement", "Dialysis Diastolic Pressure → LOINC 8462-4"),
    "1180000009": ("broadMatch", "0.8", "3027598", "Mean blood pressure",
                   "LOINC", "Measurement", "Dialysis Mean Pressure → LOINC 8478-0"),
    "1180000010": ("exactMatch", "0.9", "3024171", "Respiratory rate",
                   "LOINC", "Measurement", "Dialysis Respiration Rate → LOINC 9279-1"),
    "1180000005": ("exactMatch", "0.9", "40762499", "Oxygen saturation in Arterial blood by Pulse oximetry",
                   "LOINC", "Measurement", "Dialysis SpO2 → LOINC 59408-5"),
    "1180000601": ("broadMatch", "0.8", "3017485", "Carbon dioxide/Gas.total.at end expiration in Exhaled gas",
                   "LOINC", "Measurement", "Dialysis Exp CO2 → LOINC 19889-5 (end-tidal CO2)"),

    # === Temperature Variants ===
    "1120100050": ("exactMatch", "0.9", "21490588", "Esophageal temperature",
                   "LOINC", "Measurement", "Esophageal Temperature → LOINC 60836-4"),
    "1120100203": ("exactMatch", "0.9", "21490870", "Bladder temperature via Foley",
                   "LOINC", "Measurement", "Bladder Temperature → LOINC 76278-1"),
    "1120100047": ("broadMatch", "0.8", "21490591", "Skin temperature --in microenvironment",
                   "LOINC", "Measurement", "Skin Temperature → LOINC 60839-8"),
    "1120100051": ("exactMatch", "0.9", "21490586", "Blood temperature",
                   "LOINC", "Measurement", "Blood Temperature → LOINC 60834-9"),
    "10700000082": ("exactMatch", "0.9", "21490587", "Arterial blood temperature",
                    "LOINC", "Measurement", "Arterial Temp → LOINC 60835-6"),
    "10700000081": ("exactMatch", "0.9", "21490769", "Venous blood temperature",
                    "LOINC", "Measurement", "Venous Temp → LOINC 75987-8"),
    "1120100147": ("broadMatch", "0.8", "3020891", "Body temperature",
                   "LOINC", "Measurement", "Temperature (Non-Specific) → LOINC 8310-5 Body temperature"),

    # === Urine Output ===
    "61": ("exactMatch", "0.9", "3014315", "Urine output",
           "LOINC", "Measurement", "Urine → LOINC 9187-6"),
    "304550": ("exactMatch", "0.9", "3014315", "Urine output",
               "LOINC", "Measurement", "Output (mL) - Urine → LOINC 9187-6"),

    # === Bladder Scan ===
    "305290": ("broadMatch", "0.8", "1988498", "US Urinary bladder Volume post void",
               "LOINC", "Measurement", "Bladder Scan Volume (mL) → LOINC 98856-8 (post-void bladder volume)"),

    # === O2 Flow Rate ===
    "250026": ("exactMatch", "0.9", "3005629", "Inhaled oxygen flow rate",
               "LOINC", "Measurement", "O2 Flow Rate (L/min) → LOINC 3151-8"),

    # === FiO2 Variants ===
    "301550": ("exactMatch", "0.9", "3020716", "Inhaled oxygen concentration",
               "LOINC", "Measurement", "FiO2 → LOINC 3150-0"),
    "3040202889": ("broadMatch", "0.8", "3020716", "Inhaled oxygen concentration",
                   "LOINC", "Measurement", "CPAP/NIV FiO2 → LOINC 3150-0"),

    # === Additional ETCO2 ===
    "7075527": ("exactMatch", "0.9", "3017485", "Carbon dioxide/Gas.total.at end expiration in Exhaled gas",
                "LOINC", "Measurement", "ETCO2 (mmHg) → LOINC 19889-5"),

    # === PEEP ===
    "301620": ("exactMatch", "0.9", "3022875", "Positive end expiratory pressure setting Ventilator",
               "LOINC", "Measurement", "PEEP (cm H2O) → LOINC 20077-4"),

    # === Tidal Volume Variants ===
    "301590": ("exactMatch", "0.9", "3012410", "Tidal volume setting Ventilator",
               "LOINC", "Measurement", "Tidal Volume Set → LOINC 20112-9"),
    "301600": ("exactMatch", "0.9", "21490752", "Tidal volume expired Respiratory system airway",
               "LOINC", "Measurement", "Tidal Volume Exhaled → LOINC 75958-9"),
    "1120100036": ("broadMatch", "0.8", "21490752", "Tidal volume expired Respiratory system airway",
                   "LOINC", "Measurement", "Tidal (Observed) → LOINC 75958-9 (expired tidal volume)"),

    # === Expired Minute Volume ===
    "1120100233": ("exactMatch", "0.9", "42527120", "Expired minute Volume during Mechanical ventilation",
                   "LOINC", "Measurement", "Expired Minute Volume → LOINC 76008-2"),

    # === Inspiratory Time ===
    "316160": ("exactMatch", "0.9", "36304672", "Inspiratory time setting Ventilator",
               "LOINC", "Measurement", "Inspiratory Time (sec) → LOINC 76334-2"),

    # === P/F Ratio ===
    "3040104807": ("exactMatch", "0.9", "3029880", "Horowitz index in Blood",
                   "LOINC", "Measurement", "P/F Ratio → LOINC 50982-8 (Horowitz index)"),

    # === Isoflurane ===
    "1120100016": ("exactMatch", "0.9", "21490631", "Isoflurane [VFr/PPres] Airway adaptor --at end expiration",
                   "LOINC", "Measurement", "Expired Isoflurane → LOINC 60895-0"),
    "1120100106": ("exactMatch", "0.9", "21490525", "Isoflurane [VFr/PPres] Airway adaptor --during inspiration",
                   "LOINC", "Measurement", "Inspired Isoflurane → LOINC 62270-4"),

    # === Desflurane ===
    "1120100017": ("exactMatch", "0.9", "21490627", "Desflurane [VFr/PPres] Airway adaptor --at end expiration",
                   "LOINC", "Measurement", "Expired Desflurane → LOINC 60877-8"),
    "1120100105": ("exactMatch", "0.9", "21490567", "Desflurane [VFr/PPres] Airway adaptor --during inspiration",
                   "LOINC", "Measurement", "Inspired Desflurane → LOINC 60805-9"),

    # === Train of Four (Neuromuscular Monitoring) ===
    "11846": ("exactMatch", "0.9", "4108453", "Train of four ratio",
              "SNOMED", "Measurement", "Train of Four Ratio → SNOMED 250831000"),
    "11847": ("exactMatch", "0.9", "4353950", "Train of four count",
              "SNOMED", "Measurement", "Train of Four Count → SNOMED 250832007"),
    "1120100045": ("broadMatch", "0.8", "4353950", "Train of four count",
                   "SNOMED", "Measurement", "Train of Four → SNOMED 250832007 (assumed count)"),

    # === Intracranial Pressure ===
    # Note: 30412000070 is "ICP 1 Location" (metadata, not the measurement itself)
    # No direct ICP measurement code found in flowsheet; ICP concepts confirmed:
    #   21490653 = ICP, 21490593 = ICP Mean, 21490594 = ICP Systolic

    # === BIS / PSI (Processed EEG) ===
    "6813": ("broadMatch", "0.7", "21490711", "Bispectral index Cerebral cortex Electroencephalogram (EEG)",
             "LOINC", "Measurement", "PSI (Patient State Index) → LOINC 75918-3 (BIS equivalent; PSI is analogous processed EEG index)"),

    # === Sedation / Delirium Scales ===
    "3040104644": ("exactMatch", "0.9", "36684829", "Richmond Agitation-Sedation Scale",
                   "SNOMED", "Measurement", "RASS → SNOMED 457441000124102"),
    "3040104650": ("broadMatch", "0.7", "44807161", "Short confusion assessment method",
                   "SNOMED", "Measurement", "Overall CAM-ICU → SNOMED 824471000000102 (short CAM is closest standard)"),

    # === Pain Scores ===
    "18": ("broadMatch", "0.8", "43055141", "Pain severity - 0-10 verbal numeric rating [Score] - Reported",
           "LOINC", "Measurement", "Pain Score → LOINC 72514-3"),
    "3040104659": ("exactMatch", "0.9", "722043", "Critical Care Pain Observation Tool (CPOT): Total score",
                   "OMOP Extension", "Measurement", "CPOT Total → OMOP5214819"),
    "3040104654": ("exactMatch", "0.9", "722044", "Critical Care Pain Observation Tool (CPOT): Facial expression score",
                   "OMOP Extension", "Measurement", "CPOT Facial Expression → OMOP5214820"),
    "3040104655": ("exactMatch", "0.9", "722048", "Critical Care Pain Observation Tool (CPOT): Body movements score",
                   "OMOP Extension", "Measurement", "CPOT Body Movements → OMOP5214824"),
    "3040104658": ("exactMatch", "0.9", "722052", "Critical Care Pain Observation Tool (CPOT): Muscle tension score",
                   "OMOP Extension", "Measurement", "CPOT Muscle Tension → OMOP5214828"),
    "3040104656": ("exactMatch", "0.9", "722056", "Critical Care Pain Observation Tool (CPOT): Compliance with the ventilator score",
                   "OMOP Extension", "Measurement", "CPOT Compliance with Ventilator → OMOP5214832"),
    "3040104657": ("exactMatch", "0.9", "722060", "Critical Care Pain Observation Tool (CPOT): Vocalization score",
                   "OMOP Extension", "Measurement", "CPOT Vocalization → OMOP5214836"),

    # === FLACC Pain ===
    # 3040101146 is "Pain Rating: FLACC (Rest) - Face" — individual component
    # FLACC total:
    # (no dedicated FLACC total source_concept_code found in scan; only Face component)

    # === NIH Stroke Scale ===
    "1570490088": ("exactMatch", "0.9", "42872749", "National Institutes of Health stroke scale",
                   "SNOMED", "Measurement", "NIH Stroke Scale → SNOMED 450741005"),

    # === PHQ-2 / PHQ-9 Depression Screening ===
    "1570000016": ("exactMatch", "0.9", "44809413", "PHQ-2 - patient health questionnaire 2",
                   "SNOMED", "Measurement", "PHQ-2 Score → SNOMED 836521000000107"),
    "1570000025": ("exactMatch", "0.9", "44804610", "PHQ-9 - Patient health questionnaire 9",
                   "SNOMED", "Measurement", "PHQ-9 Score → SNOMED 758711000000105"),

    # === GAD-7 Anxiety Screening ===
    "1570400220": ("exactMatch", "0.9", "45772733", "Generalized Anxiety Disorder 7 item scale",
                   "SNOMED", "Measurement", "GAD-7 Total Score → SNOMED 704501007"),

    # === CIWA-Ar (Alcohol Withdrawal) ===
    "1570400311": ("exactMatch", "0.9", "44809983", "CIWA-Ar - Clinical Institute Withdrawal Assessment for Alcohol scale, revised",
                   "SNOMED", "Measurement", "CIWA-Ar Total → SNOMED 895761000000107"),

    # === C-SSRS (Suicide Risk Screening) ===
    "1570400181": ("exactMatch", "0.9", "3655548", "Columbia Suicide Severity Rating Scale",
                   "SNOMED", "Measurement", "C-SSRS Risk Score → SNOMED 865998003"),

    # === AUDIT-C (Alcohol Screening) ===
    "1570400748": ("exactMatch", "0.9", "46235357", "Total score [AUDIT-C]",
                   "LOINC", "Observation", "AUDIT-C Score → LOINC 75626-2"),

    # === Modified Aldrete Score ===
    "10701000111": ("exactMatch", "0.9", "40488911", "Modified Aldrete score",
                    "SNOMED", "Measurement", "Modified Aldrete Score → SNOMED 448226000"),

    # === Pupil Size ===
    "301910": ("exactMatch", "0.9", "3021415", "Left pupil Diameter Auto",
               "LOINC", "Measurement", "L Pupil Size (mm) → LOINC 8640-5"),
    "301930": ("exactMatch", "0.9", "3027214", "Right pupil Diameter Auto",
               "LOINC", "Measurement", "R Pupil Size (mm) → LOINC 8642-1"),

    # === Capillary Refill ===
    "3040100220": ("exactMatch", "0.9", "3045676", "Capillary refill [Time]",
                   "LOINC", "Measurement", "Capillary Refill → LOINC 44971-0"),

    # === Estimated Blood Loss ===
    "1221": ("exactMatch", "0.9", "3021505", "Blood loss.total intraoperative [Volume] Estimated",
             "LOINC", "Measurement", "Est. Blood Loss → LOINC 9110-8"),

    # === Fetal Heart Rate ===
    "12086": ("exactMatch", "0.9", "4092353", "Baseline fetal heart rate",
              "SNOMED", "Measurement", "FHR Baseline Rate → SNOMED 251670001"),
    "12013": ("exactMatch", "0.9", "4089747", "Fetal heart rate variability",
              "SNOMED", "Measurement", "Variability (FHR) → SNOMED 251671002"),

    # === Mixed Venous O2 Saturation ===
    "1120000912": ("exactMatch", "0.9", "40484911", "Mixed venous oxygen saturation",
                   "SNOMED", "Measurement", "SvO2 (Bcare5) → SNOMED 442734002"),

    # === Pasero Opioid-Induced Sedation Scale ===
    # 3040104675: no standard concept found — POSS is Epic-specific

    # === Peak Inspiratory Pressure ===
    # (already mapped 1120100037 in batch 1 as PIP Observed)
    "3040102593": ("broadMatch", "0.7", "4101694", "Peak inspiratory pressure",
                   "SNOMED", "Measurement", "Insp Pressure High → SNOMED 27913002 (PIP-related alarm threshold)"),

    # === Plateau Pressure ===
    # No dedicated source code for plateau pressure found; closest is Insp Pressure Low
    "3040102585": ("broadMatch", "0.7", "44782825", "Airway plateau pressure",
                   "SNOMED", "Measurement", "Insp Pressure Low → SNOMED 698822002 (plateau pressure approximation)"),

    # === SOFA Score ===
    # No direct SOFA total source code found; only MEWS and Early Detection of Sepsis
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

    # Apply mappings — skip rows already mapped by batch 1
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
