# Clinical Review Sub-Agent Kickoff

Copy-paste the kickoff prompt below into a **new Claude Code session** started from `.private/`.
No prior context is needed — the prompt is self-contained.

---

## Pre-flight checklist (before pasting the prompt)

1. **Verify config is current**: `cat EU2_Flowsheets/fca/subagent_config.py`
   - `BATCH_START_LINE` and `BATCH_END_LINE` should already be set for this session
   - If not, update them (see "How to find START_LINE" below)
2. **Clean old artifacts**: `bash EU2_Flowsheets/fca/cleanup_subagents.sh`

# Kickoff Section

## Kickoff Prompt

```
We're doing a clinical reasoning pass on ~38K unmappable flowsheet items, mapping
them to OMOP standard concepts. We use a sub-agent orchestration pattern.

CRITICAL — HOW THIS WORKS:
You are the ORCHESTRATOR. You do NOT read the enriched CSV yourself. You delegate
ALL heavy reading to sub-agents, each of which gets its own context window.

Architecture (3 tiers):
  - ORCHESTRATOR (you): read config → launch planning agent → launch 10 review
    agents using the planner's output → QA. You should use <15% of context on
    Steps 0-1. The rest is for agent launches and QA.
  - PLANNING AGENT (1): reads the 1000-line CSV batch + greps prior mappings.
    Returns a concise plan: 10-agent split with line ranges, segment notes, and
    reusable concept tuples. Runs in its own context window.
  - REVIEW AGENTS (10): each reads its 100-line PRIMARY slice plus ±50 lines of
    CONTEXT (previous/next rows for template continuity), reasons clinically,
    looks up OMOP concepts with QUALIFIER concepts where appropriate (body site,
    laterality), and writes a Python script to .private/subagents/py/.

DO NOT read the enriched CSV yourself — that's the planner's job.
DO NOT rewrite sub-agent scripts yourself. If an agent fails, note the failure
and move on. Do not spend context fixing scripts — that's what QA reruns are for.

## Step 0 — Read config only (MINIMAL — 2 reads max)

1. Read `EU2_Flowsheets/fca/subagent_config.py` for batch line range and paths
2. Read `EU2_Flowsheets/fca/subagent_template.py` for the ReviewBuilder API

Do NOT read the handoff or the enriched CSV. The planning agent handles that.

## Step 1 — Launch Planning Agent

Launch ONE Agent tool call with this prompt (fill in START/END from config):

---

### Planning agent prompt

```
You are the PLANNING AGENT for a clinical review orchestration. Your job is to
read the batch data and return a concise plan for 10 review agents.

## Your tasks

1. Skim the handoff: `.private/handoff_clinical-reasoning-pass.md`
   - Read ONLY the first 40 lines (current progress) and last 2 session summaries
   - Extract: current progress count, any patterns/gotchas from recent sessions

2. Read the 1000 lines from `EU2_Flowsheets/Mappings/unmappable_enriched.csv`
   starting at line START through line END. Use TWO Read calls (500 lines each).

3. Grep `EU2_Flowsheets/Mappings/clinical_review.csv` for concept IDs likely to
   recur in this batch (e.g., mental status, balance, ADL, wound, pain, fall risk,
   nutrition, SDOH, psychiatric). Max 5 grep calls. Extract exact concept tuples:
   (tcid, "concept_name", "VOCAB", "code", "predicate", confidence, "Domain")

4. Return a structured plan with EXACTLY this format:

## Batch Summary
- Lines: START-END
- Progress: X/38,192 reviewed
- Dominant themes: [2-3 sentence characterization]

## Reusable Concepts
- ConceptName: (tcid, "name", "VOCAB", "code", "pred", conf, "Domain")
[List 8-15 concepts that appear relevant to this batch]

## Agent Split
| Agent | Lines | Note |
|-------|-------|------|
| 1 | START-START+99 | [1-line characterization] |
| 2 | START+100-START+199 | [1-line characterization] |
...
| 10 | START+900-END | [1-line characterization] |

Note: each agent will also read ±50 CONTEXT lines around their primary range
for template continuity. Flag any agent boundaries that fall mid-template — the
orchestrator should mention this when launching those agents.

## Template Boundary Warnings
- [e.g., "Agent 3/4 boundary at line X splits REHAB OP EVAL template"]
- [If none, say "No mid-template splits detected"]

## Items Needing Qualifiers
- [Flag clusters where body site / laterality qualifiers are needed]
- [e.g., "Lines X-Y: bilateral joint ROM items need L/R qualifier concepts"]

## Gotchas
- [Any patterns from prior sessions relevant to this batch]
- [Items that look tricky or need special attention]

DO NOT review individual items. DO NOT do concept lookups beyond the grep.
Your output should be <80 lines total. Be concise.
```

---

Wait for the planning agent to complete. Use its output verbatim as context
for the review agents in Step 2.

## Step 2 — Launch 10 review agents (THIS IS THE MAIN STEP)

Launch all 10 using the **Agent tool**, ideally in parallel batches (e.g., 5+5
or 3+3+4 if context is tight). Each agent gets this prompt (customize N, START,
END, and paste the planning agent's Reusable Concepts + relevant Gotchas):

---

### Sub-agent prompt template

```
You are clinical review sub-agent N of 10. Your job: review 100 flowsheet items
and write a Python script that maps or skips each one.

## Your line range
- Enriched CSV: EU2_Flowsheets/Mappings/unmappable_enriched.csv
- PRIMARY lines: START to END (1-indexed, line 1 = header) — you MAP/SKIP these
- CONTEXT lines: read 50 lines BEFORE (offset=START-51, limit=50) and 50 lines
  AFTER (offset=END, limit=50) for template continuity. Do NOT map/skip context
  lines — they belong to adjacent agents. Use them to understand what template
  or instrument a group of items belongs to.

## Instructions

1. Read your CONTEXT lines first (before + after), then your 100 PRIMARY lines
2. Check the `template_names` and `group_names` columns — items from the same
   template/group should be mapped consistently. If your primary range starts or
   ends mid-template, use the context lines to understand the full instrument.
3. For each PRIMARY item, decide: map (clinical value) or skip (admin/non-clinical)
4. For items to map, search OMOP concepts using search_concepts tool
5. **Add qualifiers** when the item has a body site, laterality, or method:
   - Body site: e.g., "Left knee ROM" → concept=ROM + qualifier=(4135969, "Knee", "Has finding site")
   - Laterality: e.g., "RUE strength" → concept=Muscle strength + qualifier=(4180344, "Right upper extremity", "Has finding site")
   - Method: e.g., "BP cuff" → concept=BP + qualifier=(4322632, "Blood pressure cuff", "Has method")
   - Use search_concepts to find the right qualifier concept_id — don't guess
6. Write your script to .private/subagents/py/clinical_review__subagent_N.py
   IMPORTANT: Write to .private/subagents/py/ — NOT /tmp/claude/ or anywhere else.

## Common qualifier concepts (search for more specific ones as needed)
- Right (generic): (4080761, "Right", "Has laterality")
- Left (generic): (4300877, "Left", "Has laterality")
- Right upper extremity: (4180344, "Entire right upper extremity", "Has finding site")
- Left upper extremity: (4180345, "Entire left upper extremity", "Has finding site")
- Right lower extremity: (4179565, "Entire right lower extremity", "Has finding site")
- Left lower extremity: (4180483, "Entire left lower extremity", "Has finding site")
- Face: (4232301, "Face structure", "Has finding site")
- Oral: (4132161, "Oral", "Has method")

## Reusable concepts from prior sessions
[PASTE the planning agent's Reusable Concepts section here, e.g.:]
- Mental status: (3018668, "Mental status", "LOINC", "8693-4", "broadMatch", 0.7, "Observation")
- ABC Scale: (40481019, "Activities specific balance confidence scale", "SNOMED", "443322002", "broadMatch", 0.85, "Measurement")
- DHI: (46284659, "Dizziness Handicap Inventory", "SNOMED", "951681000000109", "exactMatch", 0.95, "Measurement")
[etc.]

## Decision rules — MAP AGGRESSIVELY
The goal is to find EVERY possible OMOP concept match. When in doubt, MAP.

- **map**: ANY item that captures clinical/health information and has an OMOP concept:
  - Validated instruments (named scales/scores)
  - Clinical observations with structured values
  - Vital signs, lab-adjacent items
  - SDOH screening (food insecurity, housing, transportation, safety, loneliness)
  - Behavioral health screening and observations
  - Violence/agitation risk assessments
  - Nursing ROS items with structured clinical lists
  - Medical history screening questions (TB, cardiac, diabetes, seizures)
  - Quality of life measures (CDC HRQOL, PROMIS, etc.)
  - Functional status assessments (ADLs, GG items, FIM-like scales)
  - Patient-reported outcomes of any kind
  - Psychiatric assessments (MSE, risk factors, symptoms)
  - Substance use screening items
  - Medication adherence assessments
  - Pain assessments and body diagram items
  - Wound assessment items (size, depth, drainage, tissue type)
  - Fall risk screening items
  - Nutrition screening items
- **skip**: ONLY truly non-clinical items with NO OMOP concept:
  - Staff names, receipt numbers, contact info, dates
  - Consent/verification checkboxes ("Confirmed", "Verified", "Reviewed")
  - Patient belongings/valuables inventory
  - Equipment serial numbers, machine settings
  - Free-text comment fields with no structured values
  - Template section headers
  - Duplicate items (same description already mapped with different code)
- **flag**: Ambiguous, needs source data review

## Script format

Write to: .private/subagents/py/clinical_review__subagent_N.py

```python
#!/usr/bin/env python3
"""Clinical review sub-agent N: lines START-END of unmappable_enriched.csv."""
import sys
sys.path.insert(0, "/Users/danielsmith/git_repos/org__Emory-OMOP/CVB/EU2_Flowsheets/fca")
from subagent_template import ReviewBuilder

rb = ReviewBuilder(agent_num=N, start_line=START, end_line=END)

# Concept tuple: (tcid, "concept_name", "VOCAB", "code", "pred", conf, "Domain")
# Qualifier tuple (optional): (qcid, "qualifier_name", "qualifier_rel")

MAP_ITEMS = {
    # Without qualifier:
    "source_code": ((tcid, "concept_name", "VOCAB", "code", "pred", conf, "Domain"), "justification"),
    # With qualifier (body site, laterality, or method):
    "source_code": ((tcid, "concept_name", "VOCAB", "code", "pred", conf, "Domain"), "justification",
                    (qcid, "qualifier_name", "qualifier_rel")),
}

SKIP_REASONS = {
    "source_code": "Reason for skipping.",
}

for code, desc, row in rb.source_items():
    if code in MAP_ITEMS:
        entry = MAP_ITEMS[code]
        concept, justification = entry[0], entry[1]
        if len(entry) > 2 and entry[2]:
            qcid, qcname, qrel = entry[2]
            rb.map_row(code, desc, *concept, justification, qcid, qcname, qrel)
        else:
            rb.map_row(code, desc, *concept, justification)
    elif code in SKIP_REASONS:
        rb.skip(code, desc, SKIP_REASONS[code])
    else:
        rb.skip(code, desc, "[Default skip reason for this segment].")

rb.write()

unhandled = rb.unhandled()
if unhandled:
    print(f"\nWARNING: {len(unhandled)} unhandled items:")
    for code, desc in unhandled:
        print(f"  {code}: {desc}")
```

Rules:
- NEVER hand-type source codes — ReviewBuilder reads them from the enriched CSV
- Include clinical reasoning in justification (not just "mapped to X")
- For skip-heavy segments, a single default reason is fine
- Search search_concepts for NEW instruments not in the reusable list above
- Add qualifier tuples for items with body site, laterality, or method context
- Always include the unhandled check at the end
```

---

After all 10 agents complete, proceed to Step 3.

## Step 3 — Finalize (single command)

Tell me to run:
```bash
cd /Users/danielsmith/git_repos/org__Emory-OMOP/CVB && bash EU2_Flowsheets/fca/finalize_batch.sh
```

This runs the full pipeline in one shot:
1. Accumulates sub-agent CSVs + QA checks (blocks on failure)
2. Pushes accumulated rows to clinical_review.csv
3. Validates source codes against enriched CSV
4. Auto-fixes issues (merged fields, off-by-one codes, descriptions)
5. Re-validates to confirm clean state

If it exits 0, move to Step 4. If it exits 1, review the remaining issues
printed to stdout — these need manual attention before proceeding.

For a preview without modifying clinical_review.csv:
```bash
bash EU2_Flowsheets/fca/finalize_batch.sh --dry-run
```

## Step 4 — Update handoff + config

1. Update `.private/handoff_clinical-reasoning-pass.md` with session results:
   - Update progress count at top
   - Add session history entry with: items reviewed, map/skip/flag counts, key mapped clusters
2. Update `subagent_config.py` with NEXT batch's START/END lines (+1000)

Key files:
- Enriched source: `EU2_Flowsheets/Mappings/unmappable_enriched.csv` (38,192 rows)
- Output: `EU2_Flowsheets/Mappings/clinical_review.csv`
- Config: `EU2_Flowsheets/fca/subagent_config.py`
- Template: `EU2_Flowsheets/fca/subagent_template.py`
- Finalizer: `EU2_Flowsheets/fca/finalize_batch.sh` (accumulate + push + validate + fix)
- Handoff: `.private/handoff_clinical-reasoning-pass.md`
```

## Recovery Sequence (as of 2026-03-07)

`source_items()` now auto-skips codes already in clinical_review.csv, so re-processing
ranges that partially overlap with existing data is safe.

### Step 1: Gap fill (do this FIRST)
```
BATCH_START_LINE = 6233
BATCH_END_LINE = 8293
SUBAGENT_COUNT = 1
```
Single sub-agent, 61 unreviewed items after skip filter. Finalize normally.

### Step 2: Re-run lost batches (8 standard batches)
After gap fill, process these in order. Set `SUBAGENT_COUNT = 10` for all.

| Session | START_LINE | END_LINE | Was session | Notes |
|---------|-----------|----------|-------------|-------|
| R1      | 17294     | 18293    | 24          | CDIP-58, NPI-Q, UHDRS, CI QoL, audiological |
| R2      | 18294     | 19293    | 25          | Allergy patch testing (~400), QIDS, DAS-28, pain |
| R3      | 19294     | 20293    | 26          | WHOQOL-BREF, WHYMPI, SCOPA-AUT, DASI, HCT comorbidity |
| R4      | 20294     | 21293    | 27          | FOSQ-10, IPSS, HJHS, hemophilia, sleep, psychiatry |
| R5      | 21294     | 22293    | 28          | EORTC, urodynamics, PFIQ-7, PISQ-12, PFDI-20, BH instruments |
| R6      | 22294     | 23293    | 29          | QOLIE-31, allergy patch, COMPASS-31, gene therapy, Long COVID |
| R7      | 23294     | 24293    | 30          | Rehab goals (low yield), ED CPG checklists |
| R8      | 24294     | 25293    | 31          | Finnegan NAS, APACHE, nutrition, ICU monitoring |

### Step 3: Resume normal processing
After R8, continue from 26294 (25294-26293 already ingested).

| Session | START_LINE | END_LINE |
|---------|-----------|----------|
| Next    | 26294     | 27293    |
| +1      | 27294     | 28293    |
| ...     | +1000     | +1000    |
| Last    | 37294     | 38193    |

## After each session

1. Update `subagent_config.py` with next batch's START/END lines
2. Update the handoff doc with session results
3. Verify final row count: `wc -l EU2_Flowsheets/Mappings/clinical_review.csv`
