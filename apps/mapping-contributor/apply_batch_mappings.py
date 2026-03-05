#!/usr/bin/env python3
"""Apply confirmed OMOP concept mappings to EU2_Flowsheets mapping.csv.

Mappings verified via OHDSI vocab MCP (DuckDB Athena v5 vocabulary).
Run from repo root:
    python apps/mapping-contributor/apply_batch_mappings.py
"""

import os
import sys

# Add scripts/ to path for cvb_constants
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import csv
from cvb_constants import normalize_column_name, EXPECTED_COLUMNS

# ── Confirmed mappings ──────────────────────────────────────────────────
# key: source_concept_code
# value: (predicate_id, confidence, target_concept_id, target_concept_name,
#         target_vocabulary_id, target_domain_id, mapping_justification)

MAPPINGS = {
    # === Vital Signs ===
    "8": ("exactMatch", "0.9", "3027018", "Heart rate",
          "LOINC", "Measurement", "Pulse → LOINC 8867-4 Heart rate"),
    "1120100075": ("broadMatch", "0.8", "3027018", "Heart rate",
                   "LOINC", "Measurement", "HR (ECG) is ECG-derived heart rate; maps broadly to general heart rate"),
    "1120100255": ("exactMatch", "0.9", "3027018", "Heart rate",
                   "LOINC", "Measurement", "Anesthesia pulse → LOINC 8867-4 Heart rate"),
    "1120100254": ("exactMatch", "0.9", "40762499", "Oxygen saturation in Arterial blood by Pulse oximetry",
                   "LOINC", "Measurement", "SpO2 → LOINC 59408-5"),
    "10": ("exactMatch", "0.9", "40762499", "Oxygen saturation in Arterial blood by Pulse oximetry",
           "LOINC", "Measurement", "Pulse oximetry SpO2 → LOINC 59408-5"),
    "9": ("exactMatch", "0.9", "3024171", "Respiratory rate",
          "LOINC", "Measurement", "Resp → LOINC 9279-1 Respiratory rate"),
    "1120100253": ("exactMatch", "0.9", "3024171", "Respiratory rate",
                   "LOINC", "Measurement", "Anesthesia RR → LOINC 9279-1"),
    "6": ("exactMatch", "0.9", "3020891", "Body temperature",
          "LOINC", "Measurement", "Temp → LOINC 8310-5 Body temperature"),
    "891": ("broadMatch", "0.8", "3020891", "Body temperature",
            "LOINC", "Measurement", "Anesthesia temperature → LOINC 8310-5 Body temperature"),
    "3040100959": ("broadMatch", "0.8", "3020891", "Body temperature",
                   "LOINC", "Measurement", "Temp (Celsius) for APACHE IV → LOINC 8310-5 Body temperature"),
    "5": ("exactMatch", "0.9", "40758413", "Blood pressure systolic and diastolic",
          "LOINC", "Measurement", "BP panel → LOINC 55284-4"),

    # === Blood Pressure Variants ===
    "301360": ("exactMatch", "0.9", "3027598", "Mean blood pressure",
               "LOINC", "Measurement", "MAP Cuff → LOINC 8478-0 Mean blood pressure"),
    "1120100022": ("exactMatch", "0.9", "3027598", "Mean blood pressure",
                   "LOINC", "Measurement", "Anesthesia MAP → LOINC 8478-0"),
    "1120100052": ("exactMatch", "0.9", "3027598", "Mean blood pressure",
                   "LOINC", "Measurement", "NIBP (Mean) → LOINC 8478-0"),
    "1120100070": ("broadMatch", "0.7", "40758413", "Blood pressure systolic and diastolic",
                   "LOINC", "Measurement", "Anesthesia NIBP → LOINC 55284-4 BP panel (non-invasive)"),
    "1120100019": ("broadMatch", "0.7", "21490853", "Invasive Systolic blood pressure",
                   "LOINC", "Measurement", "ABP encompasses systolic/diastolic; mapped to invasive systolic as primary"),

    # === Anthropometrics ===
    "14": ("exactMatch", "0.9", "3025315", "Body weight",
           "LOINC", "Measurement", "Weight → LOINC 29463-7 Body weight"),
    "11": ("exactMatch", "0.9", "3036277", "Body height",
           "LOINC", "Measurement", "Height → LOINC 8302-2 Body height"),
    "301070": ("exactMatch", "0.9", "3038553", "Body mass index (BMI) [Ratio]",
               "LOINC", "Measurement", "BMI (Calculated) → LOINC 39156-5"),
    "301060": ("exactMatch", "0.9", "3012042", "Body surface area Derived from formula",
               "LOINC", "Measurement", "BSA (Calculated) → LOINC 3140-1"),
    "3040102602": ("exactMatch", "0.9", "3032445", "Ideal body weight",
                   "LOINC", "Measurement", "PIBW → LOINC 50064-5 Ideal body weight"),
    "7074308": ("broadMatch", "0.8", "3032445", "Ideal body weight",
                "LOINC", "Measurement", "IBW male → LOINC 50064-5 (sex-specific variant)"),
    "7074312": ("broadMatch", "0.8", "3032445", "Ideal body weight",
                "LOINC", "Measurement", "IBW female → LOINC 50064-5 (sex-specific variant)"),

    # === Respiratory / Ventilator ===
    "1120100035": ("exactMatch", "0.9", "3020716", "Inhaled oxygen concentration",
                   "LOINC", "Measurement", "FiO2 → LOINC 3150-0"),
    "1120100038": ("exactMatch", "0.9", "3022875", "Positive end expiratory pressure setting Ventilator",
                   "LOINC", "Measurement", "PEEP/CPAP → LOINC 20077-4"),
    "1120100034": ("exactMatch", "0.9", "3017485", "Carbon dioxide/Gas.total.at end expiration in Exhaled gas",
                   "LOINC", "Measurement", "ETCO2 → LOINC 19889-5 end-tidal CO2"),
    "22537": ("exactMatch", "0.9", "3017485", "Carbon dioxide/Gas.total.at end expiration in Exhaled gas",
              "LOINC", "Measurement", "ETCO2 (Monitor) → LOINC 19889-5"),
    "1120440501": ("exactMatch", "0.9", "21490847", "Respiratory rate by Carbon dioxide measurement",
                   "LOINC", "Measurement", "RR (ETCO2) → LOINC 76172-6"),
    "22523": ("exactMatch", "0.9", "3012410", "Tidal volume setting Ventilator",
              "LOINC", "Measurement", "Tidal Volume SET → LOINC 20112-9"),
    "22525": ("exactMatch", "0.9", "21490752", "Tidal volume expired Respiratory system airway",
              "LOINC", "Measurement", "Tidal Volume Expired → LOINC 75958-9"),
    "22526": ("exactMatch", "0.9", "36303816", "Tidal volume.inspired",
              "LOINC", "Measurement", "Tidal Volume Inspired → LOINC 76221-1"),
    "1120100037": ("broadMatch", "0.7", "21490785", "Pressure Respiratory system airway --during inspiration on ventilator",
                   "LOINC", "Measurement", "PIP Observed → LOINC 76003-3 (peak inspiratory pressure equivalent)"),
    "1120100012": ("broadMatch", "0.7", "3020716", "Inhaled oxygen concentration",
                   "LOINC", "Measurement", "Anesthesia O2 agent → LOINC 3150-0 (FiO2 equivalent)"),

    # === Anesthesia Agents ===
    "1120100107": ("exactMatch", "0.9", "21490633", "Sevoflurane [VFr/PPres] Airway adaptor --during inspiration",
                   "LOINC", "Measurement", "Inspired Sevoflurane → LOINC 60907-3"),
    "1120100015": ("exactMatch", "0.9", "21490634", "Sevoflurane [VFr/PPres] Airway adaptor --at end expiration",
                   "LOINC", "Measurement", "Expired Sevoflurane → LOINC 60908-1"),
    "1120100231": ("exactMatch", "0.9", "21490632", "Nitrous oxide [VFr/PPres] Airway adaptor --at end expiration",
                   "LOINC", "Measurement", "Expired N2O → LOINC 60901-6"),
    "1120100232": ("exactMatch", "0.9", "21490527", "Nitrous oxide [VFr/PPres] Airway adaptor --during inspiration",
                   "LOINC", "Measurement", "Inspired N2O → LOINC 62272-0"),
    "1120100013": ("broadMatch", "0.7", "21490526", "Nitrous oxide [VFr/PPres] Airway adaptor",
                   "LOINC", "Measurement", "N2O (general) → LOINC 62271-2 (non-phase-specific)"),
    "1120100150": ("broadMatch", "0.7", "21490573", "Minimum alveolar concentration (MAC) sum Anesthetic agent.XXX+Nitrous oxide",
                   "LOINC", "Measurement", "MAC → LOINC 60815-8 (closest MAC concept)"),

    # === Temperature Variants ===
    "1120100048": ("exactMatch", "0.9", "21490590", "Nasopharyngeal temperature",
                   "LOINC", "Measurement", "Nasopharyngeal Temperature → LOINC 60838-0"),

    # === Pain Assessment ===
    "3040104280": ("broadMatch", "0.8", "43055141", "Pain severity - 0-10 verbal numeric rating [Score] - Reported",
                   "LOINC", "Measurement", "Pain Score → LOINC 72514-3 (generic pain score, specific scale unknown)"),

    # === Braden Scale (full panel) ===
    "305180": ("exactMatch", "0.9", "3035519", "Braden scale total score",
               "LOINC", "Measurement", "Braden Scale Score → LOINC 38227-5"),
    "305120": ("exactMatch", "0.9", "3036098", "Sensory perception Braden scale",
               "LOINC", "Measurement", "Sensory Perception → LOINC 38222-6"),
    "305130": ("exactMatch", "0.9", "3037022", "Moisture exposure Braden scale",
               "LOINC", "Measurement", "Moisture → LOINC 38229-1"),
    "305140": ("exactMatch", "0.9", "3037318", "Physical activity Braden scale",
               "LOINC", "Measurement", "Out of Bed Activity → LOINC 38223-4"),
    "305150": ("exactMatch", "0.9", "3035206", "Physical mobility Braden scale",
               "LOINC", "Measurement", "In Bed Mobility → LOINC 38224-2"),
    "305160": ("exactMatch", "0.9", "3035816", "Nutrition intake pattern Braden scale",
               "LOINC", "Measurement", "Nutrition → LOINC 38225-9"),
    "305170": ("exactMatch", "0.9", "3037347", "Friction and shear Braden scale",
               "LOINC", "Measurement", "Friction and Shear → LOINC 38226-7"),
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

    # Apply mappings
    updated = 0
    for row in rows:
        code = row.get("source_concept_code", "").strip()
        if code in MAPPINGS:
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
    print(f"Mappings applied: {len(MAPPINGS)} defined, {updated} matched in CSV.")

    # Summary by predicate
    exact = sum(1 for v in MAPPINGS.values() if v[0] == "exactMatch")
    broad = sum(1 for v in MAPPINGS.values() if v[0] == "broadMatch")
    print(f"  exactMatch: {exact}")
    print(f"  broadMatch: {broad}")


if __name__ == "__main__":
    main()
