"""Configuration for the current clinical review sub-agent batch.

Update this file before each orchestrated batch run.
The accumulate_reviews.py script reads these values.
"""
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent  # CVB/
_PRIVATE = _REPO / ".private"

# Sub-agent scripts go here (agents write .py files)
SUBAGENT_SCRIPT_DIR = str(_PRIVATE / "subagents" / "py")

# Sub-agent CSV output goes here (ReviewBuilder writes .csv files)
SUBAGENT_CSV_DIR = str(_PRIVATE / "subagents" / "csv")

# Legacy alias used by accumulate_reviews.py
SUBAGENT_DIR = SUBAGENT_CSV_DIR

# Naming pattern: {PREFIX}{N}.py produces {PREFIX}{N}.csv
SUBAGENT_PREFIX = "clinical_review__subagent_"

# How many sub-agents in this batch (1-indexed)
SUBAGENT_COUNT = 10

# Current batch line range (enriched CSV, 1-indexed with header on line 1)
# Recovery batch R1 (was session 24). Lines 17294-18293.
BATCH_START_LINE = 17294
BATCH_END_LINE = 18293

# Accumulated output (intermediate QA file)
ACCUMULATED_CSV = str(_PRIVATE / "subagents" / "csv" / "clinical_review__accumulated.csv")

# Final destination
CLINICAL_REVIEW_CSV = str(_REPO / "EU2_Flowsheets" / "Mappings" / "clinical_review.csv")
