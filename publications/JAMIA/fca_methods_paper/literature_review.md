# Literature Review: FCA + LLM for Flowsheet-to-OMOP Mapping

**Last updated**: 2026-03-06
**Status**: Deep research pass — ready for framing discussion

---

## 1. Flowsheet Data in OMOP — The Problem Space

### 1.1 Scale and heterogeneity of flowsheet data

Flowsheet data is one of the richest yet most underutilized sources of observational health data. Individual institutions report **25,000–56,000 distinct flowsheet item types** across thousands of templates (Seto et al. 2021, our Emory data). These items capture vital signs, nursing assessments, clinical scores, device parameters, and intake/output — data critical to understanding inpatient care but largely absent from standardized research datasets.

**Key challenge**: Flowsheet items are locally defined, not standardized across institutions, and exhibit extreme naming heterogeneity. The same clinical concept may appear under dozens of different names across templates, while a single item name may bundle multiple clinical dimensions (body site + laterality + assessment type).

### 1.2 Prior work on flowsheet-to-OMOP integration

| Paper | Year | Venue | Scale | Approach | Key Finding |
|-------|------|-------|-------|----------|-------------|
| **Waitman et al.** "Modeling Flowsheet Data to Support Secondary Use" | 2015 | AMIA | Foundational | Conceptual framework | Identified key challenges: volume, heterogeneity, site-specific customization |
| **Seto et al.** "Integrating Flowsheet Data in OMOP CDM for Clinical Research" | 2021 | arXiv:2109.08235 | 25,777 row types, 1,883 templates | Two approaches: structural + LOINC-based | Structural approach computationally simple but limited utility; LOINC mapping labor-intensive but higher utility. Mentions FloMap tool and stacked ML (f2=0.74). Neither tool open-sourced. |
| **Talapova et al.** "Mapping of Critical Care EHR Flowsheet data to OMOP CDM via SSSOM" | 2023 | OHDSI Symposium | Critical care subset | SSSOM (Simple Standard for Sharing Ontological Mappings) | Structural mapping approach — does not use clinical reasoning per item. Limited to critical care domain. |
| **Austin et al.** "Exploring CDM coverage of nursing flowsheet data: SNOMED CT and LOINC mapping" | 2025 | JAMIA Open | 1,170 concepts, 1,831 values | Manual expert mapping | **65.5% of concepts mapped**, 56.0% of values mapped. Average 1.19 min/concept. Demonstrates significant coverage gaps remain. |
| **Adams et al.** "Extending OMOP CDM for Critical Care Medicine (C2D2)" | 2025 | Critical Care Medicine | 226 C2D2 elements | Three-tier semantic matching + LLM | 49.6% full match, 46.4% partial, 4.0% no match. LLM matching F1=0.707 at threshold 0.90. Key gaps: ventilator parameters, composite scoring, advanced organ support. |
| **French et al.** "Coverage of functional assessments in OMOP CDM" | 2024 | medRxiv | 160 assessments (neuro + ortho) | Manual expert mapping | ~50% of functional assessments unmappable in OMOP. Multi-concept mapping common (2.2–4.3 concept IDs per assessment). |

### 1.3 FloMap tool

FloMap (University of Minnesota) is a collaborative tool for mapping local EHR flowsheet data to information models (Johnson et al., AMIA CRI 2017). Uses automated rules to find and map flowsheet measures to information model concepts. Validated across 8 health systems. **Not open-sourced or productized.** Focuses on structural mapping without clinical reasoning.

### 1.4 Gap summary

All prior flowsheet mapping work falls into one of two categories:
1. **Structural/pattern-based** (FloMap, SSSOM, stacked ML): Scalable but accuracy-limited (~55-74%), misses contextually clinical items
2. **Manual expert review** (Austin 2025): Accurate but doesn't scale (~1 min/concept × 56K items = infeasible)

**No published work combines automated structural triage with AI-assisted clinical reasoning.**

---

## 2. General OMOP Vocabulary Mapping — Tools and Automation

### 2.1 Usagi (OHDSI standard tool)

The de facto tool for OMOP vocabulary mapping. Uses fuzzy string matching to suggest concept matches, but all matches require manual review. Key limitations:
- No semantic understanding — relies on lexical similarity
- Matching scores often low for non-English or compositional terms
- Index creation is computationally expensive (hours)
- One study found only 55% acceptable matches for auto-translated terms

### 2.2 Transformer-based approaches

| Paper | Year | Approach | Performance |
|-------|------|----------|-------------|
| **Zhou et al.** "Sentence Transformer-based NLP for Schema Mapping to OMOP" | 2024 | Transformer embeddings for drug mapping | 96.5% accuracy (top-200 drugs), 83.0% (random-200). Outperforms Usagi (90.0%/70.0%) and SFR-Embedding-Mistral (89.5%/66.5%). |
| **Llettuce** (open-source tool) | 2024 | Local LLM + vector store + fuzzy matching | Runs on consumer hardware. GDPR-compliant local deployment. Targets OMOP vocabulary. MIT license. |
| **CaRROT tools** (UK) | 2024 | Collaborative mapping toolset | Mapped ~10 million individuals' records. Focus on consistent mapping decisions. |

### 2.3 LLM-based OMOP mapping (emerging 2025 landscape)

| Paper | Year | Venue | Approach | Performance |
|-------|------|-------|----------|-------------|
| **Adams et al.** "Breaking Digital Health Barriers Through LLM-Based OMOP Mapping" | 2025 | JMIR | GPT-3 embeddings + three-tier semantic matching (exact → linguistic → cosine) | AUC=0.9975, Precision 0.92–0.99, Recall 0.88–0.97. Validated on chronic pain, opioid, COVID-19 domains. |
| **JMIR Med Inform** "LLMs for Automating Clinical Trial Criteria to OMOP Queries" | 2025 | JMIR Med Inform | Multi-LLM evaluation (8 models, 5 prompting strategies) | Hallucination rates 21-50%. Smaller models sometimes outperform larger ones. 760 SQL attempts evaluated. |
| **Ahn et al.** "Agentic MCP Framework for Medical Concept Standardization" | 2025 | arXiv:2509.03828 | MCP (Model Context Protocol) + LLM with real-time vocab lookup | 100% retrieval success (48/48) with MCP vs. 0% without. Zero hallucinated concept IDs. 5.49s/query average. |
| **OHNLP omop_mcp** (open-source) | 2025 | GitHub | MCP server for LLM-assisted OMOP mapping | Zero-training, hallucination-preventive. Structured reasoning outputs. |

### 2.4 Key insight from LLM literature

The **Ahn et al. 2025** paper is the closest methodological parallel to our Stage 2 — they also use an LLM with real-time vocabulary lookup to prevent hallucination. Key difference: they map individual clinical terms in isolation, while **our approach maps flowsheet items using enriched metadata (template context, group names, value enumerations, clinical instrument recognition)**.

---

## 3. Formal Concept Analysis — Foundations and Applications

### 3.1 Mathematical foundations

FCA was formalized by **Ganter & Wille (1999)** in *Formal Concept Analysis: Mathematical Foundations* (Springer). Core framework:
- **Formal context** (G, M, I): G = objects, M = attributes, I = incidence relation
- **Galois connection** between object extents and attribute intents
- **Concept lattice**: ordered hierarchy of all formal concepts (maximal rectangles in the incidence matrix)

### 3.2 FCA in biomedical informatics

| Paper | Year | Venue | Application |
|-------|------|-------|-------------|
| **Cimiano et al.** "Context-based ontology building support in clinical domains using FCA" | 2003 | Int J Hum-Comput Stud | FCA + NLP for cardiovascular ontology construction. Demonstrates FCA utility for discovering concept hierarchies from clinical data. |
| **Zhao & Ichise** "Matching biomedical ontologies based on FCA" | 2018 | J Biomed Semantics | FCA-Map system: identifies 1:1 mappings, complex mappings, and property correspondences between ontologies. Uses lexical + structural knowledge. |
| **Shen et al.** "Clinical MetaData Ontology (CMDO)" | 2019 | PMC | Classification of clinical data elements based on semantics using General Formal Ontology method. |
| **ACM Computing Surveys** "FCA Applications in Bioinformatics" | 2022 | ACM Comput. Surv. | Comprehensive survey: gene expression, cancer classification, healthcare informatics, biomedical ontologies, drug design. **Does not cover EHR-to-vocabulary mapping.** |

### 3.3 FCA gap

FCA has been applied to:
- Ontology construction (Cimiano 2003)
- Ontology matching/alignment (Zhao & Ichise 2018, FCA-Map)
- Gene expression analysis, drug design, biomedical classification (ACM survey 2022)

**FCA has NOT been applied to**:
- EHR data element classification/triage
- Flowsheet item mappability assessment
- Pre-processing step for vocabulary mapping pipelines

Our use of FCA to **classify flowsheet items by mappability category** (atomic/compositional/unmappable) based on attribute lattices is novel.

---

## 4. Combined FCA + LLM — Novelty Analysis

### What exists (individual components):

| Component | Prior work | Our approach |
|-----------|-----------|--------------|
| **Structural flowsheet classification** | FloMap rules, SSSOM structural matching, stacked ML (f2=0.74) | FCA lattice-based classification using attribute structure (value types, units, custom lists, template co-occurrence) |
| **LLM vocabulary mapping** | Adams 2025 (GPT-3 embeddings), Ahn 2025 (MCP + LLM), Llettuce (local LLM) | LLM clinical reasoning with enriched metadata + real-time OHDSI vocabulary search |
| **Flowsheet-to-OMOP** | Seto 2021 (structural + LOINC), Austin 2025 (manual), Talapova 2023 (SSSOM) | Two-stage: FCA triage → LLM residual review |
| **FCA in clinical informatics** | Ontology building (Cimiano 2003), ontology matching (Zhao 2018) | EHR data element classification for mappability |

### What does NOT exist (our contribution):

1. **FCA for EHR item classification** — No published work uses FCA to classify clinical data elements by mappability. Our stratified NextClosure algorithm processes 56K items in seconds.

2. **Two-stage pipeline (structural triage + clinical reasoning)** — All prior approaches are either purely structural OR purely expert/LLM-driven. We combine both, using FCA output to direct LLM effort to the items that need it most.

3. **LLM reasoning with template/group context** — Prior LLM mapping work (Adams 2025, Ahn 2025) maps isolated terms. Our LLM uses the full hierarchical context (template → group → row) plus value enumerations to resolve ambiguity.

4. **Scale** — 55,938 items is the largest published flowsheet mapping effort. Austin 2025 mapped 1,170 concepts; Seto 2021 reported 25,777 row types but mapped a subset; Adams C2D2 mapped 226 elements.

---

## 5. Reference List

### Flowsheet / OMOP mapping (core)
1. Seto T, Sung L, Posada J, et al. "Integrating Flowsheet Data in OMOP CDM for Clinical Research." arXiv:2109.08235, 2021.
2. Austin RR, Lalich MB, Stewart K, et al. "Exploring CDM coverage of nursing flowsheet data: a pilot study using SNOMED CT and LOINC mapping." JAMIA Open 2025;8(6):ooaf168.
3. Talapova P, et al. "Mapping of Critical Care EHR Flowsheet data to OMOP CDM via SSSOM." OHDSI 2023 Symposium.
4. Adams MCB, Hurley RW, Bartels K, et al. "Extending OMOP CDM for Critical Care Medicine: C2D2 Framework." Critical Care Medicine 2025.
5. French MA, Hartman P, et al. "Coverage of functional assessments in OMOP CDM." medRxiv 2024.
6. Waitman LR, et al. "Modeling Flowsheet Data to Support Secondary Use." PMC 2015.

### OMOP mapping automation
7. Zhou X, Dhingra LS, et al. "Sentence Transformer-based NLP for Schema Mapping to OMOP CDM." medRxiv 2024.
8. Adams MCB, Perkins ML, et al. "Breaking Digital Health Barriers Through LLM-Based OMOP Mapping." JMIR 2025;e69004.
9. Ahn J, Wen A, Wang N, et al. "An Agentic MCP Framework for Medical Concept Standardization." arXiv:2509.03828, 2025.
10. "LLMs for Automating Clinical Trial Criteria to OMOP CDM Queries." JMIR Med Inform 2025;e71252.
11. Llettuce: Open Source NLP Tool for Clinical Encoding. arXiv:2410.09076, 2024.

### FloMap and tools
12. Johnson S, et al. "FloMap: A Collaborative Tool for Mapping Local EHR Flowsheet Data to Information Models." AMIA CRI 2017.
13. Usagi. OHDSI vocabulary mapping tool. https://ohdsi.github.io/Usagi/

### FCA foundations and biomedical applications
14. Ganter B, Wille R. Formal Concept Analysis: Mathematical Foundations. Springer, 1999.
15. Cimiano P, et al. "Context-based ontology building support in clinical domains using FCA." Int J Hum-Comput Stud 2003;59(1-2):187-208.
16. Zhao M, Ichise R. "Matching biomedical ontologies based on FCA." J Biomed Semantics 2018;9(1):11.
17. Shen Y, et al. "Clinical MetaData Ontology (CMDO)." PMC 2019.
18. "FCA Applications in Bioinformatics." ACM Computing Surveys 2022.

### General OMOP mapping context
19. Trinh NT, et al. "Harmonizing Norwegian registries onto OMOP CDM." Int J Med Inform 2024;105602.
20. Kurtz M, et al. "Suitability of OMOP CDM for mapping research datasets." SHTI 2024.
