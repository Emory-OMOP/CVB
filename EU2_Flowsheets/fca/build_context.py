"""Build the FCA formal context K = (G, M, I) from Clarity CSV exports.

Transforms raw CSVs into:
- G: set of objects (FLO_MEAS_IDs)
- M: set of binary attributes
- I: incidence relation (sparse matrix)

Input files:
    fca_master_extract.csv  - Template/group/row hierarchy with metadata
    fca_custom_lists.csv    - Custom list values per row

Output files:
    fca_context.json  - G (object list), M (attribute list), metadata
    fca_incidence.npz - scipy sparse CSR matrix (|G| × |M|)

Usage:
    python -m fca.build_context \\
        --master EU2_Flowsheets/raw_for_fca/fca_master_extract.csv \\
        --custom-lists EU2_Flowsheets/raw_for_fca/fca_custom_lists.csv \\
        --output-dir EU2_Flowsheets/raw_for_fca/
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import sparse

from .name_parser import parse_display_name
from .template_classifier import classify_template
from .value_domain_classifier import classify_value_domain
from .constants import VAL_TYPE_LABELS


def load_master_extract(path: Path) -> list[dict]:
    """Load the master extract CSV into a list of row dicts."""
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        return list(reader)


def load_custom_lists(path: Path) -> dict[str, list[str]]:
    """Load custom lists CSV, grouped by flowsheet row ID.

    Supports the actual Clarity IP_FLO_CUSTOM_LIST schema:
        id, line, cust_list_abbr, cust_list_value, cust_list_map_value, ...

    Returns dict mapping flowsheet ID (str) → list of custom list values.
    """
    result: dict[str, list[str]] = defaultdict(list)
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Clarity column: 'id' (the FLO_MEAS_ID)
            flo_id = row.get('id', '').strip()
            # Clarity column: 'cust_list_value' (display text)
            value = row.get('cust_list_value', '').strip()
            if flo_id and value:
                result[flo_id].append(value)
    return dict(result)


def _safe_int(val: str | None) -> int | None:
    """Convert string to int, returning None on failure."""
    if val is None or val == '':
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def _safe_float(val: str | None) -> float | None:
    """Convert string to float, returning None on failure."""
    if val is None or val == '':
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def build_context(
    master_rows: list[dict],
    custom_lists: dict[str, list[str]] | None = None,
) -> tuple[list[str], list[str], sparse.csr_matrix, dict]:
    """Build the formal context from extracted data.

    Args:
        master_rows: Rows from fca_master_extract.csv (or template_lines.csv).
        custom_lists: Optional dict of FLO_MEAS_ID → custom list values.

    Returns:
        (objects, attributes, incidence_matrix, metadata)
        - objects: list of FLO_MEAS_ID strings (G)
        - attributes: list of attribute names (M)
        - incidence_matrix: sparse CSR matrix (|G| × |M|)
        - metadata: dict with per-object details for downstream use
    """
    if custom_lists is None:
        custom_lists = {}

    # --- Deduplicate rows by FLO_MEAS_ID ---
    # The master extract has one row per template-group-row combo.
    # An item can appear in multiple templates/groups.
    # We collect ALL template/group memberships per item.
    item_data: dict[str, dict] = {}
    item_templates: dict[str, set[str]] = defaultdict(set)
    item_groups: dict[str, set[str]] = defaultdict(set)

    # Detect column schema: full master extract vs partial template_lines
    sample = master_rows[0] if master_rows else {}
    has_full_schema = 'row_id' in sample or 'group_id' in sample

    for row in master_rows:
        if has_full_schema:
            flo_id = str(row.get('row_id', '')).strip()
            disp_name = row.get('row_name', '').strip()
        else:
            flo_id = str(row.get('FLO_MEAS_ID', '')).strip()
            disp_name = row.get('DISP_NAME', '').strip()

        if not flo_id:
            continue

        template_name = row.get('TEMPLATE_NAME', '').strip()
        group_name = row.get('group_name', row.get('DISPLAY_NAME', '')).strip()

        # Store first occurrence's metadata (row-level attrs are stable)
        if flo_id not in item_data:
            item_data[flo_id] = {
                'disp_name': disp_name,
                'val_type_c': _safe_int(row.get('VAL_TYPE_C')),
                'row_typ_c': _safe_int(row.get('ROW_TYP_C')),
                'units': row.get('UNITS', '').strip(),
                'minvalue': _safe_float(row.get('MINVALUE')),
                'max_val': _safe_float(row.get('MAX_VAL')),
                'intake_typ_c': _safe_int(row.get('INTAKE_TYP_C')),
                'output_typ_c': _safe_int(row.get('OUTPUT_TYP_C')),
                'min_age': _safe_float(row.get('MIN_AGE')),
                'max_age': _safe_float(row.get('MAX_AGE')),
                'sex_c': _safe_int(row.get('SEX_C')),
            }

        if template_name:
            item_templates[flo_id].add(template_name)
        if group_name:
            item_groups[flo_id].add(group_name)

    # --- Build attribute set ---
    # Collect all unique attribute values first, then assign indices.
    attribute_set: dict[str, int] = {}  # attr_name → column index

    def _get_attr_idx(attr: str) -> int:
        if attr not in attribute_set:
            attribute_set[attr] = len(attribute_set)
        return attribute_set[attr]

    # Pre-scan to discover all attribute values
    objects = sorted(item_data.keys())
    obj_idx = {flo_id: i for i, flo_id in enumerate(objects)}

    # Build COO data for sparse matrix
    row_indices: list[int] = []
    col_indices: list[int] = []

    for flo_id in objects:
        data = item_data[flo_id]
        i = obj_idx[flo_id]

        def _add(attr: str) -> None:
            row_indices.append(i)
            col_indices.append(_get_attr_idx(attr))

        # --- val_type attribute family ---
        vt = data['val_type_c']
        vt_label = VAL_TYPE_LABELS.get(vt, f'val_type_{vt}')
        _add(f'val_type:{vt_label}')

        # --- unit attribute ---
        units = data['units']
        if units:
            # Normalize common unit spellings
            u_norm = units.strip().lower()
            _add(f'unit:{u_norm}')

        # --- has_range ---
        if data['minvalue'] is not None or data['max_val'] is not None:
            _add('has_range')

        # --- intake / output ---
        if data['intake_typ_c'] is not None:
            _add('is_intake')
        if data['output_typ_c'] is not None:
            _add('is_output')

        # --- age/sex filters ---
        if data['min_age'] is not None or data['max_age'] is not None:
            _add('has_age_filter')
        if data['sex_c'] is not None:
            _add('has_sex_filter')

        # --- template category attributes ---
        for tname in item_templates.get(flo_id, set()):
            cat = classify_template(tname)
            _add(f'template_cat:{cat}')

        # --- group name ---
        # NOT included as FCA attributes — too many unique values
        # (thousands) which explodes the incidence matrix.
        # Group names are preserved in metadata for downstream labeling.

        # --- DISP_NAME parsed attributes ---
        parsed = parse_display_name(data['disp_name'])

        if parsed['body_site']:
            _add(f'body_site:{parsed["body_site"]}')
        if parsed['laterality']:
            _add(f'laterality:{parsed["laterality"]}')
        if parsed['assessment']:
            _add(f'assessment:{parsed["assessment"]}')
        if parsed.get('method'):
            _add(f'method:{parsed["method"]}')
        if parsed.get('temporal'):
            _add(f'temporal:{parsed["temporal"]}')

        # --- value domain from custom lists ---
        if flo_id in custom_lists:
            domain = classify_value_domain(custom_lists[flo_id])
            if domain != 'unclassified':
                _add(f'value_domain:{domain}')

    # --- Build sparse matrix ---
    n_objects = len(objects)
    n_attributes = len(attribute_set)
    ones = np.ones(len(row_indices), dtype=np.int8)
    incidence = sparse.csr_matrix(
        (ones, (row_indices, col_indices)),
        shape=(n_objects, n_attributes),
        dtype=np.int8,
    )

    # Attribute list ordered by index
    attributes = [''] * n_attributes
    for attr, idx in attribute_set.items():
        attributes[idx] = attr

    # Build metadata for downstream use
    metadata = {
        'n_objects': n_objects,
        'n_attributes': n_attributes,
        'n_nonzero': int(incidence.nnz),
        'density': round(incidence.nnz / (n_objects * n_attributes), 4)
        if n_objects * n_attributes > 0
        else 0.0,
        'item_data': {flo_id: item_data[flo_id] for flo_id in objects},
        'item_templates': {
            flo_id: sorted(item_templates.get(flo_id, set()))
            for flo_id in objects
        },
        'item_groups': {
            flo_id: sorted(item_groups.get(flo_id, set()))
            for flo_id in objects
        },
    }

    return objects, attributes, incidence, metadata


def save_context(
    objects: list[str],
    attributes: list[str],
    incidence: sparse.csr_matrix,
    metadata: dict,
    output_dir: Path,
) -> None:
    """Save formal context to disk.

    Writes:
        fca_context.json - G, M, stats (NOT the full incidence — too large)
        fca_incidence.npz - sparse matrix
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save context metadata (without the full item_data for JSON size)
    context_json = {
        'objects': objects,
        'attributes': attributes,
        'n_objects': metadata['n_objects'],
        'n_attributes': metadata['n_attributes'],
        'n_nonzero': metadata['n_nonzero'],
        'density': metadata['density'],
    }
    with open(output_dir / 'fca_context.json', 'w') as f:
        json.dump(context_json, f, indent=2)

    # Save sparse incidence matrix
    sparse.save_npz(output_dir / 'fca_incidence.npz', incidence)

    # Save full metadata separately (includes item_data for downstream)
    with open(output_dir / 'fca_metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2, default=str)

    print(f"Context saved: {metadata['n_objects']} objects × "
          f"{metadata['n_attributes']} attributes, "
          f"density={metadata['density']:.4f}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description='Build FCA formal context from Clarity CSV exports'
    )
    parser.add_argument(
        '--master', required=True, type=Path,
        help='Path to fca_master_extract.csv (or template_lines.csv)'
    )
    parser.add_argument(
        '--custom-lists', type=Path, default=None,
        help='Path to fca_custom_lists.csv (optional)'
    )
    parser.add_argument(
        '--output-dir', required=True, type=Path,
        help='Directory for output files'
    )
    args = parser.parse_args(argv)

    print(f"Loading master extract: {args.master}")
    master_rows = load_master_extract(args.master)
    print(f"  Loaded {len(master_rows)} rows")

    custom_lists: dict[str, list[str]] = {}
    if args.custom_lists and args.custom_lists.exists():
        print(f"Loading custom lists: {args.custom_lists}")
        custom_lists = load_custom_lists(args.custom_lists)
        print(f"  Loaded lists for {len(custom_lists)} items")

    print("Building formal context...")
    objects, attributes, incidence, metadata = build_context(
        master_rows, custom_lists
    )

    save_context(objects, attributes, incidence, metadata, args.output_dir)


if __name__ == '__main__':
    main()
