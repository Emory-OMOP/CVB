#!/usr/bin/env python3
"""Enrich unmappable_items.csv with metadata from master extract and custom lists.

Joins the FCA-classified unmappable items with template/group/value-type metadata
from the master extract and custom list values, producing a single enriched CSV
for the clinical reasoning review pass.

Usage:
    uv run python -m fca.enrich_unmappable
"""
import csv
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
UNMAPPABLE = BASE / "Mappings" / "unmappable_items.csv"
MASTER = BASE / "raw_for_fca" / "fca_master_extract__v20260304.csv"
CUSTOM_LISTS = BASE / "raw_for_fca" / "fca_custom_lists__v20260304.csv"
OUTPUT = BASE / "Mappings" / "unmappable_enriched.csv"

VAL_TYPE_MAP = {
    "1": "numeric", "2": "string", "3": "numeric", "4": "category",
    "5": "date", "6": "time", "7": "datetime", "8": "custom_list",
    "9": "multi_select", "10": "text", "11": "checkbox", "12": "panel",
}


def main():
    # Load custom lists: row_id -> list of values
    print("Loading custom lists...")
    custom_lists = defaultdict(list)
    with open(CUSTOM_LISTS) as f:
        for row in csv.DictReader(f):
            custom_lists[row["id"]].append(row["cust_list_value"])

    # Load master extract: row_id -> metadata
    print("Loading master extract...")
    row_meta = defaultdict(lambda: {
        "val_type": "", "units": "", "min_val": "", "max_val": "",
        "templates": set(), "groups": set(),
    })
    with open(MASTER) as f:
        for row in csv.DictReader(f):
            rid = row["row_id"]
            meta = row_meta[rid]
            vt = row.get("VAL_TYPE_C", "")
            meta["val_type"] = VAL_TYPE_MAP.get(vt, vt)
            meta["units"] = row.get("UNITS", "") or ""
            meta["min_val"] = row.get("MINVALUE", "") or ""
            meta["max_val"] = row.get("MAX_VAL", "") or ""
            meta["templates"].add(row.get("TEMPLATE_NAME", ""))
            meta["groups"].add(row.get("group_name", ""))

    # Enrich and write
    print("Writing enriched CSV...")
    with open(UNMAPPABLE) as fin, open(OUTPUT, "w", newline="") as fout:
        reader = csv.DictReader(fin)
        writer = csv.writer(fout)
        writer.writerow([
            "source_concept_code", "source_description", "fca_concept_id",
            "reason", "intent", "val_type", "units", "min_val", "max_val",
            "custom_list_values", "template_names", "group_names", "n_templates",
        ])
        for row in reader:
            rid = row["source_concept_code"]
            meta = row_meta[rid]
            templates = sorted(meta["templates"] - {""})
            groups = sorted(meta["groups"] - {""})
            cl_values = custom_lists.get(rid, [])
            writer.writerow([
                rid, row["source_description"], row["fca_concept_id"],
                row["reason"], row.get("intent", ""),
                meta["val_type"], meta["units"], meta["min_val"], meta["max_val"],
                "|".join(cl_values) if cl_values else "",
                "|".join(templates), "|".join(groups), len(templates),
            ])

    print(f"Done. {OUTPUT}")


if __name__ == "__main__":
    main()
