# FCA Flowsheet Mapping Pipeline

## What is this?

Hospitals record patient data using **flowsheet items** — things like "Heart Rate", "RLE Edema", or "Breath Sounds Left." Our hospital has **55,938** of these items, and we need to translate each one into a standard medical coding system called **OMOP** so researchers can study the data.

The catch: many flowsheet items aren't simple. "RLE Edema" really means **two things at once**: "Edema" (the observation) + "Right Lower Extremity" (the body location). There's no single standard code for that combination. We can't just match them one-to-one.

This pipeline uses a branch of mathematics called **Formal Concept Analysis (FCA)** to automatically find families of related items, figure out what each family means, and generate the right translations — including the ones that need two codes instead of one.

## How it works

Think of it like sorting a giant pile of LEGO pieces. Instead of examining each piece individually, you dump them onto a grid, check off their properties (color, size, shape), and let the math find which pieces naturally belong together.

<img src="diagrams/pipeline.svg" width="350">

## The key insight

Many flowsheet items are **compositional** — they bundle multiple clinical ideas into one row:

<img src="diagrams/compositional.svg" width="420">

> The nurse charts one row ("RLE Edema") but it encodes two OMOP concepts: the observation (Edema) and the body site (Right Lower Extremity).

FCA discovers these compositions automatically by finding items that share the same properties:

<img src="diagrams/family.svg" width="420">

All six items share the same clinical assessment (edema) with the same value options (None/Trace/1+/2+/3+/4+). They differ only in body site. So a human reviewer approves the **family once**, not each item separately.

## The three categories

| Category | What it means | Example | How it maps | Count |
|----------|--------------|---------|-------------|-------|
| **A (Atomic)** | Standalone clinical item — no body site or laterality | Heart Rate, SpO2, Pain Score | One source item → one OMOP code | ~16,200 |
| **B (Compositional)** | Bundles body site or laterality with an assessment | RLE Edema, L Breath Sounds, R Pupil Size | OMOP observation code + body site qualifier (2 rows) | ~1,500 |
| **C (Unmappable)** | No clinical assessment detected by FCA regex | "Did patient follow plan?", template headers | Initially `noMatch`; rescued via clinical review pass | ~38,200 |

## What each file does

<img src="diagrams/modules.svg" width="490">

### Step-by-step

1. **`build_context.py`** — Reads the master extract (162K template-group-row combos from Epic Clarity) + custom list values (311K dropdown options). Deduplicates to ~56K unique items. For each item, parses the display name (`name_parser.py`), classifies the template (`template_classifier.py`), and classifies the value domain (`value_domain_classifier.py`) using dictionaries from `constants.py`. Outputs a binary matrix: items × ~300 attributes.

2. **`compute_lattice.py`** — Runs the NextClosure algorithm (Ganter 1984) on the binary matrix. Finds all "formal concepts" — maximal groups of items sharing identical attribute sets. Uses a 2-pass strategy: coarse (structural + assessment) then fine (body site + laterality refinement).

3. **`classify_concepts.py`** — Labels each formal concept as A (atomic), B (compositional), or C (unmappable) based on whether it has assessment attributes, body site/laterality attributes, or neither.

4. **`generate_mappings.py`** — Converts classified concepts into three CSVs:
   - `atomic_items.csv` — A items (need existing or manual OMOP mapping)
   - `compositional_mapping.csv` — B items with assessment + qualifier concept IDs
   - `unmappable_items.csv` — C items with reasons

5. **`build_mapping_csv.py`** — Merges FCA outputs into a single `mapping.csv` for the CVB Builder pipeline:
   - **A items**: Preserves existing hand-curated mappings from prior `mapping.csv`
   - **B items**: Generates multi-row entries (`Maps to` → observation + `Has finding site` → body site)
   - **C items**: Emits as `noMatch` (later rescued by clinical review)

6. **`validate.py`** — Checks completeness (every item classified), consistency (no items in multiple categories), and lattice validity.

### Clinical review pass (ongoing)

The FCA regex missed ~4,000 clinically valuable items in category C. A separate **clinical review pipeline** (`enrich_unmappable.py` → sub-agent orchestration → `accumulate_reviews.py`) walks through all 38K C items with OHDSI vocabulary lookups to rescue mappable items. Progress: ~17K of 38K reviewed, ~10K rescued so far.

## Running the pipeline

```bash
cd /Users/danielsmith/git_repos/org__Emory-OMOP/CVB/EU2_Flowsheets
uv sync
bash fca/run_pipeline.sh
```

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Input CSVs in `raw_for_fca/` (exported from Epic Clarity)

### Input files

| File | Source | Rows |
|------|--------|------|
| `raw_for_fca/fca_master_extract*.csv` | Clarity 4-table join (template → group → row) | ~162K |
| `raw_for_fca/fca_custom_lists*.csv` | Clarity IP_FLO_CUSTOM_LIST | ~311K |

### Output files

| File | Location | Description |
|------|----------|-------------|
| `fca_context.json` | `raw_for_fca/` | The formal context (item list + attribute list) |
| `fca_incidence.npz` | `raw_for_fca/` | Sparse binary matrix (items × attributes) |
| `fca_metadata.json` | `raw_for_fca/` | Per-item metadata for downstream use |
| `fca_lattice.json` | `raw_for_fca/` | Concept lattice (all families found) |
| `fca_classification.json` | `raw_for_fca/` | A/B/C category for each family |
| `fca_validation.json` | `raw_for_fca/` | Validation report |
| `compositional_mapping.csv` | `Mappings/` | B items: observation + qualifier concept IDs |
| `atomic_items.csv` | `Mappings/` | A items: standalone clinical items |
| `unmappable_items.csv` | `Mappings/` | C items: documented reasons |
| `mapping.csv` | `Mappings/` | Final merged mapping for CVB Builder |

## Why FCA instead of doing it by hand?

| | Doing it by hand | FCA pipeline |
|---|---|---|
| **Reviews needed** | 55,938 items, one at a time | ~500-2,000 families |
| **Can items slip through?** | Yes — easy to miss some | No — mathematically guaranteed complete |
| **Reproducible?** | Depends on who does it | Same input always gives same output |
| **Body site preserved?** | Often lost (mapped to generic "Edema") | Kept via qualifier codes |
| **New items added later?** | Start from scratch | Automatically inherit family mapping |

## References

- Ganter, B. & Wille, R. (1999). *Formal Concept Analysis: Mathematical Foundations.* Springer.
- Wille, R. (1982). "Restructuring lattice theory." *Ordered Sets*, NATO ASI Series.
- [SSSOM Specification](https://mapping-commons.github.io/sssom/) — mapping provenance standard
- [OHDSI Forums: Representing Laterality](https://forums.ohdsi.org/t/representing-laterality-general-questions-about-post-coordination/16872)
