#!/usr/bin/env python3
"""
Session Sync Tool for Antigravity & Codex
Exports/Syncs Antigravity conversation transcripts and design artifacts into the project workspace
Path: .agents/sessions/<date>-<title>.md
"""

import argparse
import datetime
import json
import os
import sys
from pathlib import Path


def find_latest_transcript():
    """Locate the most recent transcript in Antigravity's brain storage."""
    brain_root = Path.home() / ".gemini" / "antigravity" / "brain"
    if not brain_root.exists():
        return None, None

    # Find the latest modified conversation directory
    dirs = [d for d in brain_root.iterdir() if d.is_dir() and (d / ".system_generated" / "logs" / "transcript.jsonl").exists()]
    if not dirs:
        return None, None

    latest_dir = max(dirs, key=lambda d: d.stat().st_mtime)
    transcript_path = latest_dir / ".system_generated" / "logs" / "transcript.jsonl"
    return latest_dir.name, transcript_path


def parse_transcript(transcript_path):
    """Parse JSONL transcript into a structured conversation history."""
    records = []
    with open(transcript_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except Exception:
                continue
    return records


def export_session_to_markdown(conv_id, records, title, output_file):
    """Convert parsed records into a clean, human & LLM-readable Markdown document."""
    date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    md = [
        f"# Session Record: {title}",
        "",
        f"- **Date**: {date_str}",
        f"- **Conversation ID**: `{conv_id}`",
        f"- **Synchronized by**: `codex-loop/scripts/sync_session.py`",
        "",
        "---",
        "",
        "## Executive Summary & Key Decisions",
        "",
        "> 本记录由 Antigravity 自动同步至项目工作区，作为 Codex 与后续会话的持久化上下文。",
        "",
        "---",
        "",
        "## Conversation Highlights",
        "",
    ]

    for item in records:
        source = item.get("source", "")
        item_type = item.get("type", "")
        content = item.get("content", "")

        if item_type == "USER_INPUT" and content:
            md.append("### 👤 User")
            md.append(f"{content.strip()}\n")
        elif item_type == "PLANNER_RESPONSE" and content:
            md.append("### 🤖 Antigravity (Gemini)")
            md.append(f"{content.strip()}\n")

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(md), encoding="utf-8")
    print(f"[*] 会话记录已成功同步到: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Sync Antigravity session into project workspace")
    parser.add_argument("--title", "-t", default="session-notes", help="Title / topic of the session")
    parser.add_argument("--out", "-o", help="Target output file path")
    args = parser.parse_args()

    conv_id, transcript_path = find_latest_transcript()
    if not transcript_path or not transcript_path.exists():
        print("[!] 未找到当前 Antigravity 会话的 transcript.jsonl 文件", file=sys.stderr)
        sys.exit(1)

    now_date = datetime.date.today().strftime("%Y-%m-%d")
    clean_title = args.title.replace(" ", "-").lower()
    default_out = Path(".agents") / "sessions" / f"{now_date}-{clean_title}.md"
    target_out = Path(args.out) if args.out else default_out

    records = parse_transcript(transcript_path)
    export_session_to_markdown(conv_id, records, args.title, target_out)


if __name__ == "__main__":
    main()
