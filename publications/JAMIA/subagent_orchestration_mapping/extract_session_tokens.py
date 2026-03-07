#!/usr/bin/env python3
"""Extract content size metrics from Claude Code session JSONL files.

Parses ~/.claude-history/projects/ to find orchestrator sessions that launched
subagent clinical review runs. Measures content size per message (characters
and words) and outputs per-session and per-subagent breakdowns.

No external API calls required — runs entirely locally.

Usage:
    uv run python extract_session_tokens.py [--output-dir DIR] [--project-filter SUBSTR]

Output:
    session_token_summary.csv   — one row per session
    subagent_token_detail.csv   — one row per subagent launch within a session
    token_extraction_report.txt — human-readable summary
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Content measurement
# ---------------------------------------------------------------------------

@dataclass
class ContentMetrics:
    chars: int = 0
    words: int = 0
    lines: int = 0

    def __add__(self, other: "ContentMetrics") -> "ContentMetrics":
        return ContentMetrics(
            chars=self.chars + other.chars,
            words=self.words + other.words,
            lines=self.lines + other.lines,
        )


ZERO = ContentMetrics()


def measure(text: str) -> ContentMetrics:
    """Measure content size — purely local, no API calls."""
    if not text:
        return ContentMetrics()
    return ContentMetrics(
        chars=len(text),
        words=len(text.split()),
        lines=text.count("\n") + 1,
    )


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SubagentCall:
    """A single Agent tool invocation within an orchestrator session."""
    agent_index: int
    prompt_text: str = ""
    result_text: str = ""
    prompt_metrics: ContentMetrics = field(default_factory=ContentMetrics)
    result_metrics: ContentMetrics = field(default_factory=ContentMetrics)
    description: str = ""
    timestamp: str = ""
    is_clinical_review: bool = False


@dataclass
class SessionSummary:
    session_id: str
    project_name: str
    jsonl_path: str
    created: str = ""
    modified: str = ""
    model: str = ""
    message_count: int = 0
    user_messages: int = 0
    assistant_messages: int = 0
    system_messages: int = 0
    user_metrics: ContentMetrics = field(default_factory=ContentMetrics)
    assistant_metrics: ContentMetrics = field(default_factory=ContentMetrics)
    tool_calls: int = 0
    agent_tool_calls: int = 0
    subagents: list[SubagentCall] = field(default_factory=list)

    @property
    def total_metrics(self) -> ContentMetrics:
        return self.user_metrics + self.assistant_metrics


# ---------------------------------------------------------------------------
# JSONL parsing
# ---------------------------------------------------------------------------

def extract_text(content) -> str:
    """Extract plain text from a message content field."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                btype = block.get("type", "")
                if btype == "text":
                    parts.append(block.get("text", ""))
                elif btype == "tool_use":
                    parts.append(f"[tool_use: {block.get('name', '')}]")
                    inp = block.get("input", {})
                    if isinstance(inp, dict):
                        for v in inp.values():
                            if isinstance(v, str):
                                parts.append(v)
                    elif isinstance(inp, str):
                        parts.append(inp)
                elif btype == "tool_result":
                    parts.append(extract_text(block.get("content", "")))
                elif btype == "thinking":
                    parts.append(block.get("thinking", ""))
        return "\n".join(parts)
    return str(content) if content else ""


CLINICAL_KEYWORDS = [
    "clinical review", "sub-agent", "subagent",
    "reviewbuilder", "unmappable", "enriched csv",
    "flowsheet", "planning agent",
]


def parse_session(jsonl_path: str) -> SessionSummary:
    """Parse a single session JSONL file."""
    path = Path(jsonl_path)
    summary = SessionSummary(
        session_id=path.stem,
        project_name=path.parent.name,
        jsonl_path=str(path),
    )

    agent_index = 0
    pending_agents: dict[str, SubagentCall] = {}

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            rtype = record.get("type", "")
            timestamp = record.get("timestamp", "")

            if timestamp:
                if not summary.created or timestamp < summary.created:
                    summary.created = timestamp
                if not summary.modified or timestamp > summary.modified:
                    summary.modified = timestamp

            if rtype == "system":
                summary.system_messages += 1
                summary.message_count += 1
                continue

            if rtype not in ("user", "assistant"):
                continue

            summary.message_count += 1
            msg = record.get("message", {})
            content = msg.get("content", record.get("content", ""))

            if rtype == "assistant" and not summary.model:
                m = msg.get("model", "")
                if m:
                    summary.model = m

            text = extract_text(content)
            metrics = measure(text)

            if rtype == "user":
                summary.user_messages += 1
                summary.user_metrics = summary.user_metrics + metrics
            else:
                summary.assistant_messages += 1
                summary.assistant_metrics = summary.assistant_metrics + metrics

            # Scan for Agent tool calls and results
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue

                    btype = block.get("type", "")

                    if btype == "tool_use":
                        summary.tool_calls += 1
                        tool_name = block.get("name", "")

                        if tool_name == "Agent":
                            summary.agent_tool_calls += 1
                            agent_index += 1
                            inp = block.get("input", {})
                            prompt_text = inp.get("prompt", "")
                            desc = inp.get("description", "")
                            tool_use_id = block.get("id", f"unknown-{agent_index}")

                            is_clinical = any(
                                kw in prompt_text.lower() for kw in CLINICAL_KEYWORDS
                            )

                            sa = SubagentCall(
                                agent_index=agent_index,
                                prompt_text=prompt_text,
                                prompt_metrics=measure(prompt_text),
                                description=desc,
                                timestamp=timestamp,
                                is_clinical_review=is_clinical,
                            )
                            pending_agents[tool_use_id] = sa
                            summary.subagents.append(sa)

                    elif btype == "tool_result":
                        tool_use_id = block.get("tool_use_id", "")
                        if tool_use_id in pending_agents:
                            result_text = extract_text(block.get("content", ""))
                            sa = pending_agents.pop(tool_use_id)
                            sa.result_text = result_text
                            sa.result_metrics = measure(result_text)

    return summary


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def discover_sessions(project_filter: str | None = None) -> list[str]:
    """Find all JSONL session files under ~/.claude/projects/."""
    history_dir = Path.home() / ".claude" / "projects"
    if not history_dir.exists():
        print(f"ERROR: {history_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    paths = []
    for project_dir in sorted(history_dir.iterdir()):
        if not project_dir.is_dir():
            continue
        if project_filter and project_filter not in project_dir.name:
            continue
        # JSONL files live directly in the project dir
        for f in sorted(project_dir.glob("*.jsonl")):
            paths.append(str(f))
        # Also check any subdirectories (subagents, etc.)
        for f in sorted(project_dir.rglob("*.jsonl")):
            if str(f) not in paths:
                paths.append(str(f))

    return paths


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_outputs(summaries: list[SessionSummary], output_dir: str):
    os.makedirs(output_dir, exist_ok=True)

    # --- session_token_summary.csv ---
    session_csv = os.path.join(output_dir, "session_token_summary.csv")
    with open(session_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "session_id", "project_name", "created", "modified", "model",
            "message_count", "user_messages", "assistant_messages",
            "user_chars", "user_words", "assistant_chars", "assistant_words",
            "total_chars", "total_words",
            "tool_calls", "agent_tool_calls",
            "clinical_subagents", "non_clinical_subagents",
        ])
        for s in summaries:
            t = s.total_metrics
            clinical = sum(1 for sa in s.subagents if sa.is_clinical_review)
            w.writerow([
                s.session_id, s.project_name, s.created, s.modified, s.model,
                s.message_count, s.user_messages, s.assistant_messages,
                s.user_metrics.chars, s.user_metrics.words,
                s.assistant_metrics.chars, s.assistant_metrics.words,
                t.chars, t.words,
                s.tool_calls, s.agent_tool_calls,
                clinical, len(s.subagents) - clinical,
            ])
    print(f"Wrote {session_csv}")

    # --- subagent_token_detail.csv ---
    subagent_csv = os.path.join(output_dir, "subagent_token_detail.csv")
    with open(subagent_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "session_id", "agent_index", "description", "timestamp",
            "is_clinical_review",
            "prompt_chars", "prompt_words",
            "result_chars", "result_words",
            "total_chars", "total_words",
        ])
        for s in summaries:
            for sa in s.subagents:
                total = sa.prompt_metrics + sa.result_metrics
                w.writerow([
                    s.session_id, sa.agent_index, sa.description, sa.timestamp,
                    sa.is_clinical_review,
                    sa.prompt_metrics.chars, sa.prompt_metrics.words,
                    sa.result_metrics.chars, sa.result_metrics.words,
                    total.chars, total.words,
                ])
    print(f"Wrote {subagent_csv}")

    # --- token_extraction_report.txt ---
    report_path = os.path.join(output_dir, "token_extraction_report.txt")
    with open(report_path, "w") as f:
        f.write("Content Size Extraction Report\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Sessions analyzed: {len(summaries)}\n")
        f.write("=" * 70 + "\n\n")

        total_all = sum((s.total_metrics.chars for s in summaries))
        total_words = sum((s.total_metrics.words for s in summaries))
        total_agent_calls = sum(s.agent_tool_calls for s in summaries)
        all_subagents = [sa for s in summaries for sa in s.subagents]
        clinical_subagents = [sa for sa in all_subagents if sa.is_clinical_review]

        f.write("AGGREGATE SUMMARY\n")
        f.write(f"  Total sessions:           {len(summaries)}\n")
        f.write(f"  Total characters:         {total_all:,}\n")
        f.write(f"  Total words:              {total_words:,}\n")
        f.write(f"  Total Agent tool calls:   {total_agent_calls}\n")
        f.write(f"  Clinical review agents:   {len(clinical_subagents)}\n")
        f.write("\n")

        if clinical_subagents:
            prompt_chars = [sa.prompt_metrics.chars for sa in clinical_subagents]
            result_chars = [sa.result_metrics.chars for sa in clinical_subagents]
            total_chars = [sa.prompt_metrics.chars + sa.result_metrics.chars
                           for sa in clinical_subagents]
            prompt_words = [sa.prompt_metrics.words for sa in clinical_subagents]
            result_words = [sa.result_metrics.words for sa in clinical_subagents]

            f.write("CLINICAL SUBAGENT SIZE DISTRIBUTION\n")
            f.write(f"  Count:          {len(clinical_subagents)}\n")
            f.write(f"  Prompt chars:   min={min(prompt_chars):,}  "
                    f"max={max(prompt_chars):,}  "
                    f"mean={sum(prompt_chars) // len(prompt_chars):,}  "
                    f"total={sum(prompt_chars):,}\n")
            f.write(f"  Result chars:   min={min(result_chars):,}  "
                    f"max={max(result_chars):,}  "
                    f"mean={sum(result_chars) // len(result_chars):,}  "
                    f"total={sum(result_chars):,}\n")
            f.write(f"  Total chars:    min={min(total_chars):,}  "
                    f"max={max(total_chars):,}  "
                    f"mean={sum(total_chars) // len(total_chars):,}  "
                    f"total={sum(total_chars):,}\n")
            f.write(f"  Prompt words:   min={min(prompt_words):,}  "
                    f"max={max(prompt_words):,}  "
                    f"mean={sum(prompt_words) // len(prompt_words):,}  "
                    f"total={sum(prompt_words):,}\n")
            f.write(f"  Result words:   min={min(result_words):,}  "
                    f"max={max(result_words):,}  "
                    f"mean={sum(result_words) // len(result_words):,}  "
                    f"total={sum(result_words):,}\n")
            f.write("\n")

        f.write("PER-SESSION BREAKDOWN\n")
        f.write("-" * 70 + "\n")
        for s in summaries:
            t = s.total_metrics
            clinical = sum(1 for sa in s.subagents if sa.is_clinical_review)
            f.write(f"\nSession: {s.session_id[:12]}...\n")
            f.write(f"  Project:    {s.project_name}\n")
            f.write(f"  Created:    {s.created}\n")
            f.write(f"  Model:      {s.model}\n")
            f.write(f"  Messages:   {s.message_count} "
                    f"(user={s.user_messages}, asst={s.assistant_messages})\n")
            f.write(f"  Size:       {t.chars:,} chars / {t.words:,} words "
                    f"(user={s.user_metrics.chars:,}, "
                    f"asst={s.assistant_metrics.chars:,})\n")
            f.write(f"  Tool calls: {s.tool_calls} "
                    f"(Agent={s.agent_tool_calls}, clinical={clinical})\n")

            if s.subagents:
                f.write("  Subagents:\n")
                for sa in s.subagents:
                    tag = " [CLINICAL]" if sa.is_clinical_review else ""
                    total = sa.prompt_metrics + sa.result_metrics
                    f.write(f"    #{sa.agent_index}: {sa.description}{tag}\n")
                    f.write(f"      prompt={sa.prompt_metrics.chars:,}c "
                            f"result={sa.result_metrics.chars:,}c "
                            f"total={total.chars:,}c\n")

    print(f"Wrote {report_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Extract content size metrics from Claude Code sessions"
    )
    parser.add_argument(
        "--output-dir",
        default="publications/JAMIA/subagent_orchestration_mapping",
    )
    parser.add_argument(
        "--project-filter",
        default=None,
        help="Only process projects whose dir name contains this substring",
    )
    args = parser.parse_args()

    paths = discover_sessions(args.project_filter)
    if not paths:
        print("No session files found.", file=sys.stderr)
        if args.project_filter:
            print(f"  (filter was: '{args.project_filter}')", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(paths)} session files")

    summaries = []
    for i, path in enumerate(paths, 1):
        print(f"  [{i}/{len(paths)}] {Path(path).name}...", end=" ", flush=True)
        try:
            s = parse_session(path)
            summaries.append(s)
            t = s.total_metrics
            print(f"{s.message_count} msgs, {t.chars:,} chars, "
                  f"{s.agent_tool_calls} agents")
        except Exception as e:
            print(f"ERROR: {e}")

    summaries.sort(key=lambda s: s.created or "")
    write_outputs(summaries, args.output_dir)


if __name__ == "__main__":
    main()
