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
import re
import sys
from pathlib import Path

# Ensure UTF-8 stdout/stderr on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def get_brain_root():
    """Return the base directory for Antigravity brain logs."""
    return Path.home() / ".gemini" / "antigravity" / "brain"


def list_sessions(limit=15):
    """List recent conversation sessions found in brain storage."""
    brain_root = get_brain_root()
    if not brain_root.exists():
        print(f"[!] Brain directory not found: {brain_root}", file=sys.stderr)
        return []

    sessions = []
    for d in brain_root.iterdir():
        if not d.is_dir():
            continue
        transcript = d / ".system_generated" / "logs" / "transcript.jsonl"
        if not transcript.exists():
            continue

        mtime = transcript.stat().st_mtime
        time_str = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        
        # Read the first user prompt to identify session topic
        first_prompt = "(No user input recorded)"
        try:
            with open(transcript, "r", encoding="utf-8") as f:
                for line in f:
                    data = json.loads(line)
                    if data.get("type") == "USER_INPUT":
                        content = data.get("content", "")
                        clean = clean_content(content)
                        first_prompt = clean.replace("\n", " ").strip()
                        if len(first_prompt) > 70:
                            first_prompt = first_prompt[:67] + "..."
                        break
        except Exception:
            pass

        sessions.append({
            "conv_id": d.name,
            "path": transcript,
            "mtime": mtime,
            "time_str": time_str,
            "preview": first_prompt,
        })

    sessions.sort(key=lambda s: s["mtime"], reverse=True)
    return sessions[:limit]


def find_transcript(conv_id=None):
    """Locate a transcript by conversation ID or find the latest modified."""
    brain_root = get_brain_root()
    if not brain_root.exists():
        return None, None

    if conv_id:
        target_dir = brain_root / conv_id
        transcript_path = target_dir / ".system_generated" / "logs" / "transcript.jsonl"
        if transcript_path.exists():
            return conv_id, transcript_path
        return None, None

    # Fallback to latest
    dirs = [d for d in brain_root.iterdir() if d.is_dir() and (d / ".system_generated" / "logs" / "transcript.jsonl").exists()]
    if not dirs:
        return None, None

    latest_dir = max(dirs, key=lambda d: d.stat().st_mtime)
    transcript_path = latest_dir / ".system_generated" / "logs" / "transcript.jsonl"
    return latest_dir.name, transcript_path


def clean_content(content):
    """Strip verified outer XML envelope while preserving attachments, skill/item mentions, and nested code blocks."""
    if not content:
        return ""

    raw = content.strip()
    if not raw.startswith("<USER_REQUEST>"):
        return raw

    # 1. Identify outer request boundary first: locate the last closing tag of the envelope
    last_close_idx = raw.rfind("</USER_REQUEST>")
    if last_close_idx == -1:
        return raw

    user_body = raw[len("<USER_REQUEST>"):last_close_idx].strip()
    trailing = raw[last_close_idx + len("</USER_REQUEST>"):].strip()

    if not trailing:
        return user_body

    # 2. Identify the verified outer system blocks in trailing
    meta_body = None
    if trailing.startswith("<ADDITIONAL_METADATA>"):
        meta_start = len("<ADDITIONAL_METADATA>")
        if trailing.endswith("</USER_SETTINGS_CHANGE>"):
            settings_start = trailing.rfind("<USER_SETTINGS_CHANGE>")
            if settings_start == -1 or settings_start <= meta_start:
                return raw
            meta_end = trailing.rfind("</ADDITIONAL_METADATA>", meta_start, settings_start)
            if meta_end == -1 or meta_end <= meta_start:
                return raw
            meta_body = trailing[meta_start:meta_end].strip()
        elif trailing.endswith("</ADDITIONAL_METADATA>"):
            meta_end = len(trailing) - len("</ADDITIONAL_METADATA>")
            meta_body = trailing[meta_start:meta_end].strip()
        else:
            return raw
    elif trailing.startswith("<USER_SETTINGS_CHANGE>") and trailing.endswith("</USER_SETTINGS_CHANGE>"):
        meta_body = None
    else:
        return raw

    # 3. Clean trailing metadata if present, strictly removing only verified system boilerplate
    attachments = []
    if meta_body:
        # Restrict timestamp removal strictly to the verified platform ISO-8601 timestamp line at the beginning
        cleaned_meta = re.sub(
            r"^\s*The current local time is:\s*\d{4}-\d{2}-\d{2}T[0-9:+-]+\.\s*\n?",
            "",
            meta_body
        )
        # Restrict hint removal strictly to the platform boilerplate hint
        cleaned_meta = re.sub(
            r"\n?\s*You can embed (?:this image|these images) in an artifact if you need the USER to review (?:it|them)\.\s*$",
            "",
            cleaned_meta
        ).strip()
        if cleaned_meta:
            attachments.append(cleaned_meta)

    result = user_body
    if attachments:
        formatted = "\n> ".join("\n".join(attachments).splitlines())
        result += "\n\n> 📎 **Context Metadata & Attachments**:\n> " + formatted

    return result


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


def export_session_to_markdown(conv_id, records, title, output_file, summary=None):
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
    ]

    if summary:
        md.append(f"{summary.strip()}\n")
    else:
        md.append("> 本记录由 Antigravity 自动同步至项目工作区，作为 Codex 与后续会话的持久化上下文。\n")

    md.extend([
        "---",
        "",
        "## Conversation Highlights",
        "",
    ])

    turn_idx = 1
    for item in records:
        item_type = item.get("type", "")
        content = item.get("content", "")

        if item_type == "USER_INPUT" and content:
            cleaned_text = clean_content(content)
            if cleaned_text:
                md.append(f"### 👤 User (Turn {turn_idx})")
                md.append(f"{cleaned_text}\n")
                turn_idx += 1
        elif item_type == "PLANNER_RESPONSE" and content:
            md.append(f"### 🤖 Antigravity (Gemini)")
            md.append(f"{content.strip()}\n")

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(md), encoding="utf-8")
    print(f"[*] 会话记录已成功同步到: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Sync Antigravity session into project workspace")
    parser.add_argument("--list", "-l", action="store_true", help="List recent conversation sessions")
    parser.add_argument("--conv-id", "-c", help="Specific conversation ID to sync")
    parser.add_argument("--title", "-t", default="session-notes", help="Title / topic of the session")
    parser.add_argument("--summary", "-s", help="Custom executive summary text")
    parser.add_argument("--out", "-o", help="Target output file path")
    parser.add_argument("--project", "-P", help="Target project root directory (default: current workspace / git root)")
    args = parser.parse_args()

    if args.list:
        sessions = list_sessions()
        print(f"\n{'='*75}\n  Recent Antigravity Sessions ({len(sessions)} found)\n{'='*75}")
        for s in sessions:
            print(f"[{s['time_str']}] {s['conv_id']}\n  -> {s['preview']}\n")
        return

    # Import target project resolution from codex_loop
    try:
        from codex_loop import resolve_target_project
    except ImportError:
        sys.path.insert(0, str(Path(__file__).parent))
        from codex_loop import resolve_target_project

    target_project = resolve_target_project(args.project)

    conv_id, transcript_path = find_transcript(conv_id=args.conv_id)
    if not transcript_path or not transcript_path.exists():
        target_name = args.conv_id or "latest"
        print(f"[!] 未找到会话 ({target_name}) 的 transcript.jsonl 文件", file=sys.stderr)
        sys.exit(1)

    now_date = datetime.date.today().strftime("%Y-%m-%d")
    clean_title = args.title.replace(" ", "-").lower()

    if args.out:
        out_p = Path(args.out)
        target_out = out_p if out_p.is_absolute() else target_project / out_p
    else:
        target_out = target_project / ".agents" / "sessions" / f"{now_date}-{clean_title}.md"

    records = parse_transcript(transcript_path)
    export_session_to_markdown(conv_id, records, args.title, target_out, summary=args.summary)


if __name__ == "__main__":
    main()

