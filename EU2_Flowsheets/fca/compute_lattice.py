"""Compute the concept lattice from a formal context using NextClosure.

Implements a stratified computation approach:
    Pass 1 (coarse): structural + assessment attributes only → ~500-2K concepts
    Pass 2 (fine): body_site + laterality refinement within each coarse concept

The NextClosure algorithm (Ganter, 1984) is deterministic and
O(|G|·|M|·|L|) where |L| is the number of formal concepts.

Uses the `concepts` Python package for the core lattice computation.

Usage:
    python -m fca.compute_lattice \\
        --context-dir EU2_Flowsheets/raw_for_fca/ \\
        --output EU2_Flowsheets/raw_for_fca/fca_lattice.json
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
from scipy import sparse

# Try to use the 'concepts' package; fall back to our own NextClosure
try:
    import concepts as concepts_lib
    HAS_CONCEPTS_LIB = True
except ImportError:
    HAS_CONCEPTS_LIB = False


# --- Galois connection operators on sparse matrices ---

def derive_objects(
    incidence: sparse.csr_matrix,
    obj_indices: np.ndarray,
) -> np.ndarray:
    """A' = {m ∈ M | ∀g ∈ A: (g,m) ∈ I}

    Given a set of object indices, return the attribute indices
    shared by ALL objects.
    """
    if len(obj_indices) == 0:
        return np.arange(incidence.shape[1])
    sub = incidence[obj_indices, :]
    # An attribute is shared by all objects iff its column sum == |A|
    col_sums = np.asarray(sub.sum(axis=0)).ravel()
    return np.where(col_sums == len(obj_indices))[0]


def derive_attributes(
    incidence: sparse.csr_matrix,
    attr_indices: np.ndarray,
) -> np.ndarray:
    """B' = {g ∈ G | ∀m ∈ B: (g,m) ∈ I}

    Given a set of attribute indices, return the object indices
    possessing ALL attributes.
    """
    if len(attr_indices) == 0:
        return np.arange(incidence.shape[0])
    sub = incidence[:, attr_indices]
    row_sums = np.asarray(sub.sum(axis=1)).ravel()
    return np.where(row_sums == len(attr_indices))[0]


def closure(
    incidence: sparse.csr_matrix,
    attr_indices: np.ndarray,
) -> np.ndarray:
    """Compute B'' (double-prime closure of attribute set B)."""
    objs = derive_attributes(incidence, attr_indices)
    return derive_objects(incidence, objs)


# --- NextClosure algorithm (Ganter, 1984) ---

def next_closure(
    incidence: sparse.csr_matrix,
    current: set[int],
    n_attrs: int,
) -> set[int] | None:
    """Compute the next closed set after `current` in lectic order.

    Returns None if current is the last closure (= M).
    """
    for i in range(n_attrs - 1, -1, -1):
        if i in current:
            current = current - {i}
        else:
            candidate = current | {i}
            closed = set(closure(incidence, np.array(sorted(candidate))).tolist())
            # Check lectic condition: closed agrees with candidate on {0..i-1}
            if all((j in closed) == (j in candidate) for j in range(i)):
                return closed
    return None


def compute_all_concepts(
    incidence: sparse.csr_matrix,
    max_concepts: int = 50000,
) -> list[tuple[list[int], list[int]]]:
    """Enumerate all formal concepts using NextClosure.

    Returns list of (extent, intent) pairs where extent and intent
    are lists of indices into the objects and attributes arrays.
    """
    n_objects, n_attrs = incidence.shape
    concepts: list[tuple[list[int], list[int]]] = []

    # Start with the closure of the empty set
    current_intent = set(closure(incidence, np.array([], dtype=int)).tolist())
    current_extent = derive_attributes(incidence, np.array(sorted(current_intent)))

    concepts.append((
        sorted(current_extent.tolist()),
        sorted(current_intent),
    ))

    count = 1
    while count < max_concepts:
        next_intent = next_closure(incidence, current_intent, n_attrs)
        if next_intent is None:
            break

        extent = derive_attributes(incidence, np.array(sorted(next_intent)))
        concepts.append((
            sorted(extent.tolist()),
            sorted(next_intent),
        ))

        current_intent = next_intent
        count += 1

        if count % 500 == 0:
            print(f"  ... {count} concepts enumerated")

    return concepts


def _filter_columns(
    incidence: sparse.csr_matrix,
    attributes: list[str],
    prefixes: list[str],
) -> tuple[sparse.csr_matrix, list[str], list[int]]:
    """Select only columns whose attribute name starts with given prefixes."""
    keep = []
    for i, attr in enumerate(attributes):
        if any(attr.startswith(p) for p in prefixes):
            keep.append(i)
    sub = incidence[:, keep]
    sub_attrs = [attributes[i] for i in keep]
    return sub, sub_attrs, keep


def compute_lattice_stratified(
    incidence: sparse.csr_matrix,
    objects: list[str],
    attributes: list[str],
    max_coarse: int = 5000,
    max_fine_per_concept: int = 500,
) -> dict:
    """Stratified lattice computation.

    Pass 1: Coarse lattice using structural + assessment attributes.
    Pass 2: Fine-grained refinement using body_site + laterality.
    """
    # --- Pass 1: Coarse lattice ---
    # NOTE: group_name: excluded — too many unique values (thousands),
    # which explodes the attribute space and makes NextClosure intractable.
    # group_name is used in Pass 2 refinement instead.
    coarse_prefixes = [
        'val_type:', 'template_cat:', 'assessment:', 'value_domain:',
        'has_range', 'is_intake', 'is_output', 'has_age_filter',
        'has_sex_filter',
    ]

    print("Pass 1: Computing coarse lattice...")
    coarse_inc, coarse_attrs, coarse_col_idx = _filter_columns(
        incidence, attributes, coarse_prefixes
    )
    print(f"  Coarse attributes: {len(coarse_attrs)} "
          f"(from {len(attributes)} total)")

    # Remove all-zero rows (objects with no coarse attributes)
    row_nnz = np.asarray(coarse_inc.sum(axis=1)).ravel()
    active_rows = np.where(row_nnz > 0)[0]
    coarse_active = coarse_inc[active_rows, :]
    print(f"  Active objects: {len(active_rows)} "
          f"(from {incidence.shape[0]} total)")

    # Remove all-zero columns
    col_nnz = np.asarray(coarse_active.sum(axis=0)).ravel()
    active_cols = np.where(col_nnz > 0)[0]
    coarse_trimmed = coarse_active[:, active_cols]
    trimmed_attrs = [coarse_attrs[i] for i in active_cols]
    print(f"  Active attributes: {len(active_cols)}")

    t0 = time.time()
    coarse_concepts = compute_all_concepts(coarse_trimmed, max_coarse)
    t1 = time.time()
    print(f"  {len(coarse_concepts)} coarse concepts in {t1 - t0:.1f}s")

    # Map back to original object indices
    coarse_results = []
    for extent_idx, intent_idx in coarse_concepts:
        orig_obj_idx = [int(active_rows[i]) for i in extent_idx]
        intent_names = [trimmed_attrs[i] for i in intent_idx]
        coarse_results.append({
            'extent_idx': orig_obj_idx,
            'extent': [objects[i] for i in orig_obj_idx],
            'intent': intent_names,
        })

    # --- Pass 2: Fine-grained refinement ---
    fine_prefixes = ['body_site:', 'laterality:', 'method:', 'temporal:', 'unit:']

    print("Pass 2: Refining with body_site, laterality, method, temporal...")
    fine_inc, fine_attrs, fine_col_idx = _filter_columns(
        incidence, attributes, fine_prefixes
    )

    refinements = []
    n_refined = 0

    for ci, concept in enumerate(coarse_results):
        extent_idx = np.array(concept['extent_idx'])
        if len(extent_idx) <= 1:
            # Single-item concept — no refinement needed
            refinements.append({
                'coarse_concept_id': ci,
                'sub_concepts': [{
                    'extent': concept['extent'],
                    'intent': concept['intent'],
                    'fine_intent': [],
                }],
            })
            continue

        # Sub-context: rows = this concept's extent, cols = fine attributes
        sub_inc = fine_inc[extent_idx, :]
        # Remove zero columns
        col_nnz = np.asarray(sub_inc.sum(axis=0)).ravel()
        active_fine = np.where(col_nnz > 0)[0]

        if len(active_fine) == 0:
            # No fine-grained attributes — concept stays as-is
            refinements.append({
                'coarse_concept_id': ci,
                'sub_concepts': [{
                    'extent': concept['extent'],
                    'intent': concept['intent'],
                    'fine_intent': [],
                }],
            })
            continue

        sub_trimmed = sub_inc[:, active_fine]
        sub_fine_attrs = [fine_attrs[i] for i in active_fine]

        sub_concepts = compute_all_concepts(sub_trimmed, max_fine_per_concept)

        subs = []
        for sub_ext, sub_int in sub_concepts:
            orig_objs = [objects[int(extent_idx[i])] for i in sub_ext]
            sub_intent = [sub_fine_attrs[i] for i in sub_int]
            subs.append({
                'extent': orig_objs,
                'intent': concept['intent'] + sub_intent,
                'fine_intent': sub_intent,
            })

        refinements.append({
            'coarse_concept_id': ci,
            'sub_concepts': subs,
        })
        n_refined += 1

    total_fine = sum(len(r['sub_concepts']) for r in refinements)
    print(f"  {n_refined} concepts refined → {total_fine} total fine concepts")

    return {
        'coarse_concepts': coarse_results,
        'refinements': refinements,
        'stats': {
            'n_coarse': len(coarse_results),
            'n_fine_total': total_fine,
            'coarse_time_s': round(t1 - t0, 2),
        },
    }


def save_lattice(lattice: dict, output_path: Path) -> None:
    """Save lattice results to JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(lattice, f, indent=2)
    print(f"Lattice saved to {output_path}")
    print(f"  Coarse concepts: {lattice['stats']['n_coarse']}")
    print(f"  Fine concepts: {lattice['stats']['n_fine_total']}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description='Compute concept lattice from formal context'
    )
    parser.add_argument(
        '--context-dir', required=True, type=Path,
        help='Directory containing fca_context.json and fca_incidence.npz'
    )
    parser.add_argument(
        '--output', required=True, type=Path,
        help='Output path for fca_lattice.json'
    )
    parser.add_argument(
        '--max-coarse', type=int, default=5000,
        help='Max coarse concepts to enumerate'
    )
    args = parser.parse_args(argv)

    # Load context
    with open(args.context_dir / 'fca_context.json') as f:
        ctx = json.load(f)

    objects = ctx['objects']
    attributes = ctx['attributes']
    incidence = sparse.load_npz(args.context_dir / 'fca_incidence.npz')

    print(f"Loaded context: {len(objects)} objects × {len(attributes)} attributes")

    lattice = compute_lattice_stratified(
        incidence, objects, attributes,
        max_coarse=args.max_coarse,
    )

    save_lattice(lattice, args.output)


if __name__ == '__main__':
    main()
