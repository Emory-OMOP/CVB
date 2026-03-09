"""Transform FCA outputs into CVB-ready mapping.csv.

Reads the three FCA output files (atomic_items.csv, compositional_mapping.csv,
unmappable_items.csv) and produces a single mapping.csv consumable by the
CVB Builder pipeline.

Compositional items (B) produce multi-row entries:
  - Row 1: relationship_id='Maps to', target=assessment_concept_id
  - Row 2 (if qualifier): relationship_id='Has finding site', target=qualifier_concept_id

Atomic items (A) are checked in priority order:
  1. atomic_review.csv: decision='map' → use reviewed mapping (with qualifiers)
  2. atomic_review.csv: decision='skip'/'flag' → noMatch
  3. existing mapping.csv: preserve prior mapping
  4. FCA suggested_concept_id: use pre-coordinated concept
  5. Otherwise: noMatch placeholder

Unmappable items (C) are checked against clinical_review.csv:
  - decision='map': rescued with OMOP mapping from clinical review
  - decision='skip' or absent: emitted as noMatch

Usage:
    python -m fca.build_mapping_csv \
        --compositional Mappings/compositional_mapping.csv \
        --atomic Mappings/atomic_items.csv \
        --unmappable Mappings/unmappable_items.csv \
        --existing Mappings/mapping.csv \
        --clinical-review Mappings/clinical_review.csv \
        --atomic-review Mappings/atomic_review.csv \
        --output Mappings/mapping.csv

    # Self-test:
    python -m fca.build_mapping_csv --test
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path


VOCAB_ID = 'EU2_Flowsheets'
CONCEPT_CLASS = 'Suppl Concept'

# CVB mapping.csv pipeline columns (first 21 — workspace columns are stripped)
OUTPUT_HEADERS = [
    'source_concept_code',
    'source_concept_id',
    'source_vocabulary_id',
    'source_domain',
    'source_concept_class_id',
    'source_description',
    'source_description_synonym',
    'relationship_id',
    'predicate_id',
    'confidence',
    'target_concept_id',
    'target_concept_name',
    'target_vocabulary_id',
    'target_domain_id',
    'mapping_justification',
    'mapping_tool',
    'author_label',
    'review_date',
    'reviewer_name',
    'reviewer_specialty',
    'status',
]


def _empty_row(code: str, description: str) -> dict:
    """Create a row template with common fields."""
    return {
        'source_concept_code': code,
        'source_concept_id': 0,
        'source_vocabulary_id': VOCAB_ID,
        'source_domain': '',
        'source_concept_class_id': CONCEPT_CLASS,
        'source_description': description,
        'source_description_synonym': '',
        'relationship_id': '',
        'predicate_id': '',
        'confidence': 0,
        'target_concept_id': 0,
        'target_concept_name': '',
        'target_vocabulary_id': '',
        'target_domain_id': '',
        'mapping_justification': '',
        'mapping_tool': '',
        'author_label': '',
        'review_date': '',
        'reviewer_name': '',
        'reviewer_specialty': '',
        'status': 'pending',
    }


def load_compositional(path: Path) -> list[dict]:
    """Load compositional_mapping.csv and expand to multi-row CVB format."""
    rows = []
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        for r in reader:
            code = r['source_concept_code']
            desc = r['source_description']
            assessment_id = int(r['assessment_concept_id'])
            assessment_name = r['assessment_concept_name']
            qualifier_id = int(r['qualifier_concept_id'])
            qualifier_name = r['qualifier_concept_name']
            method_qualifier_id = int(r.get('method_qualifier_concept_id', 0) or 0)
            method_qualifier_name = r.get('method_qualifier_concept_name', '')
            temporal_qualifier_id = int(r.get('temporal_qualifier_concept_id', 0) or 0)
            temporal_qualifier_name = r.get('temporal_qualifier_concept_name', '')
            predicate = r['predicate_id']
            confidence = float(r['confidence'])
            justification = r['mapping_justification']

            # Row 1: Maps to → assessment concept
            row1 = _empty_row(code, desc)
            row1['source_domain'] = 'Observation'
            row1['relationship_id'] = 'Maps to'
            row1['predicate_id'] = predicate
            row1['confidence'] = confidence
            row1['target_concept_id'] = assessment_id
            row1['target_concept_name'] = assessment_name
            row1['target_vocabulary_id'] = 'SNOMED'
            row1['target_domain_id'] = 'Observation'
            row1['mapping_justification'] = justification
            row1['mapping_tool'] = ''
            row1['author_label'] = 'FCA-pipeline'
            rows.append(row1)

            # Row 2 (if qualifier): Has finding site → qualifier concept
            if qualifier_id and qualifier_id != 0:
                row2 = _empty_row(code, desc)
                row2['source_domain'] = 'Observation'
                row2['relationship_id'] = 'Has finding site'
                row2['predicate_id'] = predicate
                row2['confidence'] = confidence
                row2['target_concept_id'] = qualifier_id
                row2['target_concept_name'] = qualifier_name
                row2['target_vocabulary_id'] = 'SNOMED'
                row2['target_domain_id'] = 'Observation'
                row2['mapping_justification'] = justification
                row2['mapping_tool'] = ''
                row2['author_label'] = 'FCA-pipeline'
                rows.append(row2)

            # Row 3 (if method qualifier): Has method → method concept
            if method_qualifier_id and method_qualifier_id != 0:
                row3 = _empty_row(code, desc)
                row3['source_domain'] = 'Observation'
                row3['relationship_id'] = 'Has method'
                row3['predicate_id'] = predicate
                row3['confidence'] = confidence
                row3['target_concept_id'] = method_qualifier_id
                row3['target_concept_name'] = method_qualifier_name
                row3['target_vocabulary_id'] = 'SNOMED'
                row3['target_domain_id'] = 'Observation'
                row3['mapping_justification'] = justification
                row3['mapping_tool'] = ''
                row3['author_label'] = 'FCA-pipeline'
                rows.append(row3)

            # Row 4 (if temporal qualifier): Has temporal context → temporal concept
            if temporal_qualifier_id and temporal_qualifier_id != 0:
                row4 = _empty_row(code, desc)
                row4['source_domain'] = 'Observation'
                row4['relationship_id'] = 'Has temporal context'
                row4['predicate_id'] = predicate
                row4['confidence'] = confidence
                row4['target_concept_id'] = temporal_qualifier_id
                row4['target_concept_name'] = temporal_qualifier_name
                row4['target_vocabulary_id'] = 'SNOMED'
                row4['target_domain_id'] = 'Observation'
                row4['mapping_justification'] = justification
                row4['mapping_tool'] = ''
                row4['author_label'] = 'FCA-pipeline'
                rows.append(row4)

    return rows


def load_unmappable(path: Path) -> list[dict]:
    """Load unmappable_items.csv and convert to noMatch rows."""
    rows = []
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        for r in reader:
            row = _empty_row(r['source_concept_code'], r['source_description'])
            row['predicate_id'] = 'noMatch'
            rows.append(row)
    return rows


_CONFIDENCE_MAP = {'high': 0.9, 'medium': 0.7, 'low': 0.5}


def _parse_confidence(val: str) -> float:
    """Convert confidence value to float, handling text labels."""
    if not val:
        return 0.0
    try:
        return float(val)
    except ValueError:
        return _CONFIDENCE_MAP.get(val.lower(), 0.5)


def load_clinical_review(path: Path) -> dict[str, list[dict]]:
    """Load clinical_review.csv and convert 'map' decisions to CVB rows.

    Returns dict mapping source_concept_code → list of CVB rows.
    Items with decision='skip' are omitted (they stay as noMatch).
    Items with qualifiers produce multi-row entries.
    """
    index: dict[str, list[dict]] = {}
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r['decision'] != 'map':
                continue

            code = r['source_concept_code']
            desc = r['source_description']

            # Row 1: Maps to → target concept
            row1 = _empty_row(code, desc)
            row1['source_domain'] = r.get('domain_id', 'Observation') or 'Observation'
            row1['relationship_id'] = 'Maps to'
            row1['predicate_id'] = r.get('predicate_id', 'broadMatch')
            row1['confidence'] = _parse_confidence(r.get('confidence', ''))
            row1['target_concept_id'] = int(r.get('target_concept_id', 0) or 0)
            row1['target_concept_name'] = r.get('target_concept_name', '')
            row1['target_vocabulary_id'] = r.get('target_vocabulary_id', '')
            row1['target_domain_id'] = r.get('domain_id', 'Observation') or 'Observation'
            row1['mapping_justification'] = r.get('mapping_justification', '')
            row1['mapping_tool'] = r.get('mapping_tool', '')
            row1['author_label'] = 'clinical-review'
            row1['review_date'] = r.get('review_date', '')
            row1['reviewer_name'] = r.get('reviewer_name', '')
            row1['status'] = 'pending'

            rows = [row1]

            # Row 2 (if qualifier): Has finding site → qualifier concept
            qid = int(r.get('qualifier_concept_id', 0) or 0)
            if qid:
                row2 = _empty_row(code, desc)
                row2['source_domain'] = r.get('domain_id', 'Observation') or 'Observation'
                row2['relationship_id'] = r.get('qualifier_relationship_id', 'Has finding site') or 'Has finding site'
                row2['predicate_id'] = r.get('predicate_id', 'broadMatch')
                row2['confidence'] = _parse_confidence(r.get('confidence', ''))
                row2['target_concept_id'] = qid
                row2['target_concept_name'] = r.get('qualifier_concept_name', '')
                row2['target_vocabulary_id'] = 'SNOMED'
                row2['target_domain_id'] = r.get('domain_id', 'Observation') or 'Observation'
                row2['mapping_justification'] = r.get('mapping_justification', '')
                row2['mapping_tool'] = r.get('mapping_tool', '')
                row2['author_label'] = 'clinical-review'
                row2['review_date'] = r.get('review_date', '')
                row2['reviewer_name'] = r.get('reviewer_name', '')
                row2['status'] = 'pending'
                rows.append(row2)

            index[code] = rows

    return index


def load_atomic_review(path: Path) -> dict[str, list[dict] | None]:
    """Load atomic_review.csv and convert reviewed items to CVB rows.

    Returns dict mapping source_concept_code → list of CVB rows (for 'map')
    or None (for 'skip'/'flag', signaling noMatch).
    Same CSV format as clinical_review.csv.
    """
    index: dict[str, list[dict] | None] = {}
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        for r in reader:
            code = r['source_concept_code']
            if r['decision'] != 'map':
                # skip/flag → will become noMatch
                index[code] = None
                continue

            desc = r['source_description']

            # Row 1: Maps to → target concept
            row1 = _empty_row(code, desc)
            row1['source_domain'] = r.get('domain_id', 'Measurement') or 'Measurement'
            row1['relationship_id'] = 'Maps to'
            row1['predicate_id'] = r.get('predicate_id', 'broadMatch')
            row1['confidence'] = _parse_confidence(r.get('confidence', ''))
            row1['target_concept_id'] = int(r.get('target_concept_id', 0) or 0)
            row1['target_concept_name'] = r.get('target_concept_name', '')
            row1['target_vocabulary_id'] = r.get('target_vocabulary_id', '')
            row1['target_domain_id'] = r.get('domain_id', 'Measurement') or 'Measurement'
            row1['mapping_justification'] = r.get('mapping_justification', '')
            row1['mapping_tool'] = r.get('mapping_tool', '')
            row1['author_label'] = 'atomic-review'
            row1['review_date'] = r.get('review_date', '')
            row1['reviewer_name'] = r.get('reviewer_name', '')
            row1['status'] = 'pending'

            rows = [row1]

            # Row 2 (if qualifier): relationship → qualifier concept
            qid = int(r.get('qualifier_concept_id', 0) or 0)
            if qid:
                row2 = _empty_row(code, desc)
                row2['source_domain'] = r.get('domain_id', 'Measurement') or 'Measurement'
                row2['relationship_id'] = r.get('qualifier_relationship_id', 'Has finding site') or 'Has finding site'
                row2['predicate_id'] = r.get('predicate_id', 'broadMatch')
                row2['confidence'] = _parse_confidence(r.get('confidence', ''))
                row2['target_concept_id'] = qid
                row2['target_concept_name'] = r.get('qualifier_concept_name', '')
                row2['target_vocabulary_id'] = 'SNOMED'
                row2['target_domain_id'] = r.get('domain_id', 'Measurement') or 'Measurement'
                row2['mapping_justification'] = r.get('mapping_justification', '')
                row2['mapping_tool'] = r.get('mapping_tool', '')
                row2['author_label'] = 'atomic-review'
                row2['review_date'] = r.get('review_date', '')
                row2['reviewer_name'] = r.get('reviewer_name', '')
                row2['status'] = 'pending'
                rows.append(row2)

            index[code] = rows

    return index


def load_existing(path: Path) -> dict[str, list[dict]]:
    """Load existing mapping.csv, indexed by source_concept_code.

    Returns a dict mapping code → list of rows (multi-row items have multiple).
    Only the first 21 columns (pipeline columns) are kept.
    """
    index: dict[str, list[dict]] = {}
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        for r in reader:
            code = r['source_concept_code']
            # Keep only pipeline columns
            row = {k: r.get(k, '') for k in OUTPUT_HEADERS}
            index.setdefault(code, []).append(row)
    return index


def load_atomic_codes(path: Path) -> dict[str, dict]:
    """Load atomic_items.csv and return dict of source_concept_code → info.

    Returns dict mapping code → {suggested_concept_id, suggested_concept_name,
    source_description, omop_domain}. Items without suggested concepts have
    suggested_concept_id=0.
    """
    items: dict[str, dict] = {}
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        for r in reader:
            items[r['source_concept_code']] = {
                'suggested_concept_id': int(r.get('suggested_concept_id', 0) or 0),
                'suggested_concept_name': r.get('suggested_concept_name', ''),
                'source_description': r.get('source_description', ''),
                'omop_domain': r.get('omop_domain', ''),
            }
    return items


def build_mapping_csv(
    compositional_path: Path,
    atomic_path: Path,
    unmappable_path: Path,
    existing_path: Path | None = None,
    clinical_review_path: Path | None = None,
    atomic_review_path: Path | None = None,
) -> list[dict]:
    """Build the merged mapping.csv rows.

    Strategy:
    - Compositional (B): multi-row broadMatch from FCA (replaces any existing)
    - Unmappable (C) with clinical review 'map': rescued mapping from review
    - Unmappable (C) without review or 'skip': noMatch
    - Atomic (A) priority: atomic_review → existing mapping → FCA suggested → noMatch
    """
    # Load FCA outputs
    comp_rows = load_compositional(compositional_path)
    unmappable_rows = load_unmappable(unmappable_path)
    atomic_items = load_atomic_codes(atomic_path)

    # Load clinical review (rescued C items)
    review_index: dict[str, list[dict]] = {}
    if clinical_review_path and clinical_review_path.exists():
        review_index = load_clinical_review(clinical_review_path)

    # Load atomic review (reviewed A items)
    atomic_review_index: dict[str, list[dict] | None] = {}
    if atomic_review_path and atomic_review_path.exists():
        atomic_review_index = load_atomic_review(atomic_review_path)

    # Codes already handled by compositional/unmappable
    handled_codes: set[str] = set()
    for r in comp_rows:
        handled_codes.add(r['source_concept_code'])
    for r in unmappable_rows:
        handled_codes.add(r['source_concept_code'])

    # Load existing mapping.csv for atomic items
    existing_index: dict[str, list[dict]] = {}
    if existing_path and existing_path.exists():
        existing_index = load_existing(existing_path)

    # Build atomic rows
    atomic_rows: list[dict] = []
    for code in sorted(atomic_items):
        if code in handled_codes:
            continue
        # Priority 1: atomic review (decision='map' → rows, skip/flag → None)
        if code in atomic_review_index:
            reviewed_rows = atomic_review_index[code]
            if reviewed_rows is not None:
                atomic_rows.extend(reviewed_rows)
            else:
                # skip/flag → noMatch
                row = _empty_row(code, atomic_items[code].get('source_description', ''))
                row['predicate_id'] = 'noMatch'
                row['mapping_justification'] = 'Atomic review: skipped or flagged'
                atomic_rows.append(row)
        # Priority 2: existing mapping.csv
        elif code in existing_index:
            atomic_rows.extend(existing_index[code])
        # Priority 3: FCA pre-coordinated concept
        elif atomic_items[code]['suggested_concept_id']:
            info = atomic_items[code]
            row = _empty_row(code, info['source_description'])
            row['source_domain'] = info['omop_domain'] or 'Measurement'
            row['relationship_id'] = 'Maps to'
            row['predicate_id'] = 'broadMatch'
            row['confidence'] = 0.8
            row['target_concept_id'] = info['suggested_concept_id']
            row['target_concept_name'] = info['suggested_concept_name']
            row['target_vocabulary_id'] = 'SNOMED'
            row['target_domain_id'] = info['omop_domain'] or 'Measurement'
            row['mapping_justification'] = (
                f"FCA method-qualified: pre-coordinated SNOMED concept"
            )
            row['author_label'] = 'FCA-pipeline'
            atomic_rows.append(row)
        else:
            # Priority 4: noMatch placeholder
            row = _empty_row(code, atomic_items[code].get('source_description', ''))
            row['predicate_id'] = 'noMatch'
            row['mapping_justification'] = 'FCA atomic: awaiting review'
            atomic_rows.append(row)

    # Replace unmappable noMatch rows with clinical review mappings where available
    final_unmappable: list[dict] = []
    rescued_rows: list[dict] = []
    for r in unmappable_rows:
        code = r['source_concept_code']
        if code in review_index:
            rescued_rows.extend(review_index[code])
        else:
            final_unmappable.append(r)

    # Combine: compositional + atomic + rescued + remaining unmappable
    all_rows = comp_rows + atomic_rows + rescued_rows + final_unmappable

    # Sort by source_concept_code for deterministic output
    all_rows.sort(key=lambda r: r['source_concept_code'])

    return all_rows


def write_mapping_csv(rows: list[dict], path: Path) -> None:
    """Write rows to mapping.csv."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_HEADERS, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def run_tests() -> bool:
    """Self-test with unit test items.

    Creates in-memory FCA CSVs matching the pipeline unit test items:
    - Pulse (8): atomic, has existing exactMatch AND atomic review → review wins
    - SpO2 (10): atomic, mapped in atomic review (no existing)
    - Rodnan (10022): atomic, flagged in atomic review → noMatch
    - BP Standing (99999): atomic, pre-coordinated from FCA (no review)
    - Breath Sounds Left (1120100008): compositional, 2 relationships
    - Pre-Dialysis BP (88888): compositional, temporal qualifier
    - MEWS (14950): unmappable, rescued by clinical review
    """
    import tempfile

    passed = 0
    failed = 0

    def check(name: str, condition: bool, msg: str = ''):
        nonlocal passed, failed
        if condition:
            print(f'  PASS: {name}')
            passed += 1
        else:
            print(f'  FAIL: {name} — {msg}')
            failed += 1

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # --- Create test FCA CSVs ---

        # compositional_mapping.csv: Breath Sounds Left + Pre-Dialysis BP
        comp_csv = tmp / 'compositional_mapping.csv'
        comp_csv.write_text(
            'source_concept_code,source_description,assessment_concept_id,'
            'assessment_concept_name,qualifier_concept_id,qualifier_concept_name,'
            'method_qualifier_concept_id,method_qualifier_concept_name,'
            'temporal_qualifier_concept_id,temporal_qualifier_concept_name,'
            'value_domain_type,fca_concept_id,predicate_id,confidence,'
            'mapping_justification\n'
            '1120100008,Breath Sounds Left,4278456,Breath sounds - finding,'
            '4300877,left,0,,0,,'
            ',C0250.03,broadMatch,0.8,'
            '"FCA concept C0250.03: intent={breath_sounds, left}"\n'
            '88888,Pre-Dialysis BP,4302666,Body temperature,'
            '0,,0,,4144786,Before procedure,'
            ',C0600.01,broadMatch,0.8,'
            '"FCA concept C0600.01: intent={blood_pressure, pre_dialysis}"\n'
        )

        # atomic_items.csv: Pulse + SpO2 + Rodnan + BP Standing
        atomic_csv = tmp / 'atomic_items.csv'
        atomic_csv.write_text(
            'source_concept_code,source_description,fca_concept_id,'
            'fca_category,fca_assessments,fca_methods,omop_domain,'
            'suggested_concept_id,suggested_concept_name\n'
            '8,Pulse,C0418.00,A,spo2,,Observation,0,\n'
            '10,SpO2,C0418.00,A,spo2,,Observation,0,\n'
            '10022,Rodnan Skin Score,C0900.00,A,,,Measurement,0,\n'
            '99999,BP Standing,C0500.01,A,blood_pressure,standing,Measurement,'
            '4060833,Standing blood pressure\n'
        )

        # unmappable_items.csv: MEWS
        unmappable_csv = tmp / 'unmappable_items.csv'
        unmappable_csv.write_text(
            'source_concept_code,source_description,fca_concept_id,'
            'reason,intent\n'
            '14950,MEWS Difference from Baseline,C0000.00,'
            'no_clinical_attributes,\n'
        )

        # clinical_review.csv: MEWS rescued with a mapping
        clinical_csv = tmp / 'clinical_review.csv'
        clinical_csv.write_text(
            'source_concept_code,source_description,decision,'
            'target_concept_id,target_concept_name,'
            'target_vocabulary_id,target_concept_code,'
            'predicate_id,confidence,domain_id,'
            'qualifier_concept_id,qualifier_concept_name,'
            'qualifier_relationship_id,mapping_justification,'
            'needs_source_data,mapping_tool,reviewer_name,'
            'reviewer_type,review_date\n'
            '14950,MEWS Difference from Baseline,map,'
            '40484261,Pediatric early warning score scale,'
            'SNOMED,763437008,'
            'broadMatch,0.7,Measurement,'
            ',,,'
            'MEWS baseline difference mapped to early warning score,'
            'no,claude-opus-4-6+ohdsi-vocab-mcp,claude-opus-4-6,'
            'llm,2026-03-08\n'
        )

        # atomic_review.csv: Pulse mapped (overrides existing), SpO2 mapped, Rodnan flagged
        atomic_review_csv = tmp / 'atomic_review.csv'
        atomic_review_csv.write_text(
            'source_concept_code,source_description,decision,'
            'target_concept_id,target_concept_name,'
            'target_vocabulary_id,target_concept_code,'
            'predicate_id,confidence,domain_id,'
            'qualifier_concept_id,qualifier_concept_name,'
            'qualifier_relationship_id,mapping_justification,'
            'needs_source_data,mapping_tool,reviewer_name,'
            'reviewer_type,review_date\n'
            '8,Pulse,map,'
            '4239408,Pulse rate,SNOMED,78564009,'
            'exactMatch,0.95,Measurement,'
            ',,,'
            'Pulse rate reviewed,no,claude-opus-4-6+ohdsi-vocab-mcp,'
            'claude-opus-4-6,llm,2026-03-08\n'
            '10,SpO2,map,'
            '4020553,Oxygen saturation measurement,SNOMED,104847001,'
            'maps_to,0.95,Measurement,'
            ',,,'
            'SpO2 reviewed,no,claude-opus-4-6+ohdsi-vocab-mcp,'
            'claude-opus-4-6,llm,2026-03-08\n'
            '10022,Rodnan Skin Score,flag,'
            ',,,,,,,'
            ',,,'
            'No OMOP concept for Rodnan,no,claude-opus-4-6+ohdsi-vocab-mcp,'
            'claude-opus-4-6,llm,2026-03-08\n'
        )

        # existing mapping.csv: has Pulse with exactMatch (should be overridden by atomic review)
        existing_csv = tmp / 'existing_mapping.csv'
        existing_csv.write_text(
            ','.join(OUTPUT_HEADERS) + '\n'
            '8,0,EU2_Flowsheets,Measurement,Suppl Concept,Pulse,PULSE,,'
            'exactMatch,0.9,3027018,Heart rate,LOINC,Measurement,'
            'Pulse maps to Heart rate,AM-tool_U,Joan,,,,pending\n'
            '14950,0,EU2_Flowsheets,Measurement,Suppl Concept,'
            'MEWS Difference from Baseline,R EHC BH MEWS BASELINE DIFFERENCE,,'
            'noMatch,0,0,,,,,,Joan,,,,pending\n'
        )

        # --- Run transformer ---
        print('Running build_mapping_csv self-test...\n')
        rows = build_mapping_csv(
            compositional_path=comp_csv,
            atomic_path=atomic_csv,
            unmappable_path=unmappable_csv,
            existing_path=existing_csv,
            clinical_review_path=clinical_csv,
            atomic_review_path=atomic_review_csv,
        )

        # --- Assertions ---

        # Total rows: BSL=2 (Maps to + Has finding site),
        # Pre-Dialysis BP=2 (Maps to + Has temporal context),
        # Pulse=1 (atomic review overrides existing), SpO2=1 (atomic review),
        # Rodnan=1 (flagged → noMatch), BP Standing=1 (pre-coordinated),
        # MEWS=1 (clinical review rescue)
        check('total row count is 9', len(rows) == 9,
              f'expected 9, got {len(rows)}')

        # Index by code
        by_code: dict[str, list[dict]] = {}
        for r in rows:
            by_code.setdefault(r['source_concept_code'], []).append(r)

        # Breath Sounds Left: 2 rows
        bsl = by_code.get('1120100008', [])
        check('BSL has 2 rows', len(bsl) == 2,
              f'expected 2, got {len(bsl)}')

        bsl_maps_to = [r for r in bsl if r['relationship_id'] == 'Maps to']
        check('BSL has Maps to row', len(bsl_maps_to) == 1,
              f'got {len(bsl_maps_to)}')
        if bsl_maps_to:
            check('BSL Maps to target is 4278456',
                  str(bsl_maps_to[0]['target_concept_id']) == '4278456',
                  f'got {bsl_maps_to[0]["target_concept_id"]}')

        bsl_fs = [r for r in bsl if r['relationship_id'] == 'Has finding site']
        check('BSL has Has finding site row', len(bsl_fs) == 1,
              f'got {len(bsl_fs)}')
        if bsl_fs:
            check('BSL Has finding site target is 4300877',
                  str(bsl_fs[0]['target_concept_id']) == '4300877',
                  f'got {bsl_fs[0]["target_concept_id"]}')

        # Both BSL rows: predicate=broadMatch, author=FCA-pipeline
        for r in bsl:
            check(f'BSL row predicate is broadMatch',
                  r['predicate_id'] == 'broadMatch',
                  f'got {r["predicate_id"]}')
            check(f'BSL row author is FCA-pipeline',
                  r['author_label'] == 'FCA-pipeline',
                  f'got {r["author_label"]}')

        # Pulse: 1 row from atomic review (overrides existing mapping)
        pulse = by_code.get('8', [])
        check('Pulse has 1 row', len(pulse) == 1,
              f'expected 1, got {len(pulse)}')
        if pulse:
            check('Pulse predicate is exactMatch (from review)',
                  pulse[0]['predicate_id'] == 'exactMatch',
                  f'got {pulse[0]["predicate_id"]}')
            check('Pulse target is 4239408 (from review, not 3027018)',
                  str(pulse[0]['target_concept_id']) == '4239408',
                  f'got {pulse[0]["target_concept_id"]}')
            check('Pulse author is atomic-review (not Joan)',
                  pulse[0]['author_label'] == 'atomic-review',
                  f'got {pulse[0]["author_label"]}')

        # SpO2: 1 row from atomic review
        spo2 = by_code.get('10', [])
        check('SpO2 has 1 row', len(spo2) == 1,
              f'expected 1, got {len(spo2)}')
        if spo2:
            check('SpO2 target is 4020553',
                  str(spo2[0]['target_concept_id']) == '4020553',
                  f'got {spo2[0]["target_concept_id"]}')
            check('SpO2 author is atomic-review',
                  spo2[0]['author_label'] == 'atomic-review',
                  f'got {spo2[0]["author_label"]}')

        # Rodnan: 1 row, flagged in atomic review → noMatch
        rodnan = by_code.get('10022', [])
        check('Rodnan has 1 row', len(rodnan) == 1,
              f'expected 1, got {len(rodnan)}')
        if rodnan:
            check('Rodnan predicate is noMatch',
                  rodnan[0]['predicate_id'] == 'noMatch',
                  f'got {rodnan[0]["predicate_id"]}')

        # Pre-Dialysis BP: 2 rows (Maps to + Has temporal context)
        pdbp = by_code.get('88888', [])
        check('Pre-Dialysis BP has 2 rows', len(pdbp) == 2,
              f'expected 2, got {len(pdbp)}')
        pdbp_temporal = [r for r in pdbp if r['relationship_id'] == 'Has temporal context']
        check('Pre-Dialysis BP has Has temporal context row',
              len(pdbp_temporal) == 1,
              f'got {len(pdbp_temporal)}')
        if pdbp_temporal:
            check('Pre-Dialysis BP temporal target is 4144786',
                  str(pdbp_temporal[0]['target_concept_id']) == '4144786',
                  f'got {pdbp_temporal[0]["target_concept_id"]}')

        # BP Standing: 1 row, pre-coordinated from FCA method detection
        bps = by_code.get('99999', [])
        check('BP Standing has 1 row', len(bps) == 1,
              f'expected 1, got {len(bps)}')
        if bps:
            check('BP Standing target is 4060833',
                  str(bps[0]['target_concept_id']) == '4060833',
                  f'got {bps[0]["target_concept_id"]}')
            check('BP Standing relationship is Maps to',
                  bps[0]['relationship_id'] == 'Maps to',
                  f'got {bps[0]["relationship_id"]}')
            check('BP Standing predicate is broadMatch',
                  bps[0]['predicate_id'] == 'broadMatch',
                  f'got {bps[0]["predicate_id"]}')
            check('BP Standing author is FCA-pipeline',
                  bps[0]['author_label'] == 'FCA-pipeline',
                  f'got {bps[0]["author_label"]}')

        # MEWS: 1 row, rescued by clinical review (broadMatch, not noMatch)
        mews = by_code.get('14950', [])
        check('MEWS has 1 row', len(mews) == 1,
              f'expected 1, got {len(mews)}')
        if mews:
            check('MEWS predicate is broadMatch (rescued)',
                  mews[0]['predicate_id'] == 'broadMatch',
                  f'got {mews[0]["predicate_id"]}')
            check('MEWS target is 40484261',
                  str(mews[0]['target_concept_id']) == '40484261',
                  f'got {mews[0]["target_concept_id"]}')
            check('MEWS author is clinical-review',
                  mews[0]['author_label'] == 'clinical-review',
                  f'got {mews[0]["author_label"]}')

        # --- Write output and verify CSV round-trip ---
        out_csv = tmp / 'output_mapping.csv'
        write_mapping_csv(rows, out_csv)

        # Re-read and verify
        with open(out_csv, newline='') as f:
            reader = csv.DictReader(f)
            reread = list(reader)
        check('CSV round-trip preserves row count',
              len(reread) == len(rows),
              f'expected {len(rows)}, got {len(reread)}')
        check('CSV has correct headers',
              list(reread[0].keys()) == OUTPUT_HEADERS,
              f'got {list(reread[0].keys())}')

    # Summary
    print(f'\n{passed} passed, {failed} failed')
    return failed == 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description='Transform FCA outputs into CVB mapping.csv'
    )
    parser.add_argument(
        '--test', action='store_true',
        help='Run self-test with unit test items'
    )
    parser.add_argument(
        '--compositional', type=Path,
        help='Path to compositional_mapping.csv'
    )
    parser.add_argument(
        '--atomic', type=Path,
        help='Path to atomic_items.csv'
    )
    parser.add_argument(
        '--unmappable', type=Path,
        help='Path to unmappable_items.csv'
    )
    parser.add_argument(
        '--existing', type=Path, default=None,
        help='Path to existing mapping.csv (for atomic item mappings)'
    )
    parser.add_argument(
        '--clinical-review', type=Path, default=None,
        help='Path to clinical_review.csv (rescued C items)'
    )
    parser.add_argument(
        '--atomic-review', type=Path, default=None,
        help='Path to atomic_review.csv (reviewed A items)'
    )
    parser.add_argument(
        '--output', type=Path,
        help='Output path for merged mapping.csv'
    )
    args = parser.parse_args(argv)

    if args.test:
        success = run_tests()
        sys.exit(0 if success else 1)

    if not all([args.compositional, args.atomic, args.unmappable, args.output]):
        parser.error(
            '--compositional, --atomic, --unmappable, and --output are required '
            '(or use --test)'
        )

    rows = build_mapping_csv(
        compositional_path=args.compositional,
        atomic_path=args.atomic,
        unmappable_path=args.unmappable,
        existing_path=args.existing,
        clinical_review_path=args.clinical_review,
        atomic_review_path=args.atomic_review,
    )

    write_mapping_csv(rows, args.output)

    # Summary
    by_pred: dict[str, int] = {}
    by_rel: dict[str, int] = {}
    for r in rows:
        pred = r['predicate_id'] or '(empty)'
        by_pred[pred] = by_pred.get(pred, 0) + 1
        rel = r['relationship_id'] or '(derived)'
        by_rel[rel] = by_rel.get(rel, 0) + 1

    codes = {r['source_concept_code'] for r in rows}
    print(f'Wrote {len(rows)} rows ({len(codes)} unique items) to {args.output}')
    print(f'  By predicate: {by_pred}')
    print(f'  By relationship: {by_rel}')


if __name__ == '__main__':
    main()
