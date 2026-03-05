#!/usr/bin/env python3
"""Apply batch 4 confirmed OMOP concept mappings to EU2_Flowsheets mapping.csv.

Covers: neurological assessments (LOC, pupil, motor response, sensation,
grip strength, facial symmetry), respiratory assessments (breath sounds,
respiratory pattern, cough), cardiac assessments (cardiac rhythm, heart sounds,
radial/pedal pulses), skin/integumentary (skin integrity, turgor, condition,
edema, cyanosis), body position, urine appearance, drainage, fall risk scores,
cerebral oximetry, oxygenation index, bowel assessments, and BP metadata.

Mappings verified via OHDSI vocab MCP (DuckDB Athena v5 vocabulary).
Run from repo root:
    python apps/mapping-contributor/apply_batch_mappings_04.py
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
    # === Neurological — Level of Consciousness / Orientation ===
    "301860": ("broadMatch", "0.8", "21494983", "Level of consciousness",
               "LOINC", "Observation",
               "Level of Consciousness → LOINC 80288-4 (nursing LOC assessment → general LOC observable)"),
    "10701000109": ("broadMatch", "0.8", "4290243", "Level of consciousness",
                    "SNOMED", "Observation",
                    "Consciousness → SNOMED 6942003 Level of consciousness"),

    # === Neurological — Pupil Assessments ===
    "301920": ("broadMatch", "0.7", "4010421", "Pupil reaction to light",
               "SNOMED", "Observation",
               "R Pupil Reaction → SNOMED 113147002 (right-specific → general pupil light reaction)"),
    "301900": ("broadMatch", "0.7", "4010421", "Pupil reaction to light",
               "SNOMED", "Observation",
               "L Pupil Reaction → SNOMED 113147002 (left-specific → general pupil light reaction)"),
    "3040101192": ("exactMatch", "0.9", "21494990", "Pupil shape [Shape] of Right pupil",
                   "LOINC", "Measurement",
                   "R Pupil Shape → LOINC 80312-2 Pupil shape of Right pupil"),
    "3040101193": ("exactMatch", "0.9", "21494473", "Pupil shape [Shape] of Left pupil",
                   "LOINC", "Measurement",
                   "L Pupil Shape → LOINC 80311-4 Pupil shape of Left pupil"),

    # === Neurological — Facial Symmetry ===
    "3040102801": ("exactMatch", "0.9", "4086827", "Facial symmetry",
                   "SNOMED", "Observation",
                   "Facial Symmetry → SNOMED 248172007 Facial symmetry"),

    # === Neurological — Motor Response (extremity-specific → general) ===
    "302000": ("broadMatch", "0.7", "4237719", "Motor response",
               "SNOMED", "Observation",
               "RLE Motor Response → SNOMED 363850001 Motor response (right lower extremity → general)"),
    "301980": ("broadMatch", "0.7", "4237719", "Motor response",
               "SNOMED", "Observation",
               "RUE Motor Response → SNOMED 363850001 Motor response (right upper extremity → general)"),
    "301960": ("broadMatch", "0.7", "4237719", "Motor response",
               "SNOMED", "Observation",
               "LLE Motor Response → SNOMED 363850001 Motor response (left lower extremity → general)"),
    "301940": ("broadMatch", "0.7", "4237719", "Motor response",
               "SNOMED", "Observation",
               "LUE Motor Response → SNOMED 363850001 Motor response (left upper extremity → general)"),

    # === Neurological — Sensation (extremity-specific → general) ===
    "302010": ("broadMatch", "0.7", "4287782", "Somatic sensation",
               "SNOMED", "Observation",
               "RLE Sensation → SNOMED 397725003 Somatic sensation (right lower extremity → general)"),
    "301990": ("broadMatch", "0.7", "4287782", "Somatic sensation",
               "SNOMED", "Observation",
               "RUE Sensation → SNOMED 397725003 Somatic sensation (right upper extremity → general)"),
    "301970": ("broadMatch", "0.7", "4287782", "Somatic sensation",
               "SNOMED", "Observation",
               "LLE Sensation → SNOMED 397725003 Somatic sensation (left lower extremity → general)"),
    "301950": ("broadMatch", "0.7", "4287782", "Somatic sensation",
               "SNOMED", "Observation",
               "LUE Sensation → SNOMED 397725003 Somatic sensation (left upper extremity → general)"),

    # === Neurological — Grip Strength ===
    "3040101162": ("broadMatch", "0.8", "44805438", "Grip strength of right hand",
                   "SNOMED", "Measurement",
                   "R Hand Grasp → SNOMED 786451000000107 Grip strength of right hand"),
    "3040101163": ("broadMatch", "0.8", "44805437", "Grip strength of left hand",
                   "SNOMED", "Measurement",
                   "L Hand Grasp → SNOMED 786441000000107 Grip strength of left hand"),

    # === Neurological — Speech ===
    "301870": ("broadMatch", "0.7", "21494457", "Speech clarity",
               "LOINC", "Observation",
               "Speech → LOINC 80295-9 Speech clarity (generic speech assessment → clarity)"),

    # === Respiratory Assessments ===
    "302570": ("exactMatch", "0.9", "4150612", "Respiratory pattern",
               "SNOMED", "Observation",
               "Respiratory Pattern → SNOMED 278907009 Respiratory pattern"),
    "302390": ("broadMatch", "0.8", "42869827", "Breath sounds",
               "LOINC", "Observation",
               "Bilateral Breath Sounds → LOINC 72072-2 Breath sounds (bilateral → general)"),
    "302590": ("broadMatch", "0.7", "4137801", "Coughing",
               "SNOMED", "Observation",
               "Cough → SNOMED 263731006 Coughing (cough assessment → coughing observable)"),
    "450420": ("exactMatch", "0.9", "4146379", "Cough reflex",
               "SNOMED", "Observation",
               "Cough Reflex → SNOMED 34606001 Cough reflex"),

    # === Cardiac Assessments ===
    "301320": ("broadMatch", "0.8", "4091457", "Cardiac rhythm type",
               "SNOMED", "Observation",
               "Cardiac Rhythm → SNOMED 251149006 Cardiac rhythm type"),
    "3040100446": ("exactMatch", "0.9", "21494971", "Heart sounds",
                   "LOINC", "Measurement",
                   "Heart Sounds → LOINC 80276-9 Heart sounds"),

    # === Vascular — Pulses ===
    "303210": ("broadMatch", "0.8", "4277123", "Radial pulse",
               "SNOMED", "Measurement",
               "Right Radial Pulse → SNOMED 65452004 Radial pulse (right-specific → general)"),
    "303270": ("broadMatch", "0.8", "4277123", "Radial pulse",
               "SNOMED", "Measurement",
               "Left Radial Pulse → SNOMED 65452004 Radial pulse (left-specific → general)"),
    "303350": ("broadMatch", "0.8", "4225511", "Dorsalis pedis pulse",
               "SNOMED", "Measurement",
               "Right Pedal Pulse → SNOMED 421811005 Dorsalis pedis pulse (right-specific → general)"),
    "303420": ("broadMatch", "0.8", "4225511", "Dorsalis pedis pulse",
               "SNOMED", "Measurement",
               "Left Pedal Pulse → SNOMED 421811005 Dorsalis pedis pulse (left-specific → general)"),

    # === Skin / Integumentary ===
    "306470": ("exactMatch", "0.9", "21492838", "Skin integrity",
               "LOINC", "Measurement",
               "Skin Integrity → LOINC 80344-5 Skin integrity"),
    "330130": ("exactMatch", "0.9", "4132134", "Skin turgor",
               "SNOMED", "Observation",
               "Skin Turgor → SNOMED 26669000 Skin turgor"),
    "303450": ("broadMatch", "0.7", "4223743", "Skin condition",
               "SNOMED", "Observation",
               "Skin Condition/Temp → SNOMED 422000003 Skin condition (source includes temp component)"),

    # === Body Position / Patient Position ===
    "304000798": ("exactMatch", "0.9", "4287468", "Body position",
                  "SNOMED", "Observation",
                  "Body Position → SNOMED 397155001 Body position"),
    "5203010101": ("broadMatch", "0.8", "4156503", "Patient position finding",
                   "SNOMED", "Observation",
                   "Patient Position → SNOMED 272525001 Patient position finding"),

    # === Genitourinary ===
    "304150": ("exactMatch", "0.9", "4143063", "Urine appearance",
               "SNOMED", "Measurement",
               "Urine Appearance → SNOMED 267065001 Urine appearance"),

    # === Gastrointestinal ===
    "302990": ("exactMatch", "0.9", "4337265", "Bowel sounds",
               "SNOMED", "Observation",
               "Bowel Sounds (All Quadrants) → SNOMED 87042004 Bowel sounds"),
    "3040103156": ("broadMatch", "0.8", "3021028", "Bowel incontinence [CCC]",
                   "LOINC", "Observation",
                   "Bowel Incontinence → LOINC 28146-9 Bowel incontinence [CCC]"),

    # === Wound / Drainage ===
    # REMOVED: Drainage Amount (303770) → "Drainage amount of Wound" — source is
    # generic drainage (surgical drain, chest tube, JP) not wound-specific.

    # === Edema / Cyanosis ===
    "3040100965": ("exactMatch", "0.9", "3045290", "Edema",
                   "LOINC", "Observation",
                   "Edema → LOINC 44966-0 Edema"),
    "3040100223": ("broadMatch", "0.7", "44807058", "O/E - cyanosis",
                   "SNOMED", "Observation",
                   "Cyanosis → SNOMED 794581000000108 O/E - cyanosis (assessment → finding)"),

    # === Blood Pressure Metadata ===
    "301310": ("exactMatch", "0.9", "3003798", "Blood pressure method",
               "LOINC", "Observation",
               "BP Method → LOINC 8357-6 Blood pressure method"),

    # === Pain ===
    # REMOVED: Pain Location (301090) → "Pain trigger point [Anatomy]" — trigger
    # points are myofascial-specific; source records general body site of pain.

    # === Cerebral Oximetry ===
    "6819": ("broadMatch", "0.7", "4262311", "Transcranial cerebral oximetry",
             "SNOMED", "Measurement",
             "Cerebral Oximeter Left Baseline → SNOMED 397832002 Transcranial cerebral oximetry (left baseline → general)"),
    "6821": ("broadMatch", "0.7", "4262311", "Transcranial cerebral oximetry",
             "SNOMED", "Measurement",
             "Cerebral Oximeter Right Baseline → SNOMED 397832002 Transcranial cerebral oximetry (right baseline → general)"),

    # === Oxygenation Index ===
    "3041008000": ("broadMatch", "0.8", "37173614", "Oxygenation index percent in blood",
                   "SNOMED", "Measurement",
                   "Oxygen Index → SNOMED 6301000237104 Oxygenation index percent in blood"),

    # === Fall Risk Scores ===
    "3040105119": ("broadMatch", "0.7", "43533853", "Fall risk assessment",
                   "LOINC", "Observation",
                   "Fall Risk Calculated Score → LOINC 73830-2 Fall risk assessment (calculated score → assessment)"),
    "3040104747": ("broadMatch", "0.7", "43533853", "Fall risk assessment",
                   "LOINC", "Observation",
                   "Hester Davis Fall Risk Total → LOINC 73830-2 Fall risk assessment (proprietary total → general)"),
    "3042500049": ("broadMatch", "0.7", "43533853", "Fall risk assessment",
                   "LOINC", "Observation",
                   "Hester Davis Fall Risk → LOINC 73830-2 Fall risk assessment (proprietary scale → general)"),
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

    # Apply mappings (only to rows currently marked noMatch)
    updated = 0
    skipped = 0
    for row in rows:
        code = row.get("source_concept_code", "").strip()
        if code in MAPPINGS:
            # Skip if already has a real mapping (not noMatch)
            current_pred = row.get("predicate_id", "").strip()
            if current_pred and current_pred != "noMatch":
                skipped += 1
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
    print(f"Skipped {skipped} rows (already mapped).")
    print(f"Mappings defined: {len(MAPPINGS)}, matched: {updated}")

    # Summary by predicate
    exact = sum(1 for v in MAPPINGS.values() if v[0] == "exactMatch")
    broad = sum(1 for v in MAPPINGS.values() if v[0] == "broadMatch")
    print(f"  exactMatch: {exact}")
    print(f"  broadMatch: {broad}")


if __name__ == "__main__":
    main()
