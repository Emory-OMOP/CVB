"""FCA-based flowsheet-to-OMOP mapping pipeline.

Uses Formal Concept Analysis (Ganter & Wille, 1999) to systematically
identify mapping groups from Epic flowsheet metadata and generate
OMOP mappings with proper modifiers.

Pipeline stages:
    1. build_context  - CSV → formal context K = (G, M, I)
    2. compute_lattice - Context → concept lattice B(K)
    3. classify_concepts - Lattice → A/B/C categories
    4. generate_mappings - Categories → mapping CSVs
    5. validate - Automated integrity checks
"""
