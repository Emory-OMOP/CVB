# project flow

## Lineage Diagrams

### Step 1: create-general-concepts

**Purpose**: Registers the custom PSYCHIATRY vocabulary by creating a new concept in vocab.concept and linking it in vocab.vocabulary. This establishes the anchor point for all subsequent mappings and updates.

**Why it Matters**: This step is like adding a new “dictionary” to OMOP. By inserting PSYCHIATRY into both concept and vocabulary, all later mappings and updates know where to attach psychiatry-specific concepts. Without this anchor, the pipeline would have no recognized home for the new terminology.

```mermaid
%% Column-level lineage: create-general-concepts.sql
%% Styles: table=blue, const=yellow, file=green

flowchart LR
  %% Table nodes
  VC[vocab.concept]:::table
  VV[vocab.vocabulary]:::table

  %% Const sources
  C_ID[CONST 2072499999]:::const
  C_NAME[CONST PSYCHIATRY]:::const
  C_DOMAIN[CONST Metadata]:::const
  C_VOCAB_ID[CONST Vocabulary]:::const
  C_CLASS[CONST Vocabulary_class]:::const
  C_STD[CONST S]:::const
  C_CODE[CONST OMOP_generated]:::const
  C_VSTART[CONST now_date]:::const
  C_VEND[CONST 2099_12_31]:::const
  C_INV[CONST NULL]:::const

  V_ID[CONST PSYCHIATRY]:::const
  V_NAME[CONST Psychiatry_Custom_Terminology]:::const
  V_REF[CONST OMOP_generated]:::const
  V_VER[CONST now_date]:::const

  %% Edges to vocab.concept
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

  %% Link concept to vocabulary_concept_id
  VC -->|concept_id -> vocabulary_concept_id| VV

  %% Edges to vocab.vocabulary
  V_ID -->|vocabulary_id| VV
  V_NAME -->|vocabulary_name| VV
  V_REF -->|vocabulary_reference| VV
  V_VER -->|vocabulary_version| VV

  %% Legend
  subgraph Legend [Legend]
    L1[Table Node]:::table
    L2[Const / Literal]:::const
    L3[File / CSV Input]:::file
  end

  %% Styles
  classDef table fill:#e6f2ff,stroke:#3366cc,stroke-width:1px,color:#000,rx:6,ry:6;
  classDef const fill:#fff2cc,stroke:#cc9900,stroke-width:1px,color:#000,rx:4,ry:4;
  classDef file fill:#e6ffe6,stroke:#339933,stroke-width:1px,color:#000,rx:4,ry:4;
```

