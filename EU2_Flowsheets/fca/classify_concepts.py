"""Classify formal concepts into mapping categories.

Categories:
    A (Atomic):        No body_site/laterality → 1:1 OMOP mapping
    B (Compositional): Has assessment + body_site/laterality → observation + qualifier
    C (Unmappable):    No clinical assessment, or admin/workflow → noMatch

Usage:
    python -m fca.classify_concepts \\
        --lattice EU2_Flowsheets/raw_for_fca/fca_lattice.json \\
        --metadata EU2_Flowsheets/raw_for_fca/fca_metadata.json \\
        --output EU2_Flowsheets/raw_for_fca/fca_classification.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .constants import (
    PRE_COORDINATED_METHOD_CONCEPTS,
    PRE_COORDINATED_TEMPORAL_CONCEPTS,
)


# Template categories that are administrative/workflow (not clinical)
ADMIN_TEMPLATE_CATS = {
    'quality_measures', 'home_monitoring', 'tobacco_substance',
}

# Assessment types that indicate genuinely atomic items
ATOMIC_ASSESSMENTS = {
    # Vital signs
    'blood_pressure', 'heart_rate', 'respiratory_rate', 'spo2',
    'weight', 'height', 'bmi',
    # Scoring instruments
    'pain_score', 'gcs', 'rass', 'braden', 'morse_fall_risk',
    'stroke_scale', 'delirium_screening', 'suicide_risk',
    # Neuro/status
    'train_of_four', 'consciousness', 'orientation', 'body_position',
    # OB
    'contraction', 'fetal_variability',
    # Clinical findings (standalone, not lateralized)
    'seizure', 'headache', 'anxiety', 'depression', 'nausea', 'dyspnea',
    'tremor', 'fever', 'delirium', 'fatigue', 'dizziness', 'apnea',
    # Rehab/functional (standalone assessments)
    'gait', 'balance', 'swallowing', 'speech', 'cognition', 'memory',
    'attention', 'vision', 'hearing', 'toileting', 'bathing', 'grooming',
    'self_care',
}


def classify_concept(intent: list[str], extent: list[str]) -> dict:
    """Classify a single formal concept based on its intent.

    Args:
        intent: List of attribute names in the concept's intent.
        extent: List of FLO_MEAS_IDs in the concept's extent.

    Returns:
        Dict with category, reason, and routing info.
    """
    # Parse intent into attribute families
    has_body_site = any(a.startswith('body_site:') for a in intent)
    has_laterality = any(a.startswith('laterality:') for a in intent)
    has_assessment = any(a.startswith('assessment:') for a in intent)
    has_val_type = any(a.startswith('val_type:') for a in intent)
    has_value_domain = any(a.startswith('value_domain:') for a in intent)
    has_method = any(a.startswith('method:') for a in intent)
    has_temporal = any(a.startswith('temporal:') for a in intent)

    assessments = [
        a.split(':', 1)[1] for a in intent if a.startswith('assessment:')
    ]
    body_sites = [
        a.split(':', 1)[1] for a in intent if a.startswith('body_site:')
    ]
    lateralities = [
        a.split(':', 1)[1] for a in intent if a.startswith('laterality:')
    ]
    methods = [
        a.split(':', 1)[1] for a in intent if a.startswith('method:')
    ]
    temporals = [
        a.split(':', 1)[1] for a in intent if a.startswith('temporal:')
    ]
    val_types = [
        a.split(':', 1)[1] for a in intent if a.startswith('val_type:')
    ]
    template_cats = [
        a.split(':', 1)[1] for a in intent
        if a.startswith('template_cat:')
    ]

    # Check if purely administrative
    is_admin = (
        all(tc in ADMIN_TEMPLATE_CATS for tc in template_cats)
        if template_cats else False
    )

    # Classification logic
    if is_admin and not has_assessment:
        return {
            'category': 'C',
            'reason': 'administrative_template',
            'omop_domain': None,
            'routing': 'noMatch',
        }

    if not has_assessment and not has_val_type:
        return {
            'category': 'C',
            'reason': 'no_clinical_attributes',
            'omop_domain': None,
            'routing': 'noMatch',
        }

    # Temporal context: has assessment + temporal qualifier.
    # Check for pre-coordinated concept first; otherwise compositional B.
    if has_assessment and has_temporal:
        # Check if a pre-coordinated concept exists
        has_precoord_temporal = any(
            (a, t) in PRE_COORDINATED_TEMPORAL_CONCEPTS
            for a in assessments for t in temporals
        )
        if has_precoord_temporal and not has_body_site and not has_laterality:
            result = {
                'category': 'A',
                'reason': 'atomic_with_temporal',
                'omop_domain': _route_domain(val_types, assessments),
                'routing': '1:1',
                'assessments': assessments,
                'temporals': temporals,
            }
            if methods:
                result['methods'] = methods
            return result

        # Compositional: assessment + temporal (+ optional body_site/method)
        result = {
            'category': 'B',
            'reason': 'compositional_temporal',
            'omop_domain': 'Observation',
            'routing': 'observation_with_qualifier',
            'assessments': assessments,
            'temporals': temporals,
        }
        if body_sites:
            result['body_sites'] = body_sites
        if lateralities:
            result['lateralities'] = lateralities
        if methods:
            result['methods'] = methods
        return result

    # Compositional: has assessment AND (body_site or laterality)
    if has_assessment and (has_body_site or has_laterality):
        # Check if this is a "simple lateralized" vital that has
        # a pre-coordinated OMOP concept (e.g., pupil size L/R)
        if any(a in ATOMIC_ASSESSMENTS for a in assessments):
            result = {
                'category': 'A',
                'reason': 'atomic_with_site',
                'omop_domain': _route_domain(val_types, assessments),
                'routing': '1:1',
                'body_sites': body_sites,
                'lateralities': lateralities,
                'assessments': assessments,
            }
            if methods:
                result['methods'] = methods
            return result

        result = {
            'category': 'B',
            'reason': 'compositional',
            'omop_domain': 'Observation',
            'routing': 'observation_with_qualifier',
            'body_sites': body_sites,
            'lateralities': lateralities,
            'assessments': assessments,
        }
        if methods:
            result['methods'] = methods
        return result

    # Atomic with method: has assessment + method but NO body_site/laterality.
    # Pre-coordinated SNOMED concept exists for most (assessment, method) pairs.
    if has_assessment and has_method and not has_body_site and not has_laterality:
        return {
            'category': 'A',
            'reason': 'atomic_with_method',
            'omop_domain': _route_domain(val_types, assessments),
            'routing': '1:1',
            'assessments': assessments,
            'methods': methods,
        }

    # Atomic: has assessment but NO body_site/laterality/method
    if has_assessment and not has_body_site and not has_laterality:
        return {
            'category': 'A',
            'reason': 'atomic_assessment',
            'omop_domain': _route_domain(val_types, assessments),
            'routing': '1:1',
            'assessments': assessments,
        }

    # Has val_type but no assessment — could still be a measurement
    if has_val_type:
        is_numeric = any(v in ('numeric', 'blood_pressure', 'weight',
                                'height', 'temperature') for v in val_types)
        if is_numeric:
            return {
                'category': 'A',
                'reason': 'numeric_without_assessment',
                'omop_domain': 'Measurement',
                'routing': '1:1',
            }

    # Default: unmappable
    return {
        'category': 'C',
        'reason': 'insufficient_clinical_signal',
        'omop_domain': None,
        'routing': 'noMatch',
    }


def _route_domain(val_types: list[str], assessments: list[str]) -> str:
    """Determine OMOP domain routing."""
    numeric_types = {'numeric', 'blood_pressure', 'weight', 'height', 'temperature'}
    if any(v in numeric_types for v in val_types):
        return 'Measurement'
    return 'Observation'


def classify_all_concepts(lattice: dict) -> dict:
    """Classify all concepts in a lattice.

    Args:
        lattice: Output from compute_lattice_stratified.

    Returns:
        Dict with classified concepts and summary stats.
    """
    # Priority: B (compositional) > A (atomic) > C (unmappable).
    # An item appearing in multiple concepts gets the best category.
    CATEGORY_PRIORITY = {'B': 2, 'A': 1, 'C': 0}

    classified = []
    category_counts = {'A': 0, 'B': 0, 'C': 0}
    item_to_category: dict[str, str] = {}    # FLO_MEAS_ID → category
    item_to_concept: dict[str, str] = {}     # FLO_MEAS_ID → best concept_id

    for refinement in lattice['refinements']:
        coarse_id = refinement['coarse_concept_id']
        for si, sub in enumerate(refinement['sub_concepts']):
            concept_id = f"C{coarse_id:04d}.{si:02d}"
            classification = classify_concept(sub['intent'], sub['extent'])

            entry = {
                'concept_id': concept_id,
                'coarse_concept_id': coarse_id,
                'extent': sub['extent'],
                'intent': sub['intent'],
                **classification,
            }
            classified.append(entry)
            category_counts[classification['category']] += 1

            # For each item, keep the highest-priority category
            cat = classification['category']
            for flo_id in sub['extent']:
                prev = item_to_category.get(flo_id)
                if prev is None or CATEGORY_PRIORITY[cat] > CATEGORY_PRIORITY[prev]:
                    item_to_category[flo_id] = cat
                    item_to_concept[flo_id] = concept_id

    # Recount by unique item categories (not concept counts)
    item_cat_counts = {'A': 0, 'B': 0, 'C': 0}
    for cat in item_to_category.values():
        item_cat_counts[cat] += 1

    return {
        'classified_concepts': classified,
        'category_counts': category_counts,
        'item_categories': item_to_category,
        'item_concept_assignments': item_to_concept,
        'item_category_counts': item_cat_counts,
        'n_items_classified': len(item_to_category),
    }


def save_classification(classification: dict, output_path: Path) -> None:
    """Save classification results to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(classification, f, indent=2)

    cc = classification['category_counts']
    ic = classification.get('item_category_counts', {})
    print(f"Classification saved to {output_path}")
    print(f"  Concepts:  A={cc['A']}, B={cc['B']}, C={cc['C']}")
    print(f"  Items:     A={ic.get('A', '?')}, B={ic.get('B', '?')}, C={ic.get('C', '?')}")
    print(f"  Total items classified: {classification['n_items_classified']}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description='Classify formal concepts into mapping categories'
    )
    parser.add_argument(
        '--lattice', required=True, type=Path,
        help='Path to fca_lattice.json'
    )
    parser.add_argument(
        '--output', required=True, type=Path,
        help='Output path for fca_classification.json'
    )
    args = parser.parse_args(argv)

    with open(args.lattice) as f:
        lattice = json.load(f)

    classification = classify_all_concepts(lattice)
    save_classification(classification, args.output)


if __name__ == '__main__':
    main()
