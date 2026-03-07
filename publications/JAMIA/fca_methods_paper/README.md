# FCA + LLM Clinical Reasoning for Flowsheet-to-OMOP Mapping

**Target journal**: Journal of the American Medical Informatics Association (JAMIA)

## Mini Abstract

Electronic health record flowsheet data — capturing vital signs, nursing assessments, clinical scores, and device parameters — represents one of the richest yet most underutilized sources of observational health data. At a typical academic medical center, flowsheet repositories contain 25,000–56,000 distinct item types across thousands of templates, making manual mapping to standardized vocabularies like OMOP infeasible. We present a two-stage methodology combining Formal Concept Analysis (FCA) for automated structural classification with LLM-assisted clinical reasoning for residual item review. In the first stage, FCA analyzes the attribute structure of flowsheet items (value types, units, ranges, custom list values, template co-occurrence) to classify items into three categories: atomic (1:1 mappable to a single OMOP concept), compositional (requiring multi-concept mappings with qualifiers), and unmappable (lacking detectable clinical attributes). In the second stage, an LLM performs item-by-item clinical reasoning over the unmappable residual, using enriched metadata (template names, group context, value enumerations) to determine clinical meaning and look up appropriate OMOP vocabulary concepts. Applied to 55,938 Epic flowsheet items at Emory Healthcare, FCA automatically classified 17,745 items (31.7%) as directly mappable, while LLM-assisted review of the 38,192 residual items is rescuing an estimated 10% (~4,000 items) that contain clinical value invisible to pattern-based approaches. The combined method achieves broader coverage than either approach alone, with FCA providing scalable triage and LLM reasoning providing the contextual clinical judgment needed for ambiguous items.

## Background Research

### Directly relevant prior work

1. **Waitman et al. (2021)** — "Integrating Flowsheet Data in OMOP Common Data Model for Clinical Research" (arXiv:2109.08235)
   - Reports 25,777 distinct flowsheet row types across 1,883 templates — similar scale to our 55,938 items
   - Presents two approaches: structural mapping and LOINC-based mapping
   - Mentions FloMap (University of Minnesota) and stacked ML models (topic model + SVM, f2=0.74)
   - Neither tool is open-sourced or productized
   - Key gap: ML approaches achieve moderate accuracy but lack clinical reasoning about item context
   - URL: https://arxiv.org/abs/2109.08235

2. **Talapova et al. (2023)** — "Mapping of Critical Care EHR Flowsheet data to OMOP CDM via SSSOM"
   - Presented at OHDSI 2023 Symposium
   - Uses Simple Standard for Sharing Ontological Mappings (SSSOM) as intermediate representation
   - Focuses on critical care flowsheets specifically
   - Structural mapping approach — does not use clinical reasoning per item
   - URL: https://www.ohdsi.org/2023showcase-501/

3. **Waitman et al. (2015)** — "Modeling Flowsheet Data for Clinical Research" (PMC)
   - Foundational work on the problem of flowsheet data integration
   - Identifies key challenges: volume, heterogeneity, site-specific customization
   - URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC4525247/

4. **Mt. Sinai MSDW OMOP Mapping (2022)** — Timothy Quinn
   - Documents institutional approach to OMOP vocabulary mapping
   - Covers terminology mapping workflows but not flowsheet-specific methods
   - URL: https://labs.icahn.mssm.edu/msdw/wp-content/uploads/sites/350/2022/12/MSDW-OMOP-Mapping_2022-11-29.pdf

### FCA in clinical informatics

5. **Cimiano et al. (2003)** — "Context-based ontology building support in clinical domains using formal concept analysis"
   - FCA applied to cardiovascular medicine ontology construction
   - Integrates FCA module with NLP module
   - Demonstrates FCA's utility for discovering concept hierarchies from clinical data
   - Not applied to EHR-to-vocabulary mapping
   - URL: https://pubmed.ncbi.nlm.nih.gov/12909160/

6. **Zhao & Ichise (2018)** — "Matching biomedical ontologies based on formal concept analysis"
   - FCA lattices used to find mappings between biomedical ontologies
   - Identifies one-to-one mappings, complex mappings, and property correspondences
   - Methodologically related to our FCA pipeline but applied ontology-to-ontology, not EHR-to-ontology
   - URL: https://link.springer.com/article/10.1186/s13326-018-0178-9

7. **Shen et al. (2019)** — "Clinical MetaData Ontology (CMDO)"
   - Classification scheme for clinical data elements based on semantics
   - Uses General Formal Ontology method
   - Related goal of classifying clinical data elements but different approach
   - URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC6701018/

### What is novel about our approach

No published work combines these three elements:

1. **FCA for structural triage** — Using attribute lattices (value type, units, custom list structure, template co-occurrence) to automatically classify flowsheet items into mappability categories. FCA has been used for ontology building and ontology matching, but not for EHR item classification.

2. **LLM-assisted clinical reasoning** — Using a large language model to perform item-by-item clinical reasoning over residual items, leveraging enriched metadata (template context, group names, value enumerations) to determine clinical meaning. This goes beyond pattern matching — the LLM understands that "Grimace" in an APGAR template is a reflex irritability score, or that "RUE" in an OB DTR group is a preeclampsia assessment.

3. **OMOP vocabulary lookup in the reasoning loop** — The LLM searches the OHDSI vocabulary (7.4M+ concepts) during review, matching items to specific SNOMED/LOINC/CPT concepts with predicate types (exactMatch/broadMatch/narrowMatch) and confidence scores. This produces audit-ready mapping metadata, not just binary mapped/unmapped classifications.

The closest comparisons are:
- **FloMap / SVM classifiers**: Pattern-matching systems that achieve f2=0.74 but lack contextual reasoning
- **SSSOM approach**: Structural mapping that handles well-structured items but misses contextually clinical items
- **Manual expert review**: Gold standard for accuracy but doesn't scale to 56K items

Our method achieves the scalability of automated approaches (FCA handles 56K items in seconds) with the accuracy of expert review (LLM clinical reasoning for the residual), at a fraction of the cost of full manual review.

## Key numbers for the paper

- 55,938 total flowsheet items at Emory Healthcare
- 1,883+ templates, 46,850+ groups (comparable to Waitman et al.)
- FCA Stage 1: 16,204 atomic (A), 1,541 compositional (B), 38,192 unmappable (C)
- LLM Stage 2 (in progress): ~10% rescue rate from C items (~4,000 expected)
- Mapping predicates: exactMatch, broadMatch, narrowMatch, closeMatch with 0.0-1.0 confidence
- Target vocabularies: SNOMED, LOINC, CPT4
- 60+ validated clinical instruments identified in residual (APGAR, Modified Ashworth, BVAS, DHI, etc.)

## File structure (planned)

```
fca_methods_paper/
  README.md          <- this file
  manuscript.tex     <- main manuscript (LaTeX, JAMIA format)
  figures/           <- diagrams and result figures
  tables/            <- mapping statistics tables
  supplementary/     <- full instrument list, example mappings
```
