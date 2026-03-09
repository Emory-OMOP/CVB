"""Configuration for the atomic item review sub-agent batch.

Parallel to subagent_config.py but for category-A (atomic) items.
Update BATCH_START_LINE / BATCH_END_LINE before each batch run.
"""
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent  # CVB/
_PRIVATE = _REPO / ".private"

# Sub-agent scripts go here (agents write .py files)
SUBAGENT_SCRIPT_DIR = str(_PRIVATE / "subagents" / "atomic_py")

# Sub-agent CSV output goes here (ReviewBuilder writes .csv files)
SUBAGENT_CSV_DIR = str(_PRIVATE / "subagents" / "atomic_csv")

# Naming pattern: {PREFIX}{N}.py produces {PREFIX}{N}.csv
SUBAGENT_PREFIX = "atomic_review__subagent_"

# How many sub-agents in this batch (1-indexed)
SUBAGENT_COUNT = 10

# Current batch line range (atomic_enriched.csv, 1-indexed with header on line 1)
# Batch 1: lines 2-1001 (first 1000 data rows)
BATCH_START_LINE = 4002
BATCH_END_LINE = 5001

# Accumulated output (intermediate QA file)
ACCUMULATED_CSV = str(_PRIVATE / "subagents" / "atomic_csv" / "atomic_review__accumulated.csv")

# Final destination
ATOMIC_REVIEW_CSV = str(_REPO / "EU2_Flowsheets" / "Mappings" / "atomic_review.csv")

# Source enriched CSV
ATOMIC_ENRICHED_CSV = str(_REPO / "EU2_Flowsheets" / "Mappings" / "atomic_enriched.csv")

# Total items: 16,179 (lines 2-16180)
# Batch plan: 16 batches of 1000 + 1 batch of 179
# Batch  1: lines     2 -  1001
# Batch  2: lines  1002 -  2001
# Batch  3: lines  2002 -  3001
# ...
# Batch 16: lines 15002 - 16001
# Batch 17: lines 16002 - 16180  (179 items)
