# OMOP Arcade: Design Document

**Date**: 2026-03-06
**Status**: Draft
**Repo**: `lits__EmoryDataSolutions/emory_omop_enterprise`
**Hosting**: GitHub Pages (private repo — Emory SSO via GitHub org)

---

## Purpose

A gamified web tool for clinicians and informaticists to review proposed flowsheet-to-OMOP mappings. Generates gold-standard evaluation data for the JAMIA publication while producing clinically validated mappings for production use.

## User Flow

```
1. User navigates to GitHub Pages site (must be authenticated to GitHub org via Emory SSO)
2. User enters or selects their display name
3. User sees a list of mapping groups (LLM-curated clinical instrument clusters)
4. User selects a group to review
5. For each item in the group, user sees:
   - Full source context (flowsheet item name, template, group, values)
   - Full target context (OMOP concept details: name, domain, vocabulary, code, class)
   - LLM justification text
6. User chooses one of three actions:
   a. 👍 Agree — accepts the proposed mapping (+1 point)
   b. 👎 Disagree — rejects the mapping (+1 point)
   c. 👎 Disagree & Suggest — rejects and proposes a better mapping (+3x points, +6x if suggestion reaches consensus)
7. User can load previous/next 10–100 neighboring items for context
8. On batch submit, reviews are committed as JSON via GitHub API
9. GitHub Action rebuilds leaderboard (~10 min delay)
```

## Architecture

```
GitHub Pages (static site)
├── index.html              — game UI (vanilla JS or lightweight framework)
├── data/
│   ├── task_groups.json    — LLM-curated mapping groups from clinical_review.csv
│   ├── enriched_context.json — source context from unmappable_enriched.csv
│   └── vocab_index.json    — OMOP concept search index (Fuse.js)
├── reviews/                — committed by users via GitHub API
│   └── {date}_{user}_{batch}.json
└── leaderboard.json        — rebuilt by GitHub Action

GitHub Action (on push to reviews/)
├── Aggregates all review JSONs
├── Computes leaderboard stats
├── Computes inter-rater agreement (items with 2+ reviews)
└── Writes leaderboard.json
```

## Data Structures

### Task Group (what the user sees)

```json
{
  "group_id": "rodnan_skin_score",
  "instrument_name": "Modified Rodnan Skin Score",
  "template_name": "EHC AMB RHU RODNAN SKIN SCORE",
  "group_name": "Rodnan Skin Score",
  "description": "Skin thickness scored 0-3 at 17 body sites. Validated instrument for systemic sclerosis.",
  "items": [
    {
      "source_concept_code": "10003",
      "source_description": "Face",
      "custom_list_values": "Uninvolved|Mild thickening|Moderate thickening|Severe thickening",
      "decision": "map",
      "proposed_mapping": {
        "target_concept_id": 141960,
        "target_concept_name": "Skin finding",
        "target_vocabulary_id": "SNOMED",
        "target_concept_code": "106076001",
        "target_domain_id": "Condition",
        "target_concept_class_id": "Clinical Finding",
        "target_standard_concept": "S",
        "predicate_id": "broadMatch",
        "relationship_id": "Maps to"
      },
      "qualifier": {
        "qualifier_concept_id": 4232301,
        "qualifier_concept_name": "Face structure",
        "qualifier_relationship_id": "Has finding site"
      },
      "mapping_justification": "Modified Rodnan Skin Score component — skin thickness scored 0-3. Validated instrument for systemic sclerosis."
    }
  ]
}
```

### Review Submission (what gets committed)

```json
{
  "reviewer": "jsmith",
  "submitted_at": "2026-03-06T14:32:00Z",
  "group_id": "rodnan_skin_score",
  "reviews": [
    {
      "source_concept_code": "10003",
      "action": "agree",
      "time_spent_ms": 3200
    },
    {
      "source_concept_code": "10008",
      "action": "disagree",
      "time_spent_ms": 5100
    },
    {
      "source_concept_code": "10011",
      "action": "disagree_suggest",
      "time_spent_ms": 18400,
      "suggested_mapping": {
        "target_concept_id": 4265108,
        "target_concept_name": "Left hand structure",
        "target_vocabulary_id": "SNOMED",
        "target_concept_code": "85151006",
        "predicate_id": "exactMatch",
        "qualifier_concept_id": null,
        "qualifier_relationship_id": null,
        "notes": "More specific body site concept exists"
      }
    }
  ]
}
```

### Leaderboard (rebuilt by Action)

```json
{
  "updated_at": "2026-03-06T14:45:00Z",
  "rankings": [
    {
      "reviewer": "jsmith",
      "score": 214,
      "items_reviewed": 142,
      "groups_completed": 8,
      "agrees": 110,
      "disagrees": 20,
      "suggestions": 12,
      "suggestions_stuck": 4,
      "avg_time_per_item_ms": 4200,
      "first_review": "2026-03-06",
      "last_review": "2026-03-06"
    }
  ],
  "inter_rater": {
    "items_with_multiple_reviews": 89,
    "agreement_rate": 0.82,
    "cohens_kappa": 0.71
  },
  "totals": {
    "total_items_reviewed": 312,
    "total_groups_completed": 18,
    "total_reviewers": 5,
    "overall_agree_rate": 0.76
  }
}
```

## UI Screens

### Screen 1: Group Selection

- List of available mapping groups
- Each shows: instrument name, template, item count, % reviewed
- Sort by: unreviewed first, then by item count
- User's session stats at top

### Screen 2: Review Cards

- Header: instrument name, template, group, overall justification
- Context bar: "Load previous (N)" / "Load next (N)" with slider 10–100
  - Loads neighboring items from the enriched context (original flowsheet order)
  - Displayed as a collapsed sidebar for reference, not for review
- Card for current item:
  - Source side: item name, code, custom list values
  - Target side: full OMOP concept row (name, domain, vocabulary, code, class, standard)
  - Qualifier row (if present): qualifier concept name, relationship
  - LLM justification text
  - Three buttons: 👍 Agree (+1) | 👎 Disagree (+1) | 👎 Disagree & Suggest (+3x, +6x if it sticks!)
- Progress bar: "Item 3 of 17 in this group"
- Mini leaderboard in footer

### Screen 3: Vocabulary Search (on "Disagree & Suggest")

- Search box with Fuse.js fuzzy search against vocab_index.json
- Filter dropdowns: Domain, Vocabulary, Concept Class
- Results as a scrollable list showing full concept details
- Click to select → populates suggestion form
- Optional notes field
- Submit returns to next review card

## Vocabulary Search Index

Generated from our DuckDB vocab instance. Filter to:
- `standard_concept = 'S'` (standard concepts only)
- `invalid_reason IS NULL` (valid only)
- Domains: Measurement, Observation, Condition, Procedure, Device
- ~200-500K concepts → estimate 30-50MB JSON, gzipped ~5-10MB

Fields per concept:
```json
{
  "c": 141960,
  "n": "Skin finding",
  "d": "Condition",
  "v": "SNOMED",
  "k": "106076001",
  "l": "Clinical Finding"
}
```

Short keys to minimize file size. Fuse.js searches on `n` (name).

### Future: ATHENA API (Phase 2)

Replace the static JSON index with a live API call to an ATHENA-compatible endpoint. The search component interface stays the same — only the data source changes. This removes the static file size constraint and gives access to the full 7.4M concept vocabulary.

## GitHub Action: Leaderboard Builder

```yaml
name: Rebuild Leaderboard
on:
  push:
    paths:
      - 'apps/omop-arcade/reviews/**'
jobs:
  rebuild:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: python apps/omop-arcade/scripts/build_leaderboard.py
      - uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "Rebuild leaderboard"
          file_pattern: apps/omop-arcade/leaderboard.json
```

## Data Pipeline

### Generating task_groups.json from clinical_review.csv

Group clinical_review.csv rows by clinical instrument (derived from mapping_justification patterns). Join with unmappable_enriched.csv for source context (template_names, group_names, custom_list_values). Output as JSON array of task groups.

Script: `apps/omop-arcade/scripts/build_task_groups.py`

### Generating vocab_index.json from DuckDB

Query the OHDSI vocab DuckDB for standard, valid concepts in target domains. Output as compact JSON with short keys.

Script: `apps/omop-arcade/scripts/build_vocab_index.py`

## Metrics for the Paper

From the review data, we compute:

| Metric | Source | Paper Use |
|--------|--------|-----------|
| FCA Stage 1 precision | Reviews of atomic items (sample) | "X% of FCA-classified atomic items confirmed by expert review" |
| LLM triage utility | Agree rate on clinical_review items | "Clinicians agreed with X% of LLM-proposed mappings" |
| Inter-rater agreement | Items with 2+ reviews | Cohen's kappa for mapping acceptance |
| Time per review | time_spent_ms field | Comparison to Austin 2025 (1.19 min/concept) |
| Correction quality | disagree_suggest submissions | "Of rejected mappings, X% received alternative suggestions" |
| Coverage improvement | Total mappable after review | Final count vs. FCA-only and LLM-only counts |

## Directory Structure

```
emory_omop_enterprise/
  apps/
    omop-arcade/
      index.html
      style.css
      app.js
      data/
        task_groups.json
        enriched_context.json
        vocab_index.json
      reviews/
        .gitkeep
      leaderboard.json
      scripts/
        build_task_groups.py
        build_vocab_index.py
        build_leaderboard.py
```

## Decisions

1. **Name**: OMOP Arcade
2. **Tutorial**: Yes — onboarding flow with very simple examples before first review session. Plain language, no assumed OMOP knowledge.
3. **Reviews per item**: Target 3 for consensus. 2 is sufficient for inter-rater agreement stats. Items are available for review until they reach 3 reviews, then removed from the queue. If concurrent reviewers push an item to 4+, that's fine — extra data doesn't hurt.
4. ~~Should "skip" decisions also count toward the leaderboard?~~ — Resolved: No skip option. Disagree (+1), Disagree & Suggest (+3x, +6x if suggestion reaches consensus).
5. ~~Should we include FCA Category A (atomic) items as a control sample?~~ — Resolved: Yes, include Category A items. Serves as a control to measure FCA Stage 1 precision.

## Next Steps

- [ ] Generate task_groups.json from clinical_review.csv + unmappable_enriched.csv
- [ ] Generate vocab_index.json from DuckDB vocab
- [ ] Build the static site (index.html, app.js, style.css)
- [ ] Write the GitHub Action for leaderboard rebuild
- [ ] Deploy to GitHub Pages on emory_omop_enterprise
- [ ] Recruit 3-5 reviewers for pilot
- [ ] Collect data for paper evaluation section
