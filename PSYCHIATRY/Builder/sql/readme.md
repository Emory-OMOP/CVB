# project flow

## Lineage Diagrams

### Legend
```mermaid
flowchart LR
 subgraph Legend["Legend"]
        L1["Table Node"]
        L2["Const / Literal"]
        L3["File / CSV Input"]
        L4["Logic / Decision"]
        L5["Sequence / Auto-increment"]
        L6["Relationships"]
  end

     L1:::table
     L2:::const
     L3:::file
     L4:::logic
     L5:::sequence
     L6:::relt
    classDef table fill:#e6f2ff,stroke:#3366cc,stroke-width:1px,color:#000,rx:6,ry:6
    classDef const fill:#fff2cc,stroke:#cc9900,stroke-width:1px,color:#000,rx:4,ry:4
    classDef file fill:#e6ffe6,stroke:#339933,stroke-width:1px,color:#000,rx:4,ry:4
    classDef sequence fill:#a3d0D4,stroke:#426871,stroke-width:1px,color:#000,rx:6,ry:6
    classDef logic fill:#efe6ff,stroke:#6b3fa0,stroke-width:1px,color:#000,rx:6,ry:6
    classDef relt fill:#d3d3d3,stroke:#d3d3d3,stroke-width:1px,color:#000,rx:6,ry:6
```

### Step 1: create-general-concepts

**Purpose**: Registers the custom PSYCHIATRY vocabulary by creating a new concept in vocab.concept and linking it in vocab.vocabulary. This establishes the anchor point for all subsequent mappings and updates.

**Why it Matters**: This step is like adding a new “dictionary” to OMOP. By inserting PSYCHIATRY into both concept and vocabulary, all later mappings and updates know where to attach psychiatry-specific concepts. Without this anchor, the pipeline would have no recognized home for the new terminology.

```mermaid
%% Column-level lineage: create-general-concepts.sql (Step 1)
%% Functions/literals quoted; legend included only in Step 1.

flowchart LR
  VC[vocab.concept]:::table
  VV[vocab.vocabulary]:::table

  C_ID["CONST 2072499999"]:::const
  C_NAME["CONST 'PSYCHIATRY'"]:::const
  C_DOMAIN["CONST 'Metadata'"]:::const
  C_VOCAB_ID["CONST 'Vocabulary'"]:::const
  C_CLASS["CONST 'Vocabulary'"]:::const
  C_STD["CONST 'S'"]:::const
  C_CODE["CONST 'OMOP generated'"]:::const
  C_VSTART["CONST now()::date"]:::const
  C_VEND["CONST '2099-12-31'"]:::const
  C_INV["CONST NULL"]:::const

  V_ID["CONST 'PSYCHIATRY'"]:::const
  V_NAME["CONST 'Psychiatry_Custom_Terminology'"]:::const
  V_REF["CONST 'OMOP generated'"]:::const
  V_VER["CONST now()::date"]:::const

  C_ID -->|concept_id| VC
  C_NAME -->|concept_name| VC
  C_DOMAIN -->|domain_id| VC
  C_VOCAB_ID -->|vocabulary_id| VC
  C_CLASS -->|concept_class_id| VC
  C_STD -->|standard_concept| VC
  C_CODE -->|concept_code| VC
  C_VSTART -->|valid_start_date| VC
  C_VEND -->|valid_end_date| VC
  C_INV -->|invalid_reason| VC

  VC -->|"concept_id -> vocabulary_concept_id"| VV

  V_ID -->|vocabulary_id| VV
  V_NAME -->|vocabulary_name| VV
  V_REF -->|vocabulary_reference| VV
  V_VER -->|vocabulary_version| VV

  subgraph Legend [Legend]
    L1[Table Node]:::table
    L2[Const / Literal]:::const
  end

  classDef table fill:#e6f2ff,stroke:#3366cc,stroke-width:1px,color:#000,rx:6,ry:6;
  classDef const fill:#fff2cc,stroke:#cc9900,stroke-width:1px,color:#000,rx:4,ry:4;
```

### Step 2: source-ddl.sql
**Purpose:**
Creates the staging and helper tables used throughout the pipeline: pubilc.psych_mapping_emory, public.source_to_update, public.vocab_logger, and ensures permanent helper tables vocab.mapping_exceptions and vocab.review_ids exist.

**Why it matters:**
These tables are the workspace and control tables for loading raw mappings, tracking review metadata, logging counts/messages, and handling exception/reviewer lookups. Without them, later steps that load CSVs, transform mappings, and compute deltas have nowhere to land or reference.

```mermaid
%% Column-level lineage: source-ddl.sql (Step 2)
%% Pure DDL – creates tables. No column-level lineage from Step 1.

flowchart LR
  T_PM[public.psych_mapping_emory]:::table
  T_STU[public.source_to_update]:::table
  T_VL[public.vocab_logger]:::table
  T_ME[vocab.mapping_exceptions]:::table
  T_RI[vocab.review_ids]:::table

  classDef table fill:#e6f2ff,stroke:#3366cc,stroke-width:1px,color:#000,rx:6,ry:6;
  classDef const fill:#fff2cc,stroke:#cc9900,stroke-width:1px,color:#000,rx:4,ry:4;
  classDef file fill:#e6ffe6,stroke:#339933,stroke-width:1px,color:#000,rx:4,ry:4;
```

### Step 3: load-source.sql
**Purpose:**
Transforms rows from temp.psych_mapping into a normalized staging table temp.source_to_update, applying trims, length caps, casts, default class/domain, date normalization, and simple casing.

**Why it matters:**
This step converts the raw mapping sheet into a typed, consistent staging shape used by all downstream QA and update logic. It enforces basic hygiene (non-blank codes/descriptions, safe string lengths, domain defaults, type casts) so later SQL can rely on schema-clean inputs.

```mermaid
%% UPDATED Column-level lineage: load-source.sql (Step 3)
%% Styles: table=blue, const=yellow, file=green, logic=purple

flowchart LR

%% Tables
PM[public.psych_mapping_emory]:::table
STU[public.source_to_update]:::table

%% Constants
K_CLASS[CONST 'Suppl Concept']:::const
K_METADATA[CONST 'Metadata']:::const
K_TODAY[CONST CURRENT_DATE]:::const
K_NULL_CODE[CONST NULL]:::const
K_NULL_AFFIL[CONST NULL]:::const

%% Decision for COALESCE(target_domain_id,'Metadata') -> source_domain_id
TDI[target_domain_id]:::table
SDI[source_domain_id]:::table
D1{target_domain_id is NULL?}:::logic

PM --> TDI
TDI --> D1
D1 -- No --> SDI
D1 -- Yes --> K_METADATA
K_METADATA --> SDI

%% Remaining column-level mappings (functions quoted)
PM -->|"TRIM(LEFT(source_concept_code,50))" -> source_concept_code| STU
K_NULL_CODE -->|source_concept_id| STU
PM -->|source_vocabulary_id -> source_vocabulary_id| STU
K_CLASS -->|source_concept_class_id| STU
PM -->|"LEFT(source_description,255)" -> source_description| STU
PM -->|"LEFT(source_description_synonym,255)" -> source_description_synonym| STU
K_TODAY -->|valid_start| STU
PM -->|relationship_id -> relationship_id| STU
PM -->|predicate_id -> predicate_id| STU
PM -->|"confidence::FLOAT" -> confidence| STU
PM -->|"target_concept_id::INTEGER" -> target_concept_id| STU
PM -->|target_concept_code -> target_concept_code| STU
PM -->|target_concept_name -> target_concept_name| STU
PM -->|target_vocabulary_id -> target_vocabulary_id| STU
PM -->|"INITCAP(target_domain_id)" -> target_domain_id| STU
PM -->|"decision::INT" -> decision| STU
PM -->|"review_date_mm_dd_yy::DATE" -> review_date| STU
PM -->|reviewer_name -> reviewer_name| STU
PM -->|reviewer_specialty -> reviewer_specialty| STU
PM -->|reviewer_comment -> reviewer_comment| STU
PM -->|orcid_id -> orcid_id| STU
K_NULL_AFFIL -->|reviewer_affiliation_name| STU
PM -->|status -> status| STU
PM -->|author_comment -> author_comment| STU
PM -->|change_required -> change_required| STU

%% Connect decision result into target table
SDI --> STU

%% Styles
classDef table fill:#e6f2ff,stroke:#3366cc,stroke-width:1px,color:#000,rx:6,ry:6;
classDef const fill:#fff2cc,stroke:#cc9900,stroke-width:1px,color:#000,rx:4,ry:4;
classDef file fill:#e6ffe6,stroke:#339933,stroke-width:1px,color:#000,rx:4,ry:4;
classDef logic fill:#efe6ff,stroke:#6b3fa0,stroke-width:1px,color:#000,rx:6,ry:6;
```

### Step 4a: revert-id-sequence.sql

**Purpose:**
Drops/recreates vocab.master_id_assignment to generate descending custom IDs in a reserved range, then setval to the minimum available concept ID (or a fallback).

**Why it matters:**
This ensures stable, unique IDs for new psychiatry concepts that don’t overlap with OMOP core IDs. By anchoring the sequence in a controlled range, the pipeline can always assign valid identifiers without clashing with upstream vocabularies.

```mermaid
%% Column-level lineage: revert-id-sequence.sql (Step 4)
%% Styles: table=blue, const=yellow, file=green, logic=purple
%% Decision node models COALESCE(min(concept_id), 2072499886)

flowchart LR

%% Tables / Objects
VC[vocab.concept]:::sequence
SEQ[vocab.master_id_assignment]:::sequence

%% Constants (sequence properties + fallback)
C_MIN["CONST {reserved 2b lower bound}"]:::const
C_MAX["CONST {reserved 2b lower bound}"]:::const
C_START["CONST {known starting place}"]:::const
C_FALLBACK["CONST {START + 1}"]:::const
C_STD["CONST 'S'"]:::const

%% Aggregation + filter logic to find MIN(concept_id) in band where standard_concept='S'
F1["'FILTER concept_id BETWEEN {lower bound + 1} AND {upper bound - 1} AND standard_concept=''S'''"]:::logic
MINC["'MIN(concept_id) from filtered'"]:::logic

VC --> F1 --> MINC

%% Decision: does a MIN(concept_id) exist?
D1{"'MIN(concept_id) exists?'" }:::logic
MINC --> D1

%% Yes -> use MIN(concept_id) for setval
D1 -- Yes --> SEQ

%% No -> use fallback 2072499886
D1 -- No --> C_FALLBACK --> SEQ

%% Sequence property wiring
C_MIN -->|"MINVALUE"| SEQ
C_MAX -->|"MAXVALUE"| SEQ
C_START -->|"START"| SEQ

%% (Optional) show the standard_concept='S' filter attachment
C_STD -->|"filter"| F1

  subgraph Legend [Legend]
    L2[Const / Literal]:::const
    L4[Logic / Decision]:::logic
    L5[Sequence / Auto-increment]:::sequence
  end

  classDef table fill:#e6f2ff,stroke:#3366cc,stroke-width:1px,color:#000,rx:6,ry:6;
  classDef const fill:#fff2cc,stroke:#cc9900,stroke-width:1px,color:#000,rx:4,ry:4;
  classDef file fill:#e6ffe6,stroke:#339933,stroke-width:1px,color:#000,rx:4,ry:4;
  classDef sequence fill:#a3d0D4,stroke:#426871,stroke-width:1px,color:#000,rx:6,ry:6;
  classDef logic fill:#efe6ff,stroke:#6b3fa0,stroke-width:1px,color:#000,rx:6,ry:6;
 
```

### Step 4b: revert-id-sequence.sql

**under construction here! complex step**

**Purpose:**
Builds check tables (temp.CONCEPT_CHECK_S, temp.CONCEPT_CHECK_NS and their raw/working copies) to compare new psychiatry mappings against existing vocabularies. It flags duplicates, exact matches, and assigns candidates for standard/non-standard IDs.

**Why it matters:**
This step is the quality gate: it filters out mappings that are already present, identifies potential duplicates, and isolates only the novel custom concepts. Without it, the pipeline could introduce redundant or conflicting concept definitions into the OMOP vocabulary.

```mermaid
%% Column-level lineage: revert-id-sequence.sql (Step 4)
%% Styles: table=blue, const=yellow, file=green, logic=purple
%% Functions/casts quoted. Decisions modeled with purple diamond nodes.

flowchart TB

  %% Sources
  STU[temp.source_to_update]:::table
  VC[vocab.concept]:::table

  %% Decision for standard vs non-standard
  D_STD{standard_concept = 'S'}:::logic
  D_NS{standard_concept IS NULL}:::logic

  %% Outputs (with raw/working tables)
  CCS[temp.CONCEPT_CHECK_S]:::table
  CCS_RAW[temp.CONCEPT_CHECK_S_RAW]:::table
  SDM[temp.SRC_DESC_MATCH]:::table
  CCNS[temp.CONCEPT_CHECK_NS]:::table
  CCNS_RAW[temp.CONCEPT_CHECK_NS_RAW]:::table

  %% Join logic for standard custom concepts
  STU -->|"TRIM(UPPER(source_concept_code))"| D_STD
  VC -->|"TRIM(UPPER(concept_code))"| D_STD
  D_STD --> CCS

  %% Filters applied to CCS
  CCS -->|"predicate_id = 'skos:noMatch'"| CCS
  CCS -->|"source_description NOT IN (SELECT source_description FROM temp.source_to_update WHERE predicate_id = 'skos:exactMatch')"| CCS

  %% Derivative tables
  CCS --> CCS_RAW
  CCS --> SDM

  %% Join logic for non-standard custom concepts
  STU -->|"TRIM(UPPER(source_concept_code))"| D_NS
  VC -->|"TRIM(UPPER(concept_code))"| D_NS
  D_NS --> CCNS
  CCNS --> CCNS_RAW

  %% Deduplication steps
  CCS -->|"DELETE duplicates by source_description"| CCS
  CCNS -->|"DELETE duplicates by source_description"| CCNS

  %% Remove rows with concept_name already populated
  CCNS -->|"DELETE WHERE concept_name IS NOT NULL"| CCNS

  %% Styles
  classDef table fill:#e6f2ff,stroke:#3366cc,stroke-width:1px,color:#000,rx:6,ry:6;
  classDef const fill:#fff2cc,stroke:#cc9900,stroke-width:1px,color:#000,rx:4,ry:4;
  classDef file fill:#e6ffe6,stroke:#339933,stroke-width:1px,color:#000,rx:4,ry:4;
  classDef logic fill:#efe6ff,stroke:#6b3fa0,stroke-width:1px,color:#000,rx:6,ry:6;
```
