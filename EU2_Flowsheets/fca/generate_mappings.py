"""Generate OMOP mapping CSVs from classified formal concepts.

Produces three outputs:
1. Updates to existing mapping.csv (atomic 1:1 items)
2. New compositional_mapping.csv (observation + qualifier_concept_id)
3. New value_mappings.csv (categorical value → OMOP concept)

Usage:
    python -m fca.generate_mappings \\
        --classification EU2_Flowsheets/raw_for_fca/fca_classification.json \\
        --metadata EU2_Flowsheets/raw_for_fca/fca_metadata.json \\
        --output-dir EU2_Flowsheets/Mappings/
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .constants import QUALIFIER_CONCEPTS


# --- Compositional mapping CSV schema ---
COMPOSITIONAL_HEADERS = [
    'source_concept_code',
    'source_description',
    'assessment_concept_id',
    'assessment_concept_name',
    'qualifier_concept_id',
    'qualifier_concept_name',
    'value_domain_type',
    'fca_concept_id',
    'predicate_id',
    'confidence',
    'mapping_justification',
]

# --- Value mapping CSV schema ---
VALUE_MAPPING_HEADERS = [
    'source_flo_meas_id',
    'source_option_value',
    'target_concept_id',
    'target_concept_name',
    'value_domain_type',
]

# --- Assessment → OMOP concept_id mapping ---
# These are the base observation/measurement concepts for each assessment type.
# Concept IDs are looked up via OHDSI vocab tools and verified.
# This dict is populated during the vocab lookup phase (Step 5).
ASSESSMENT_CONCEPT_MAP: dict[str, tuple[int, str]] = {
    # Vascular assessments — all verified via OHDSI vocab search
    'edema':           (433595,   'Edema'),                           # SNOMED 267038008
    'pulse':           (4183393,  'Peripheral pulse'),                # SNOMED 54718008
    'capillary_refill': (4089379, 'Capillary refill'),               # SNOMED 248753002
    'color':           (4264810,  'Color of skin'),                   # SNOMED 364533002
    'temperature':     (4302666,  'Body temperature'),                # SNOMED 386725007
    'cyanosis':        (438555,   'Cyanosis'),                        # SNOMED 3415004
    'perfusion':       (4090047,  'Tissue perfusion measure'),        # SNOMED 252084009
    # Neurological
    'motor':           (4198563,  'Motor function'),                  # SNOMED 52479005
    'sensation':       (4287782,  'Somatic sensation'),               # SNOMED 397725003
    'reflex':          (4227123,  'Reflex'),                          # SNOMED 87572000
    'neuro_general':   (4011630,  'Neurological finding'),            # SNOMED 102957003
    # Respiratory
    'breath_sounds':   (4278456,  'Breath sounds - finding'),         # SNOMED 366135003
    'respiratory_general': (4024567, 'Respiratory finding'),          # SNOMED 106048009
    'cough':           (254761,   'Cough'),                           # SNOMED 49727002
    'sputum':          (4164116,  'Sputum'),                          # SNOMED 45710003
    # Skin/wound
    'wound':           (4021667,  'Wound finding'),                   # SNOMED 225552003
    'skin_assessment': (141960,   'Skin finding'),                    # SNOMED 106076001
    'pressure_injury': (37159532, 'Pressure injury'),                 # SNOMED 1163215007
    # GI
    'bowel_sounds':    (4337265,  'Bowel sounds'),                    # SNOMED 87042004
    'drainage':        (4312638,  'Skin drainage'),                   # SNOMED 424329008
    # Cardiac
    'cardiac_rhythm':  (4091457,  'Cardiac rhythm type'),             # SNOMED 251149006
    'heart_sounds':    (4158197,  'Heart sounds'),                    # SNOMED 271660002
    # WDL screening (within defined limits)
    'wdl_screening':   (4011630,  'Neurological finding'),            # Using neuro as proxy for WDL
    # Pupil
    'pupil':           (4081627,  'Pupil finding'),                    # SNOMED 247010007
    # O2 delivery
    'o2_delivery':     (4036936,  'Oxygen delivery'),                  # SNOMED 16206004
    # Dressing
    'dressing':        (761103,   'Wound dressing observable'),        # SNOMED 1481000124102
    # GI/GU
    'urine':           (437382,   'Urine finding'),                    # SNOMED 301830001
    'stool':           (4093347,  'Stool finding'),                    # SNOMED 249612005
    # Pain
    'pain_score':      (4022240,  'Pain score'),                       # SNOMED 225908003
    'pain_location':   (4132926,  'Pain finding at anatomical site'),  # SNOMED 279001004
    'pain_general':    (4234651,  'Pain level'),                       # SNOMED 405161002
    # Functional
    'mobility':        (4083973,  'Ability to walk'),                  # SNOMED 282097004
    'ambulation':      (4083973,  'Ability to walk'),                  # SNOMED 282097004
    'adl':             (4126495,  'Activities of daily living assessment'), # SNOMED 304492001
    'fall_risk':       (4185623,  'Fall risk assessment'),             # SNOMED 414191008
    # Intake/Output
    'intake':          (4092647,  'Fluid intake'),                     # SNOMED 251992000
    'output':          (4090192,  'Fluid output'),                     # SNOMED 251840008
    # Consciousness/Orientation
    'consciousness':   (4290243,  'Level of consciousness'),           # SNOMED 6942003
    'orientation':     (4183166,  'Orientation'),                      # SNOMED 43173001
    # Neuromuscular
    'train_of_four':   (4353950,  'Train of four count'),              # SNOMED 250832007
    'grip_strength':   (4089159,  'Grip strength'),                    # SNOMED 251433001
    'muscle_tone':     (4289445,  'Muscle tone'),                      # SNOMED 6918002
    # Neuro scales
    'stroke_scale':    (42872749, 'National Institutes of Health stroke scale'), # SNOMED 450741005
    'delirium_screening': (44807161, 'Short confusion assessment method'), # SNOMED 824471000000102
    'suicide_risk':    (4166620,  'Suicide risk scale'),               # SNOMED 273852006
    # Facial/CPOT
    'facial_assessment': (4011630, 'Neurological finding'),            # SNOMED 102957003 (proxy)
    'vocalization':    (4175709,  'Vocalization'),                     # SNOMED 278288005
    'body_movement':   (37116893, 'Assessment of body movement'),      # SNOMED 733919004
    'ventilator_compliance': (4298264, 'Lung compliance'),             # SNOMED 3863008
    # OB/Fetal
    'contraction':     (4322469,  'Uterine contraction'),              # SNOMED 70514001
    'fetal_variability': (4089747, 'Fetal heart rate variability'),    # SNOMED 251671002
    # GI
    'bowel_function':  (4024576,  'Large bowel function'),             # SNOMED 106084002
    # Position
    'body_position':   (4287468,  'Body position'),                    # SNOMED 397155001
    # Rehab / Functional
    'gait':            (4272021,  'Gait'),                             # SNOMED 63448001
    'balance':         (4179853,  'Balance observable'),               # SNOMED 363838007
    'toileting':       (4110000,  'Ability to use toilet'),            # SNOMED 284906000
    'bathing':         (4108023,  'Ability to wash self'),             # SNOMED 284785009
    'grooming':        (45767121, 'Personal grooming activities'),     # SNOMED 704435007
    'self_care':       (44792412, 'Self care'),                        # SNOMED 326051000000105
    # Speech/Swallowing/Cognition
    'swallowing':      (4252257,  'Swallowing function of larynx'),   # SNOMED 73821007
    'speech':          (4237854,  'Speech observable'),                # SNOMED 363918005
    'cognition':       (4150851,  'Cognitive functions'),              # SNOMED 311465003
    'memory':          (4239755,  'Memory observable'),                # SNOMED 363887009
    'attention':       (4150851,  'Cognitive functions'),              # SNOMED 311465003 (proxy)
    'vision':          (4239582,  'Visual acuity'),                    # SNOMED 363983007
    'hearing':         (4038501,  'Hearing finding'),                  # SNOMED 118230007
    # Clinical findings
    'seizure':         (377091,   'Seizure'),                          # SNOMED 91175000
    'headache':        (378253,   'Headache'),                         # SNOMED 25064002
    'anxiety':         (441542,   'Anxiety'),                          # SNOMED 48694002
    'depression':      (440383,   'Depressive disorder'),              # SNOMED 35489007
    'nausea':          (31967,    'Nausea'),                           # SNOMED 422587007
    'dyspnea':         (312437,   'Dyspnea'),                         # SNOMED 267036007
    'tremor':          (443782,   'Tremor'),                           # SNOMED 26079004
    'fever':           (437663,   'Fever'),                            # SNOMED 386661006
    'delirium':        (373995,   'Delirium'),                         # SNOMED 2776000
    'fatigue':         (4223659,  'Fatigue'),                          # SNOMED 84229001
    'dizziness':       (4223938,  'Dizziness'),                        # SNOMED 404640003
    'apnea':           (321689,   'Apnea'),                            # SNOMED 1023001
    # --- Concepts added by clinical reasoning pass ---
    'range_of_motion': (74392,    'Finding of range of joint movement'), # SNOMED 298180004
    'sleep_assessment': (4041989, 'Sleep finding'),                     # SNOMED 118190003
    'muscle_strength': (4097165,  'Grade of muscle power'),             # SNOMED 249948009
    'allergy_assessment': (1243740, 'Allergy status'),                  # SNOMED 1300212001
    'bladder_function': (4170255, 'Urinary bladder function'),          # SNOMED 42111002
    'ventilator_settings': (40488354, 'Continuous positive airway pressure titration'), # SNOMED 446573003
    'perceived_exertion': (37311860, 'Borg Rating of Perceived Exertion'), # SNOMED 789163003
    'continence':      (4235720,  'Urinary continence status'),         # SNOMED 406218000
    'spasticity':      (4329728,  'Spasticity'),                        # SNOMED 221360009
    'appetite':        (4269437,  'Appetite observable'),                # SNOMED 364663004
    'swelling':        (4275722,  'Swelling'),                          # SNOMED 65124004
    'restraint':       (4302381,  'Physical restraint'),                 # SNOMED 386423001
    'suction':         (4047449,  'Airway suction technique'),           # SNOMED 230040009
    'vomiting':        (4096715,  'Vomiting symptom'),                   # SNOMED 249497008
    'enteral_feeding': (4042005,  'Enteral feeding'),                    # SNOMED 229912004
    'cranial_nerve':   (4024014,  'Cranial nerve finding'),              # SNOMED 106150003
    'speech_disorder': (4237854,  'Speech observable'),                  # SNOMED 363918005
    'diaphoresis':     (4188566,  'Sweating'),                           # SNOMED 415690000
    'rigidity':        (4050941,  'Muscle rigidity'),                    # SNOMED 16046003
    'pruritus':        (4169287,  'Itching of skin'),                    # SNOMED 418363000
    'fim_score':       (4159704,  'Functional independence measure'),    # SNOMED 273469003
    'agitation':       (4187507,  'Psychomotor agitation'),              # SNOMED 47295007
    'skin_finding':    (141960,   'Skin finding'),                       # SNOMED 106076001
    'bowel_movement':  (4024576,  'Large bowel function'),               # SNOMED 106084002
}


def _build_concept_index(classification: dict) -> dict[str, dict]:
    """Index classified concepts by concept_id for fast lookup."""
    return {
        c['concept_id']: c
        for c in classification['classified_concepts']
    }


def generate_compositional_mappings(
    classification: dict,
    metadata: dict,
) -> list[dict]:
    """Generate compositional mapping rows for category B items.

    Deduplicated: each item appears exactly once, using its best
    concept assignment from item_concept_assignments.
    """
    rows = []
    item_data = metadata.get('item_data', {})
    item_cats = classification.get('item_categories', {})
    item_concepts = classification.get('item_concept_assignments', {})
    concept_idx = _build_concept_index(classification)

    for flo_id, cat in item_cats.items():
        if cat != 'B':
            continue

        concept_id = item_concepts.get(flo_id)
        concept = concept_idx.get(concept_id, {})
        intent = concept.get('intent', [])

        assessments = concept.get('assessments', [])
        body_sites = concept.get('body_sites', [])
        lateralities = concept.get('lateralities', [])

        # Get assessment concept
        assessment_id = 0
        assessment_name = ''
        for a in assessments:
            if a in ASSESSMENT_CONCEPT_MAP:
                assessment_id, assessment_name = ASSESSMENT_CONCEPT_MAP[a]
                break

        # Get qualifier concept (body_site + laterality)
        qualifier_id = 0
        qualifier_name = ''
        site = body_sites[0] if body_sites else None
        lat = lateralities[0] if lateralities else None
        if site or lat:
            key = (site, lat)
            if key in QUALIFIER_CONCEPTS:
                qualifier_id = QUALIFIER_CONCEPTS[key]
                qualifier_name = f"{site or ''} {lat or ''}".strip()
            elif (None, lat) in QUALIFIER_CONCEPTS:
                qualifier_id = QUALIFIER_CONCEPTS[(None, lat)]
                qualifier_name = lat or ''

        # Value domain
        value_domains = [
            a.split(':', 1)[1] for a in intent
            if a.startswith('value_domain:')
        ]
        vd = value_domains[0] if value_domains else ''

        # Confidence
        if assessment_id and qualifier_id:
            confidence = 0.8
            predicate = 'broadMatch'
        elif assessment_id:
            confidence = 0.6
            predicate = 'broadMatch'
        else:
            confidence = 0.3
            predicate = 'relatedMatch'

        idata = item_data.get(flo_id, {})
        rows.append({
            'source_concept_code': flo_id,
            'source_description': idata.get('disp_name', ''),
            'assessment_concept_id': assessment_id,
            'assessment_concept_name': assessment_name,
            'qualifier_concept_id': qualifier_id,
            'qualifier_concept_name': qualifier_name,
            'value_domain_type': vd,
            'fca_concept_id': concept_id,
            'predicate_id': predicate,
            'confidence': confidence,
            'mapping_justification': (
                f"FCA concept {concept_id}: "
                f"intent={{{', '.join(intent)}}}"
            ),
        })

    return rows


def generate_atomic_updates(
    classification: dict,
    metadata: dict,
) -> list[dict]:
    """Generate mapping updates for category A (atomic) items.

    Deduplicated: each item appears exactly once.
    """
    rows = []
    item_data = metadata.get('item_data', {})
    item_cats = classification.get('item_categories', {})
    item_concepts = classification.get('item_concept_assignments', {})
    concept_idx = _build_concept_index(classification)

    for flo_id, cat in item_cats.items():
        if cat != 'A':
            continue

        concept_id = item_concepts.get(flo_id)
        concept = concept_idx.get(concept_id, {})
        assessments = concept.get('assessments', [])

        idata = item_data.get(flo_id, {})
        rows.append({
            'source_concept_code': flo_id,
            'source_description': idata.get('disp_name', ''),
            'fca_concept_id': concept_id,
            'fca_category': 'A',
            'fca_assessments': ','.join(assessments),
            'omop_domain': concept.get('omop_domain', ''),
        })

    return rows


def generate_unmappable_report(
    classification: dict,
    metadata: dict,
) -> list[dict]:
    """Generate report of category C (unmappable) items with reasons.

    Deduplicated: each item appears exactly once.
    """
    rows = []
    item_data = metadata.get('item_data', {})
    item_cats = classification.get('item_categories', {})
    item_concepts = classification.get('item_concept_assignments', {})
    concept_idx = _build_concept_index(classification)

    for flo_id, cat in item_cats.items():
        if cat != 'C':
            continue

        concept_id = item_concepts.get(flo_id)
        concept = concept_idx.get(concept_id, {})

        idata = item_data.get(flo_id, {})
        rows.append({
            'source_concept_code': flo_id,
            'source_description': idata.get('disp_name', ''),
            'fca_concept_id': concept_id,
            'reason': concept.get('reason', ''),
            'intent': ', '.join(concept.get('intent', [])),
        })

    return rows


def write_csv(rows: list[dict], path: Path, headers: list[str]) -> None:
    """Write rows to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Wrote {len(rows)} rows to {path}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description='Generate OMOP mapping CSVs from classified concepts'
    )
    parser.add_argument(
        '--classification', required=True, type=Path,
        help='Path to fca_classification.json'
    )
    parser.add_argument(
        '--metadata', required=True, type=Path,
        help='Path to fca_metadata.json'
    )
    parser.add_argument(
        '--output-dir', required=True, type=Path,
        help='Output directory for mapping CSVs'
    )
    args = parser.parse_args(argv)

    with open(args.classification) as f:
        classification = json.load(f)
    with open(args.metadata) as f:
        metadata = json.load(f)

    print("Generating mappings...")

    # Compositional mappings
    comp_rows = generate_compositional_mappings(classification, metadata)
    write_csv(
        comp_rows,
        args.output_dir / 'compositional_mapping.csv',
        COMPOSITIONAL_HEADERS,
    )

    # Atomic item report (for manual mapping enrichment)
    atomic_rows = generate_atomic_updates(classification, metadata)
    write_csv(
        atomic_rows,
        args.output_dir / 'atomic_items.csv',
        ['source_concept_code', 'source_description', 'fca_concept_id',
         'fca_category', 'fca_assessments', 'omop_domain'],
    )

    # Unmappable report
    unmappable_rows = generate_unmappable_report(classification, metadata)
    write_csv(
        unmappable_rows,
        args.output_dir / 'unmappable_items.csv',
        ['source_concept_code', 'source_description', 'fca_concept_id',
         'reason', 'intent'],
    )

    # Summary
    cc = classification['category_counts']
    print(f"\nSummary:")
    print(f"  Compositional mappings: {len(comp_rows)} items "
          f"(from {cc['B']} concepts)")
    print(f"  Atomic items: {len(atomic_rows)} "
          f"(from {cc['A']} concepts)")
    print(f"  Unmappable: {len(unmappable_rows)} "
          f"(from {cc['C']} concepts)")


if __name__ == '__main__':
    main()
