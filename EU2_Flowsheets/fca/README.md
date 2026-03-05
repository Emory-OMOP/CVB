# FCA Flowsheet Mapping Pipeline

## What is this?

Hospitals record patient data using **flowsheet items** — things like "Heart Rate", "RLE Edema", or "Breath Sounds Left." Our hospital has **25,166** of these items, and we need to translate each one into a standard medical coding system called **OMOP** so researchers can study the data.

The catch: many flowsheet items aren't simple. "RLE Edema" really means **two things at once**: "Edema" (the observation) + "Right Lower Extremity" (the body location). There's no single standard code for that combination. We can't just match them one-to-one.

This pipeline uses a branch of mathematics called **Formal Concept Analysis (FCA)** to automatically find families of related items, figure out what each family means, and generate the right translations — including the ones that need two codes instead of one.

## How it works

Think of it like sorting a giant pile of LEGO pieces. Instead of examining each piece individually, you dump them onto a grid, check off their properties (color, size, shape), and let the math find which pieces naturally belong together.

```mermaid
flowchart TD
    A["📋 Step 1: Export Data\n162K template rows + 311K dropdown values\nfrom Epic Clarity database"] --> B

    B["🔲 Step 2: Build the Grid\nFor each of 25K items, check off ~300\nbinary properties like body site,\nleft/right, numeric, severity scale"] --> C

    C["🔍 Step 3: Find Natural Groups\nMath scans the grid for 'maximal rectangles'\n= largest groups sharing identical properties\nDone in 2 passes: rough then fine"] --> D

    D["🏷️ Step 4: Label Each Group\nA = Atomic (simple 1:1 match)\nB = Compositional (needs qualifier)\nC = Unmappable (not clinical)"] --> E

    E["📄 Step 5: Generate Translations\nAtomic → direct OMOP code\nCompositional → OMOP code + body site qualifier\nUnmappable → documented reason"] --> F

    F["✅ Step 6: Validate\nEvery item classified?\nNo items missed?\nMath checks out?"]
```

## The key insight

Many flowsheet items are **compositional** — they bundle multiple clinical ideas into one row:

```mermaid
graph LR
    subgraph "What the nurse sees (1 row)"
        A["RLE Edema"]
    end

    subgraph "What it actually means (2 concepts)"
        B["Edema\n(the observation)"]
        C["Right Lower Extremity\n(the body location)"]
    end

    A --> B
    A --> C
```

FCA discovers these compositions automatically by finding items that share the same properties:

```mermaid
graph TD
    subgraph "FCA finds this family"
        R["RLE Edema"]
        L["LLE Edema"]
        RU["RUE Edema"]
        LU["LUE Edema"]
        F["Facial Edema"]
        G["Generalized Edema"]
    end

    subgraph "Shared properties (the 'intent')"
        P1["assessment: edema"]
        P2["val_type: custom_list"]
        P3["value_domain: ordinal_severity"]
    end

    R --- P1
    L --- P1
    RU --- P1
    LU --- P1
    F --- P1
    G --- P1
```

All six items share the same clinical assessment (edema) with the same value options (None/Trace/1+/2+/3+/4+). They differ only in body site. So a human reviewer approves the **family once**, not each item separately.

## What each file does

```mermaid
flowchart LR
    subgraph "Input CSVs"
        M["fca_master_extract.csv\n162K rows"]
        CL["fca_custom_lists.csv\n311K rows"]
    end

    subgraph "Python Modules"
        direction TB
        CON["constants.py\nDictionaries for\nbody sites, assessments,\nOMOP concept IDs"]
        NP["name_parser.py\nReads item names\nlike 'RLE Edema'\nand extracts meaning"]
        TC["template_classifier.py\nSorts templates into\ncategories like\n'cardiology' or 'OB'"]
        VD["value_domain_classifier.py\nLooks at dropdown options\nto figure out the\nvalue type (severity, yes/no, etc.)"]
        BC["build_context.py\nCombines everything\ninto the big grid\n(the 'formal context')"]
        CL2["compute_lattice.py\nThe core math —\nfinds all natural\nfamilies in the grid"]
        CC["classify_concepts.py\nLabels each family\nas A, B, or C"]
        GM["generate_mappings.py\nWrites the actual\ntranslation files"]
        VA["validate.py\nChecks everything\nfor correctness"]
    end

    subgraph "Outputs"
        CTX["fca_context.json\nThe grid"]
        LAT["fca_lattice.json\nThe families"]
        CMP["compositional_mapping.csv\nTranslations with qualifiers"]
        ATM["atomic_items.csv\nSimple 1:1 translations"]
        UNM["unmappable_items.csv\nItems that can't be translated"]
    end

    M --> BC
    CL --> BC
    CON --> NP
    CON --> TC
    CON --> VD
    NP --> BC
    TC --> BC
    VD --> BC
    BC --> CTX
    CTX --> CL2
    CL2 --> LAT
    LAT --> CC
    CC --> GM
    GM --> CMP
    GM --> ATM
    GM --> UNM
    CTX --> VA
    LAT --> VA
    CC --> VA
```

## The three categories

| Category | What it means | Example | How it maps | ~Count |
|----------|--------------|---------|-------------|--------|
| **A (Atomic)** | A simple, standalone clinical item | Heart Rate, SpO2, Pain Score | One source item → one OMOP code | ~1,000 |
| **B (Compositional)** | Bundles body site or laterality with an assessment | RLE Edema, L Breath Sounds, R Pupil Size | OMOP observation code + body site qualifier | ~15,000 |
| **C (Unmappable)** | Administrative, workflow, or not clinical | "Did patient follow plan?", template headers | Documented as noMatch with a reason | ~9,000 |

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
| `compositional_mapping.csv` | `Mappings/` | Translations needing body site qualifiers |
| `atomic_items.csv` | `Mappings/` | Simple 1:1 translation candidates |
| `unmappable_items.csv` | `Mappings/` | Items that can't be translated, with reasons |

## Why FCA instead of doing it by hand?

| | Doing it by hand | FCA pipeline |
|---|---|---|
| **Reviews needed** | 25,166 items, one at a time | ~500–2,000 families |
| **Can items slip through?** | Yes — easy to miss some | No — mathematically guaranteed complete |
| **Reproducible?** | Depends on who does it | Same input always gives same output |
| **Body site preserved?** | Often lost (mapped to generic "Edema") | Kept via qualifier codes |
| **New items added later?** | Start from scratch | Automatically inherit family mapping |

## References

- Ganter, B. & Wille, R. (1999). *Formal Concept Analysis: Mathematical Foundations.* Springer.
- Wille, R. (1982). "Restructuring lattice theory." *Ordered Sets*, NATO ASI Series.
- [SSSOM Specification](https://mapping-commons.github.io/sssom/) — mapping provenance standard
- [OHDSI Forums: Representing Laterality](https://forums.ohdsi.org/t/representing-laterality-general-questions-about-post-coordination/16872)
