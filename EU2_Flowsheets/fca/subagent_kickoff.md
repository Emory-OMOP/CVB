# Clinical Review Sub-Agent Kickoff

Copy-paste the kickoff prompt below into a **new Claude Code session** started from `.private/`.
No prior context is needed — the prompt is self-contained.

---

## Pre-flight checklist (before pasting the prompt)

1. **Verify config is current**: `cat EU2_Flowsheets/fca/subagent_config.py`
   - `BATCH_START_LINE` and `BATCH_END_LINE` should already be set for this session
   - If not, update them (see "How to find START_LINE" below)
2. **Clean old artifacts**: `bash EU2_Flowsheets/fca/cleanup_subagents.sh`

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
  - REVIEW AGENTS (10): each reads its 100-line slice, reasons clinically, looks
    up OMOP concepts, and writes a Python script to .private/subagents/py/.

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
- Lines START to END (1-indexed, line 1 = header)

## Instructions

1. Read your 100 lines from the enriched CSV (offset=START-1, limit=100)
2. For each item, decide: map (clinical value) or skip (admin/non-clinical)
3. For items to map, search OMOP concepts using search_concepts tool
4. Write your script to .private/subagents/py/clinical_review__subagent_N.py
   IMPORTANT: Write to .private/subagents/py/ — NOT /tmp/claude/ or anywhere else.

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

MAP_ITEMS = {
    "source_code": ((tcid, "concept_name", "VOCAB", "code", "pred", conf, "Domain"), "Clinical reasoning justification"),
}

SKIP_REASONS = {
    "source_code": "Reason for skipping.",
}

for code, desc, row in rb.source_items():
    if code in MAP_ITEMS:
        concept, justification = MAP_ITEMS[code]
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
- Always include the unhandled check at the end
```

---

After all 10 agents complete, proceed to Step 3.

## Step 3 — Ask me to run QA

Tell me to run:
```bash
cd /Users/danielsmith/git_repos/org__Emory-OMOP/CVB/EU2_Flowsheets && uv run python fca/accumulate_reviews.py
```

Review the QA output. If issues found, note them and ask me to re-run after fixes.

## Step 4 — Push

If QA passes, tell me to run:
```bash
cd /Users/danielsmith/git_repos/org__Emory-OMOP/CVB/EU2_Flowsheets && uv run python fca/accumulate_reviews.py --skip-run --push
```

## Step 5 — Validate

Tell me to run:
```bash
cd /Users/danielsmith/git_repos/org__Emory-OMOP/CVB/EU2_Flowsheets && uv run python fca/validate_review_codes.py
```

If NEW issues found (check line numbers — issues at lines <current batch are pre-existing), fix with:
```bash
uv run python fca/fix_clinical_review.py         # dry run first
uv run python fca/fix_clinical_review.py --apply  # then apply
uv run python fca/validate_review_codes.py        # re-validate
```

## Step 6 — Update handoff + config

1. Update `.private/handoff_clinical-reasoning-pass.md` with session results:
   - Update progress count at top
   - Add session history entry with: items reviewed, map/skip/flag counts, key mapped clusters
2. Update `subagent_config.py` with NEXT batch's START/END lines (+1000)

Key files:
- Enriched source: `EU2_Flowsheets/Mappings/unmappable_enriched.csv` (38,192 rows)
- Output: `EU2_Flowsheets/Mappings/clinical_review.csv`
- Config: `EU2_Flowsheets/fca/subagent_config.py`
- Template: `EU2_Flowsheets/fca/subagent_template.py`
- Accumulator: `EU2_Flowsheets/fca/accumulate_reviews.py`
- Validator: `EU2_Flowsheets/fca/validate_review_codes.py`
- Fixer: `EU2_Flowsheets/fca/fix_clinical_review.py`
- Handoff: `.private/handoff_clinical-reasoning-pass.md`
```

## How to find START_LINE

The enriched CSV line number = items reviewed + 2 (line 1 is header, line 2 is first data row).

| After session | Items reviewed | Next START_LINE | BATCH_END_LINE |
|--------------|---------------|-----------------|----------------|
| Session 15   | 9,231         | 9,294           | 10,293         |
| Session 16   | 10,231        | 10,294          | 11,293         |
| Session 17   | 11,231        | 11,294          | 12,293         |
| Session 18   | 12,231        | 12,294          | 13,293         |
| Session 19   | 13,231        | 13,294          | 14,293         |
| Session 20   | 14,231        | 14,294          | 15,293         |
| Session 21   | 15,231        | 15,294          | 16,293         |
| Session 22   | 16,231        | 16,294          | 17,293         |
| Session 23   | 17,231        | 17,294          | 18,293         |
| Session 24   | 18,231        | 18,294          | 19,293         |
| Session 25   | 19,231        | 19,294          | 20,293         |
| Session 26   | 20,231        | 20,294          | 21,293         |

(Add 1000 per session, +2 for header offset)

## After each session

1. Update `subagent_config.py` with next batch's START/END lines
2. Update the handoff doc with session results
3. Verify final row count: `wc -l EU2_Flowsheets/Mappings/clinical_review.csv`
