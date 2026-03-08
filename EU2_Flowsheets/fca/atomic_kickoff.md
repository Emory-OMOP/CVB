# Atomic Item Review Sub-Agent Kickoff

Copy-paste the kickoff prompt below into a **new Claude Code session** started from `.private/`.
No prior context is needed — the prompt is self-contained.

---

## Pre-flight checklist (before pasting the prompt)

1. **Verify config is current**: `cat EU2_Flowsheets/fca/atomic_config.py`
   - `BATCH_START_LINE` and `BATCH_END_LINE` should already be set for this session
   - If not, update them (see batch plan at bottom of config file)
2. **Clean old artifacts**: `rm -f .private/subagents/atomic_py/*.py .private/subagents/atomic_csv/*.csv`

# Kickoff Section

## Kickoff Prompt

```
We're doing a clinical mapping pass on ~16K atomic flowsheet items, mapping
them to OMOP standard concepts. These are FCA category-A items — confirmed
clinical, expected to map at ~80% rate. We use a sub-agent orchestration pattern.

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
    laterality), and writes a Python script to .private/subagents/atomic_py/.

DO NOT read the enriched CSV yourself — that's the planner's job.
DO NOT rewrite sub-agent scripts yourself. If an agent fails, note the failure
and move on. Do not spend context fixing scripts — that's what QA reruns are for.

## Step 0 — Read config only (MINIMAL — 2 reads max)

1. Read `EU2_Flowsheets/fca/atomic_config.py` for batch line range and paths
2. Read `EU2_Flowsheets/fca/atomic_template.py` for the AtomicReviewBuilder API

Do NOT read the handoff or the enriched CSV. The planning agent handles that.

## Step 1 — Launch Planning Agent

Launch ONE Agent tool call with this prompt (fill in START/END from config):

---

### Planning agent prompt

```
You are the PLANNING AGENT for an atomic item review orchestration. Your job is
to read the batch data and return a concise plan for 10 review agents.

## Your tasks

1. Read the 1000 lines from `EU2_Flowsheets/Mappings/atomic_enriched.csv`
   starting at line START through line END. Use TWO Read calls (500 lines each).

2. Grep `EU2_Flowsheets/Mappings/atomic_review.csv` for concept IDs likely to
   recur in this batch (e.g., vital signs, ROM, balance, pain, hemodynamic,
   cath lab, validated instruments). Max 5 grep calls. Extract exact concept tuples:
   (tcid, "concept_name", "VOCAB", "code", "predicate", confidence, "Domain")

3. Return a structured plan with EXACTLY this format:

## Batch Summary
- Lines: START-END
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
- [Atomic items to SKIP: patient belongings, rehab goal metadata, exercise
  Reps/Sets/Weight, free-text comments, device settings/colors]
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
You are atomic item review sub-agent N of 10. Your job: review 100 flowsheet items
and write a Python script that maps or skips each one.

## Your line range
- Enriched CSV: EU2_Flowsheets/Mappings/atomic_enriched.csv
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
6. Write your script to .private/subagents/atomic_py/atomic_review__subagent_N.py
   IMPORTANT: Write to .private/subagents/atomic_py/ — NOT /tmp/claude/ or anywhere else.

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
[PASTE the planning agent's Reusable Concepts section here]

## Decision rules — MAP with exactMatch preferred

These are FCA category-A items — confirmed clinical. Most should map.

- **map**: ANY item that captures clinical/health information and has an OMOP concept:
  - Vital signs (SpO2, BP, HR, Temp, RR, Weight, Height, BMI)
  - Range of motion measurements (joint-specific LOINC codes exist)
  - Hemodynamic / cardiac cath pressures and saturations
  - Validated instruments and scales (named scores, subscales)
  - Functional status assessments (ADLs, FIM, GG items)
  - Clinical observations with structured values
  - Pain assessments and body diagram items
  - Wound assessment items
  - Nursing assessments (breath sounds, capillary refill, drainage)
  - Allergy skin test wheal/flare measurements
  - Lab-adjacent or point-of-care measurements
- **skip**: ONLY truly non-clinical items with NO OMOP concept:
  - Patient belongings inventory (Bathrobe, Bra, Pain Pump count)
  - Rehab goal metadata (Time Frame, Progress/Outcomes, Strategies/Barriers)
  - Exercise prescriptions (Reps/Sets/Weight items)
  - Free-text comment fields with no structured values
  - Device settings, colors, serial numbers
  - Equipment specifications (wheelchair dimensions, CI implant details)
  - Missed therapy minutes, scheduling metadata
- **flag**: Ambiguous, needs source data review

### Match precision guidance
- **exactMatch** preferred: look for the most specific OMOP concept
- **narrowMatch**: when source is more specific than available concept (e.g.,
  specific cath pressure site → generic chamber-level concept)
- **broadMatch**: only when no closer concept exists
- For hemodynamic measurements: use chamber-level SNOMED concepts (e.g.,
  4174434 "Right ventricular pressure") with narrowMatch when the source is
  a specific measurement point within that chamber

## Script format

Write to: .private/subagents/atomic_py/atomic_review__subagent_N.py

```python
#!/usr/bin/env python3
"""Atomic review sub-agent N: lines START-END of atomic_enriched.csv."""
import sys
sys.path.insert(0, "/Users/danielsmith/git_repos/org__Emory-OMOP/CVB/EU2_Flowsheets/fca")
from atomic_template import AtomicReviewBuilder

rb = AtomicReviewBuilder(agent_num=N, start_line=START, end_line=END)

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
- NEVER hand-type source codes — AtomicReviewBuilder reads them from the enriched CSV
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
cd /Users/danielsmith/git_repos/org__Emory-OMOP/CVB && bash EU2_Flowsheets/fca/finalize_atomic_batch.sh
```

This runs the full pipeline in one shot:
1. Accumulates sub-agent CSVs + QA checks (blocks on failure)
2. Pushes accumulated rows to atomic_review.csv
3. Validates source codes against atomic_enriched.csv
4. Auto-fixes issues (merged fields, off-by-one codes, descriptions)
5. Re-validates to confirm clean state

If it exits 0, move to Step 4. If it exits 1, review the remaining issues
printed to stdout — these need manual attention before proceeding.

For a preview without modifying atomic_review.csv:
```bash
bash EU2_Flowsheets/fca/finalize_atomic_batch.sh --dry-run
```

## Step 4 — Update config

1. Update `atomic_config.py` with NEXT batch's START/END lines (+1000)
2. Note session results (items reviewed, map/skip/flag counts)

Key files:
- Enriched source: `EU2_Flowsheets/Mappings/atomic_enriched.csv` (16,179 rows)
- Output: `EU2_Flowsheets/Mappings/atomic_review.csv`
- Config: `EU2_Flowsheets/fca/atomic_config.py`
- Template: `EU2_Flowsheets/fca/atomic_template.py`
- Finalizer: `EU2_Flowsheets/fca/finalize_atomic_batch.sh` (accumulate + push + validate + fix)
```
