#!/usr/bin/env python3
"""Apply batch 5 confirmed OMOP concept mappings to EU2_Flowsheets mapping.csv.

Covers: corneal/Babinski reflexes, muscle tone, posterior tibial pulses,
capillary refill (4 extremities), extremity edema (4 + generalized),
cerebral oximetry (continuous), breath sounds (L/R/general), swallowing,
pacemaker, pain frequency/onset, wound status, functional status,
and additional duplicate source codes for already-mapped concepts.

Mappings verified via OHDSI vocab MCP (DuckDB Athena v5 vocabulary).
Run from repo root:
    python apps/mapping-contributor/apply_batch_mappings_05.py
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
    # === Neurological — Reflexes ===
    "450990": ("broadMatch", "0.7", "4011079", "Corneal reflex",
               "SNOMED", "Observation",
               "R Corneal Reflex → SNOMED 112219002 Corneal reflex (right-specific → general)"),
    "450410": ("broadMatch", "0.7", "4011079", "Corneal reflex",
               "SNOMED", "Observation",
               "L Corneal Reflex → SNOMED 112219002 Corneal reflex (left-specific → general)"),
    "3040103168": ("broadMatch", "0.8", "3017443", "Babinski reflex",
                   "LOINC", "Measurement",
                   "R Babinski Reflex → LOINC 32385-7 Babinski reflex (right-specific → general)"),
    "3040103169": ("broadMatch", "0.8", "3017443", "Babinski reflex",
                   "LOINC", "Measurement",
                   "L Babinski Reflex → LOINC 32385-7 Babinski reflex (left-specific → general)"),

    # === Neurological — Muscle Tone ===
    "12017": ("broadMatch", "0.7", "4289445", "Muscle tone",
              "SNOMED", "Observation",
              "Resting Tone (Palpate) → SNOMED 6918002 Muscle tone (palpation assessment → general)"),

    # === Vascular — Posterior Tibial Pulses ===
    "303340": ("broadMatch", "0.8", "4222862", "Posterior tibial pulse",
               "SNOMED", "Measurement",
               "Right Posterior Tibial Pulse → SNOMED 421568004 Posterior tibial pulse (right → general)"),
    "303410": ("broadMatch", "0.8", "4222862", "Posterior tibial pulse",
               "SNOMED", "Measurement",
               "Left Posterior Tibial Pulse → SNOMED 421568004 Posterior tibial pulse (left → general)"),

    # === Capillary Refill (extremity-specific → general) ===
    "303290": ("broadMatch", "0.8", "3045676", "Capillary refill [Time]",
               "LOINC", "Measurement",
               "RLE Capillary Refill → LOINC 44971-0 Capillary refill [Time] (RLE → general)"),
    "303360": ("broadMatch", "0.8", "3045676", "Capillary refill [Time]",
               "LOINC", "Measurement",
               "LLE Capillary Refill → LOINC 44971-0 Capillary refill [Time] (LLE → general)"),
    "303170": ("broadMatch", "0.8", "3045676", "Capillary refill [Time]",
               "LOINC", "Measurement",
               "RUE Capillary Refill → LOINC 44971-0 Capillary refill [Time] (RUE → general)"),
    "303230": ("broadMatch", "0.8", "3045676", "Capillary refill [Time]",
               "LOINC", "Measurement",
               "LUE Capillary Refill → LOINC 44971-0 Capillary refill [Time] (LUE → general)"),

    # === Edema (extremity-specific → general) ===
    "303140": ("broadMatch", "0.7", "3045290", "Edema",
               "LOINC", "Observation",
               "RLE Edema → LOINC 44966-0 Edema (right lower extremity → general)"),
    "303160": ("broadMatch", "0.7", "3045290", "Edema",
               "LOINC", "Observation",
               "LLE Edema → LOINC 44966-0 Edema (left lower extremity → general)"),
    "303130": ("broadMatch", "0.7", "3045290", "Edema",
               "LOINC", "Observation",
               "RUE Edema → LOINC 44966-0 Edema (right upper extremity → general)"),
    "303150": ("broadMatch", "0.7", "3045290", "Edema",
               "LOINC", "Observation",
               "LUE Edema → LOINC 44966-0 Edema (left upper extremity → general)"),
    "303020": ("exactMatch", "0.9", "3045290", "Edema",
               "LOINC", "Observation",
               "Generalized Edema → LOINC 44966-0 Edema"),

    # === Cerebral Oximetry (continuous, not baseline) ===
    "6818": ("broadMatch", "0.8", "4262311", "Transcranial cerebral oximetry",
             "SNOMED", "Measurement",
             "Cerebral Oximeter Right → SNOMED 397832002 Transcranial cerebral oximetry (right → general)"),
    "6817": ("broadMatch", "0.8", "4262311", "Transcranial cerebral oximetry",
             "SNOMED", "Measurement",
             "Cerebral Oximeter Left → SNOMED 397832002 Transcranial cerebral oximetry (left → general)"),

    # === Respiratory — Breath Sounds (additional codes) ===
    "3040111689": ("exactMatch", "0.9", "42869827", "Breath sounds",
                   "LOINC", "Observation",
                   "Breath Sounds → LOINC 72072-2 Breath sounds"),
    "302400": ("broadMatch", "0.8", "42869827", "Breath sounds",
               "LOINC", "Observation",
               "R Breath Sounds → LOINC 72072-2 Breath sounds (right → general)"),
    "302410": ("broadMatch", "0.8", "42869827", "Breath sounds",
               "LOINC", "Observation",
               "L Breath Sounds → LOINC 72072-2 Breath sounds (left → general)"),

    # === Swallowing ===
    "700530": ("broadMatch", "0.8", "4225856", "Swallowing status",
               "SNOMED", "Observation",
               "Swallow → SNOMED 405035003 Swallowing status"),

    # === Cardiac — Pacemaker ===
    "2281": ("broadMatch", "0.7", "4185147", "Cardiac pacemaker observable",
             "SNOMED", "Observation",
             "Pacemaker → SNOMED 413754003 Cardiac pacemaker observable (flowsheet → pacemaker assessment)"),

    # === Pain ===
    "400350": ("broadMatch", "0.7", "3045901", "Pain frequency [Minimum Data Set]",
               "LOINC", "Observation",
               "Pain Frequency → LOINC 45710-1 Pain frequency [MDS] (generic → MDS instrument)"),
    # REMOVED: Pain Onset (400340) → "Speed of pain onset" — source captures *when*
    # pain started; target is *how quickly* it developed. Different concepts.

    # === Wound ===
    "703210": ("exactMatch", "0.9", "3042590", "Wound status",
               "LOINC", "Measurement",
               "Wound Status → LOINC 39123-5 Wound status"),

    # === Functional Status ===
    "364190": ("broadMatch", "0.8", "40757653", "Functional status",
               "LOINC", "Observation",
               "Functional Status → LOINC 54522-8 Functional status"),

    # === Duplicate source codes for concepts mapped in batch 4 ===
    "3041210115": ("broadMatch", "0.7", "4287782", "Somatic sensation",
                   "SNOMED", "Observation",
                   "RLE Sensation (alt code) → SNOMED 397725003 Somatic sensation (right lower extremity → general)"),
    "3042400005": ("broadMatch", "0.8", "4156503", "Patient position finding",
                   "SNOMED", "Observation",
                   "Patient Position (alt code) → SNOMED 272525001 Patient position finding"),
}


def main():
    csv_path = os.path.join(REPO_ROOT, "EU2_Flowsheets", "Mappings", "mapping.csv")

    # Read
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        raw_headers = list(reader.fieldnames)
        rows = list(reader)

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
