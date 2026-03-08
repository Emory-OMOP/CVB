#!/usr/bin/env python3
"""Atomic item review sub-agent template.

Thin wrapper around ReviewBuilder configured for atomic items.
Points to atomic_enriched.csv as source and atomic_review.csv for
skip-filter deduplication.

Usage in sub-agent scripts:

    from atomic_template import AtomicReviewBuilder

    rb = AtomicReviewBuilder(agent_num=1, start_line=2, end_line=101)

    for code, desc, enriched_row in rb.source_items():
        if should_map(code, desc):
            rb.map_row(code, desc, tcid, tname, tvocab, tcode,
                       pred, conf, domain, justification)
        else:
            rb.skip(code, desc, justification)

    rb.write()
"""
import csv
import os
from pathlib import Path

MAPPINGS_DIR = Path(__file__).resolve().parent.parent / "Mappings"
ATOMIC_ENRICHED_CSV = MAPPINGS_DIR / "atomic_enriched.csv"
ATOMIC_REVIEW_CSV = MAPPINGS_DIR / "atomic_review.csv"

TOOL = "claude-opus-4-6+ohdsi-vocab-mcp"
REVIEWER = "claude-opus-4-6"
RTYPE = "llm"
RDATE = "2026-03-08"


class AtomicReviewBuilder:
    """Builds atomic review rows from a slice of the enriched CSV."""

    def __init__(self, agent_num, start_line, end_line,
                 output_dir=None, prefix="atomic_review__subagent_"):
        if output_dir is None:
            from atomic_config import SUBAGENT_CSV_DIR
            output_dir = SUBAGENT_CSV_DIR
        os.makedirs(output_dir, exist_ok=True)
        self.agent_num = agent_num
        self.start_line = start_line
        self.end_line = end_line
        self.output_path = os.path.join(output_dir, f"{prefix}{agent_num}.csv")
        self.source_csv = ATOMIC_ENRICHED_CSV
        self.rows = []
        self._source_data = None

    def source_items(self):
        """Yield (code, desc, full_row_dict) for assigned lines.

        Lines are 1-indexed (line 1 = header, line 2 = first data row).
        Codes already in atomic_review.csv are automatically skipped.
        """
        if self._source_data is None:
            self._source_data = []
            # Load already-reviewed codes to skip
            reviewed_codes = set()
            if ATOMIC_REVIEW_CSV.exists():
                with open(ATOMIC_REVIEW_CSV, newline="") as f:
                    reader = csv.DictReader(f)
                    reviewed_codes = {r["source_concept_code"] for r in reader}

            with open(self.source_csv, newline="") as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader, start=2):
                    if i < self.start_line:
                        continue
                    if i > self.end_line:
                        break
                    code = row.get("source_concept_code", "").strip()
                    if code in reviewed_codes:
                        continue
                    self._source_data.append(row)

            if reviewed_codes:
                print(f"[AtomicReviewBuilder] Skipped already-reviewed codes. "
                      f"Items to review: {len(self._source_data)}")

        for row in self._source_data:
            code = row.get("source_concept_code", "").strip()
            desc = row.get("source_description", "").strip()
            yield code, desc, row

    def skip(self, code, desc, justification):
        self.rows.append([
            code, desc, "skip",
            "", "", "", "", "", "", "",
            "", "", "",
            justification, "no", TOOL, REVIEWER, RTYPE, RDATE,
        ])

    def map_row(self, code, desc, tcid, tname, tvocab, tcode,
                pred, conf, domain, justification,
                qcid="", qcname="", qrel=""):
        self.rows.append([
            code, desc, "map",
            tcid, tname, tvocab, tcode, pred, conf, domain,
            qcid, qcname, qrel,
            justification, "no", TOOL, REVIEWER, RTYPE, RDATE,
        ])

    def flag(self, code, desc, justification):
        self.rows.append([
            code, desc, "flag",
            "", "", "", "", "", "", "",
            "", "", "",
            justification, "no", TOOL, REVIEWER, RTYPE, RDATE,
        ])

    def write(self):
        with open(self.output_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(self.rows)

        mapped = sum(1 for r in self.rows if r[2] == "map")
        skipped = sum(1 for r in self.rows if r[2] == "skip")
        flagged = sum(1 for r in self.rows if r[2] == "flag")
        print(f"Total rows: {len(self.rows)}")
        print(f"Mapped: {mapped}")
        print(f"Skipped: {skipped}")
        if flagged:
            print(f"Flagged: {flagged}")
        print(f"Output: {self.output_path}")

    def unhandled(self):
        """Return source items that haven't been added to rows yet."""
        handled_codes = {r[0] for r in self.rows}
        return [
            (code, desc) for code, desc, _ in self.source_items()
            if code not in handled_codes
        ]
