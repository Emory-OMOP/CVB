#!/usr/bin/env python3
"""Aggregate session token/content counts into publication-ready tables.

Reads session_token_summary.csv and links orchestrator sessions to their
child subagent sessions by timestamp containment. Produces hierarchical
counts for the JAMIA paper.

Usage:
    uv run python aggregate_counts.py
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent


@dataclass
class Session:
    session_id: str
    project_name: str
    created: str
    modified: str
    model: str
    message_count: int
    user_messages: int
    assistant_messages: int
    user_chars: int
    user_words: int
    assistant_chars: int
    assistant_words: int
    total_chars: int
    total_words: int
    tool_calls: int
    agent_tool_calls: int
    clinical_subagents: int
    non_clinical_subagents: int

    @property
    def is_orchestrator(self) -> bool:
        return self.project_name != "subagents"

    @property
    def is_subagent(self) -> bool:
        return self.project_name == "subagents" and not self.is_compact

    @property
    def is_compact(self) -> bool:
        return "compact" in self.session_id

    @property
    def is_empty(self) -> bool:
        return self.message_count == 0

    @property
    def created_dt(self) -> datetime | None:
        if not self.created:
            return None
        return datetime.fromisoformat(self.created.replace("Z", "+00:00"))

    @property
    def modified_dt(self) -> datetime | None:
        if not self.modified:
            return None
        return datetime.fromisoformat(self.modified.replace("Z", "+00:00"))

    @property
    def duration_minutes(self) -> float | None:
        c, m = self.created_dt, self.modified_dt
        if c and m:
            return (m - c).total_seconds() / 60.0
        return None


def load_sessions() -> list[Session]:
    rows = []
    with open(DATA_DIR / "session_token_summary.csv") as f:
        for r in csv.DictReader(f):
            rows.append(Session(
                session_id=r["session_id"],
                project_name=r["project_name"],
                created=r["created"],
                modified=r["modified"],
                model=r["model"],
                message_count=int(r["message_count"]),
                user_messages=int(r["user_messages"]),
                assistant_messages=int(r["assistant_messages"]),
                user_chars=int(r["user_chars"]),
                user_words=int(r["user_words"]),
                assistant_chars=int(r["assistant_chars"]),
                assistant_words=int(r["assistant_words"]),
                total_chars=int(r["total_chars"]),
                total_words=int(r["total_words"]),
                tool_calls=int(r["tool_calls"]),
                agent_tool_calls=int(r["agent_tool_calls"]),
                clinical_subagents=int(r["clinical_subagents"]),
                non_clinical_subagents=int(r["non_clinical_subagents"]),
            ))
    return rows


def link_parents(sessions: list[Session]) -> dict[str, list[Session]]:
    """Map orchestrator session_id -> list of child subagent sessions.

    A subagent belongs to an orchestrator if its created timestamp falls
    within the orchestrator's [created, modified] window.
    """
    orchestrators = [s for s in sessions if s.is_orchestrator and not s.is_empty]
    agents = [s for s in sessions if s.is_subagent]

    # Sort orchestrators by created time
    orchestrators.sort(key=lambda s: s.created or "")

    parent_map: dict[str, list[Session]] = {o.session_id: [] for o in orchestrators}

    for agent in agents:
        adt = agent.created_dt
        if not adt:
            continue
        # Find the orchestrator whose window contains this agent
        best = None
        for o in orchestrators:
            odt = o.created_dt
            omdt = o.modified_dt
            if odt and omdt and odt <= adt <= omdt:
                best = o
                break  # Take the first (earliest) match
        if best:
            parent_map[best.session_id].append(agent)

    return parent_map


def fmt(n: int) -> str:
    return f"{n:,}"


def write_report(sessions: list[Session], parent_map: dict[str, list[Session]]):
    out = DATA_DIR / "aggregate_report.txt"

    orchestrators = [s for s in sessions if s.is_orchestrator and not s.is_empty]
    all_agents = [s for s in sessions if s.is_subagent]
    compact = [s for s in sessions if s.is_compact]
    empty = [s for s in sessions if s.is_empty]

    # Identify clinical orchestration sessions (those that launched 10 review agents)
    clinical_orch = [
        o for o in orchestrators
        if len(parent_map.get(o.session_id, [])) >= 10
    ]
    clinical_agents = []
    for o in clinical_orch:
        clinical_agents.extend(parent_map[o.session_id])

    with open(out, "w") as f:
        W = f.write

        W("=" * 80 + "\n")
        W("SUBAGENT ORCHESTRATION — AGGREGATE COUNTS\n")
        W(f"Generated: {datetime.now().isoformat()}\n")
        W("=" * 80 + "\n\n")

        # ── OVERALL ──────────────────────────────────────────────────
        W("OVERALL COUNTS\n")
        W("-" * 60 + "\n")
        W(f"  Total session files:         {len(sessions)}\n")
        W(f"    Empty/abandoned:           {len(empty)}\n")
        W(f"    Orchestrator sessions:     {len(orchestrators)}\n")
        W(f"    Subagent sessions:         {len(all_agents)}\n")
        W(f"    Compact (context mgmt):    {len(compact)}\n")
        W(f"\n")

        total_chars = sum(s.total_chars for s in sessions if not s.is_empty)
        total_words = sum(s.total_words for s in sessions if not s.is_empty)
        total_msgs = sum(s.message_count for s in sessions if not s.is_empty)
        total_tools = sum(s.tool_calls for s in sessions if not s.is_empty)

        W(f"  Total characters:            {fmt(total_chars)}\n")
        W(f"  Total words:                 {fmt(total_words)}\n")
        W(f"  Total messages:              {fmt(total_msgs)}\n")
        W(f"  Total tool calls:            {fmt(total_tools)}\n")
        W("\n")

        # ── BY ROLE ──────────────────────────────────────────────────
        all_active = [s for s in sessions if not s.is_empty]
        user_chars = sum(s.user_chars for s in all_active)
        asst_chars = sum(s.assistant_chars for s in all_active)
        user_words = sum(s.user_words for s in all_active)
        asst_words = sum(s.assistant_words for s in all_active)

        W("BY ROLE (all sessions)\n")
        W("-" * 60 + "\n")
        W(f"  User (input):    {fmt(user_chars)} chars / {fmt(user_words)} words\n")
        W(f"  Assistant (out):  {fmt(asst_chars)} chars / {fmt(asst_words)} words\n")
        W(f"  Ratio (user:asst chars):  {user_chars / asst_chars:.2f}:1\n")
        W("\n")

        # ── BY MODEL ────────────────────────────────────────────────
        models: dict[str, dict] = {}
        for s in all_active:
            m = s.model or "unknown"
            if m not in models:
                models[m] = {"sessions": 0, "chars": 0, "words": 0,
                             "msgs": 0, "tools": 0}
            models[m]["sessions"] += 1
            models[m]["chars"] += s.total_chars
            models[m]["words"] += s.total_words
            models[m]["msgs"] += s.message_count
            models[m]["tools"] += s.tool_calls

        W("BY MODEL\n")
        W("-" * 60 + "\n")
        for m, d in sorted(models.items(), key=lambda x: -x[1]["chars"]):
            W(f"  {m}:\n")
            W(f"    Sessions: {d['sessions']}  |  "
              f"Chars: {fmt(d['chars'])}  |  "
              f"Words: {fmt(d['words'])}  |  "
              f"Msgs: {fmt(d['msgs'])}  |  "
              f"Tools: {fmt(d['tools'])}\n")
        W("\n")

        # ── BY SESSION TYPE ─────────────────────────────────────────
        W("BY SESSION TYPE\n")
        W("-" * 60 + "\n")
        for label, group in [
            ("Orchestrator", orchestrators),
            ("Subagent", all_agents),
            ("Compact", compact),
        ]:
            chars = sum(s.total_chars for s in group)
            words = sum(s.total_words for s in group)
            msgs = sum(s.message_count for s in group)
            tools = sum(s.tool_calls for s in group)
            W(f"  {label} ({len(group)} sessions):\n")
            W(f"    Chars: {fmt(chars)}  |  Words: {fmt(words)}  |  "
              f"Msgs: {fmt(msgs)}  |  Tools: {fmt(tools)}\n")
        W("\n")

        # ── CLINICAL ORCHESTRATION SESSIONS ─────────────────────────
        W("CLINICAL ORCHESTRATION SESSIONS (>=10 subagents)\n")
        W("-" * 60 + "\n")
        W(f"  Orchestrator sessions:  {len(clinical_orch)}\n")
        W(f"  Total subagents:        {len(clinical_agents)}\n")
        W("\n")

        for o in sorted(clinical_orch, key=lambda s: s.created or ""):
            children = parent_map[o.session_id]
            child_chars = sum(c.total_chars for c in children)
            child_words = sum(c.total_words for c in children)
            child_msgs = sum(c.message_count for c in children)
            child_tools = sum(c.tool_calls for c in children)
            combined_chars = o.total_chars + child_chars
            dur = o.duration_minutes

            W(f"  {o.session_id[:12]}...  [{o.created[:16] if o.created else '?'}]\n")
            W(f"    Duration:       {dur:.0f} min\n" if dur else "")
            W(f"    Model:          {o.model}\n")
            W(f"    Orchestrator:   {fmt(o.total_chars)} chars / "
              f"{fmt(o.total_words)} words / "
              f"{o.message_count} msgs / {o.tool_calls} tools\n")
            W(f"    Subagents ({len(children)}): {fmt(child_chars)} chars / "
              f"{fmt(child_words)} words / "
              f"{child_msgs} msgs / {child_tools} tools\n")
            W(f"    Combined:       {fmt(combined_chars)} chars\n")
            W("\n")

        # ── SUBAGENT DISTRIBUTION ───────────────────────────────────
        if clinical_agents:
            W("CLINICAL SUBAGENT DISTRIBUTION\n")
            W("-" * 60 + "\n")
            chars_list = [s.total_chars for s in clinical_agents]
            words_list = [s.total_words for s in clinical_agents]
            msgs_list = [s.message_count for s in clinical_agents]
            tools_list = [s.tool_calls for s in clinical_agents]
            dur_list = [s.duration_minutes for s in clinical_agents
                        if s.duration_minutes is not None]

            for label, data in [
                ("Chars", chars_list),
                ("Words", words_list),
                ("Messages", msgs_list),
                ("Tool calls", tools_list),
            ]:
                W(f"  {label}:\n")
                W(f"    min={fmt(min(data))}  max={fmt(max(data))}  "
                  f"mean={fmt(sum(data) // len(data))}  "
                  f"median={fmt(sorted(data)[len(data) // 2])}  "
                  f"total={fmt(sum(data))}\n")

            if dur_list:
                W(f"  Duration (min):\n")
                W(f"    min={min(dur_list):.1f}  max={max(dur_list):.1f}  "
                  f"mean={sum(dur_list) / len(dur_list):.1f}  "
                  f"median={sorted(dur_list)[len(dur_list) // 2]:.1f}  "
                  f"total={sum(dur_list):.0f}\n")
            W("\n")

            # Model breakdown within clinical subagents
            agent_models: dict[str, int] = {}
            for a in clinical_agents:
                m = a.model or "unknown"
                agent_models[m] = agent_models.get(m, 0) + 1
            W("  By model:\n")
            for m, c in sorted(agent_models.items(), key=lambda x: -x[1]):
                W(f"    {m}: {c} agents\n")
            W("\n")

        # ── TIMELINE ────────────────────────────────────────────────
        W("TIMELINE (orchestrator sessions, chronological)\n")
        W("-" * 60 + "\n")
        for o in sorted(orchestrators, key=lambda s: s.created or ""):
            children = parent_map.get(o.session_id, [])
            date = o.created[:10] if o.created else "????"
            dur = o.duration_minutes
            dur_str = f"{dur:.0f}m" if dur else "?"
            W(f"  {date}  {dur_str:>5}  "
              f"{fmt(o.total_chars):>10} chars  "
              f"{o.message_count:>4} msgs  "
              f"{o.tool_calls:>4} tools  "
              f"{len(children):>3} agents  "
              f"{o.session_id[:8]}\n")
        W("\n")

        # ── PUBLICATION TABLE ───────────────────────────────────────
        W("=" * 80 + "\n")
        W("PUBLICATION-READY SUMMARY TABLE\n")
        W("=" * 80 + "\n\n")

        date_range = ""
        dated = [s for s in orchestrators if s.created]
        if dated:
            first = min(s.created[:10] for s in dated)
            last = max(s.created[:10] for s in dated)
            date_range = f"{first} to {last}"

        orch_chars = sum(s.total_chars for s in orchestrators)
        agent_chars = sum(s.total_chars for s in all_agents)
        orch_tools = sum(s.tool_calls for s in orchestrators)
        agent_tools = sum(s.tool_calls for s in all_agents)

        W(f"  Date range:                    {date_range}\n")
        W(f"  Orchestrator sessions:         {len(orchestrators)}\n")
        W(f"  Subagent sessions:             {len(all_agents)}\n")
        W(f"  Total sessions (incl compact): {len(all_active)}\n")
        W(f"\n")
        W(f"  Orchestrator content:          {fmt(orch_chars)} chars / "
          f"{fmt(sum(s.total_words for s in orchestrators))} words\n")
        W(f"  Subagent content:              {fmt(agent_chars)} chars / "
          f"{fmt(sum(s.total_words for s in all_agents))} words\n")
        W(f"  Total content:                 {fmt(total_chars)} chars / "
          f"{fmt(total_words)} words\n")
        W(f"\n")
        W(f"  Orchestrator tool calls:       {fmt(orch_tools)}\n")
        W(f"  Subagent tool calls:           {fmt(agent_tools)}\n")
        W(f"  Total tool calls:              {fmt(total_tools)}\n")
        W(f"\n")
        W(f"  Total messages:                {fmt(total_msgs)}\n")
        W(f"  Avg chars/subagent session:    {fmt(agent_chars // len(all_agents) if all_agents else 0)}\n")
        W(f"  Avg msgs/subagent session:     "
          f"{sum(s.message_count for s in all_agents) // len(all_agents) if all_agents else 0}\n")
        W(f"  Avg tools/subagent session:    "
          f"{agent_tools // len(all_agents) if all_agents else 0}\n")

    print(f"Wrote {out}")


def write_csv(sessions: list[Session], parent_map: dict[str, list[Session]]):
    """Write a hierarchical CSV linking orchestrators to children."""
    out = DATA_DIR / "orchestrator_hierarchy.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "orchestrator_id", "date", "duration_min", "model",
            "orch_chars", "orch_words", "orch_msgs", "orch_tools",
            "num_subagents",
            "subagent_chars", "subagent_words", "subagent_msgs", "subagent_tools",
            "combined_chars", "combined_words",
        ])
        orchestrators = [s for s in sessions if s.is_orchestrator and not s.is_empty]
        for o in sorted(orchestrators, key=lambda s: s.created or ""):
            children = parent_map.get(o.session_id, [])
            child_chars = sum(c.total_chars for c in children)
            child_words = sum(c.total_words for c in children)
            child_msgs = sum(c.message_count for c in children)
            child_tools = sum(c.tool_calls for c in children)
            dur = o.duration_minutes
            w.writerow([
                o.session_id,
                o.created[:10] if o.created else "",
                f"{dur:.1f}" if dur else "",
                o.model,
                o.total_chars, o.total_words, o.message_count, o.tool_calls,
                len(children),
                child_chars, child_words, child_msgs, child_tools,
                o.total_chars + child_chars, o.total_words + child_words,
            ])
    print(f"Wrote {out}")


def main():
    sessions = load_sessions()
    parent_map = link_parents(sessions)
    write_report(sessions, parent_map)
    write_csv(sessions, parent_map)


if __name__ == "__main__":
    main()
