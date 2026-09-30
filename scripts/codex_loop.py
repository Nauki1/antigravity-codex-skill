#!/usr/bin/env python3
"""
Codex Automation Loop Script (Dual-Agent Collaboration Engine)
Project: codex-loop
Supports: Google Antigravity (Gemini) <-> OpenAI Codex CLI (gpt-6.1-sol / o3)
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Ensure UTF-8 stdout/stderr on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def find_codex_binary():
    """Locate the Codex CLI executable across environments, prioritizing user's active runtime."""
    # 1. Check ~/.codex/config.toml for CODEX_CLI_PATH
    config_toml = Path.home() / ".codex" / "config.toml"
    if config_toml.exists():
        try:
            for line in config_toml.read_text(encoding="utf-8").splitlines():
                if "CODEX_CLI_PATH" in line and "=" in line:
                    raw_val = line.split("=", 1)[1].strip().strip("'\"")
                    if os.path.exists(raw_val):
                        return raw_val
        except Exception:
            pass

    # 2. Check standard Windows AppData Local paths
    appdata_pattern = str(Path.home() / "AppData" / "Local" / "OpenAI" / "Codex" / "bin" / "*" / "codex.exe")
    matches = glob.glob(appdata_pattern)
    if matches and os.path.exists(matches[0]):
        return matches[0]

    # 3. Check system PATH
    in_path = shutil.which("codex")
    if in_path:
        return in_path

    # 4. Check Unix / WSL local bin
    unix_bin = os.path.expanduser("~/.local/bin/codex")
    if os.path.exists(unix_bin):
        return unix_bin

    # 5. Check sandbox or plugin directories
    candidates = [
        Path.home() / ".codex" / ".sandbox-bin" / "codex.exe",
        Path.home() / ".codex" / "plugins" / ".plugin-appserver" / "codex.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)

    return "codex"


CODEX_BIN = find_codex_binary()


def get_current_info():
    """Inspect local codex configuration, active model, and auth mode."""
    info = {
        "binary_path": CODEX_BIN,
        "binary_exists": os.path.exists(CODEX_BIN) if os.path.isabs(CODEX_BIN) else bool(shutil.which(CODEX_BIN)),
        "active_model": "gpt-6.1-sol",
        "reasoning_effort": "xhigh",
        "auth_mode": "unknown",
        "config_exists": False,
    }
    config_path = Path.home() / ".codex" / "config.toml"
    auth_path = Path.home() / ".codex" / "auth.json"

    if config_path.exists():
        info["config_exists"] = True
        try:
            for line in config_path.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if s.startswith("model ="):
                    info["active_model"] = s.split("=", 1)[1].strip().strip("'\"")
                elif s.startswith("model_reasoning_effort ="):
                    info["reasoning_effort"] = s.split("=", 1)[1].strip().strip("'\"")
        except Exception:
            pass

    if auth_path.exists():
        try:
            auth_data = json.loads(auth_path.read_text(encoding="utf-8"))
            info["auth_mode"] = auth_data.get("auth_mode", "unknown")
            info["account_id"] = auth_data.get("account_id", "")
        except Exception:
            pass

    return info


def run_plan(prompt, model=None, reasoning_effort="xhigh", target_file=None):
    """Run Codex in non-interactive exec mode to generate an implementation blueprint."""
    current_info = get_current_info()
    effective_model = model or current_info.get("active_model", "gpt-6.1-sol")

    cmd = [CODEX_BIN, "exec", "--skip-git-repo-check", "--ephemeral", "--sandbox", "read-only"]
    if effective_model:
        cmd.extend(["-c", f'model="{effective_model}"'])
    if reasoning_effort:
        cmd.extend(["-c", f'model_reasoning_effort="{reasoning_effort}"'])

    full_prompt = (
        f"你现在作为首席架构师，负责为当前项目制定实施计划与开发规则。\n"
        f"用户需求：\n{prompt}\n\n"
        f"请输出规范清晰的技术设计、步骤分解（Checklist）和质量约束。\n"
        f"要求：输出结构清晰的 Markdown。"
    )
    cmd.append(full_prompt)

    print(f"[*] 启动 Codex 规划中 (Model: {effective_model}, Reasoning: {reasoning_effort})...", file=sys.stderr)
    res = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, encoding="utf-8", errors="replace")

    if res.returncode != 0:
        err_msg = res.stderr or ""
        print(f"[!] Codex 规划执行失败 (code {res.returncode}):\n{err_msg}", file=sys.stderr)
        return False, err_msg

    output = (res.stdout or "").strip()
    if target_file:
        p = Path(target_file)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(output, encoding="utf-8")
        print(f"[*] 规划已写入文件: {target_file}", file=sys.stderr)

    print(output)
    return True, output


def run_review(instructions=None, model=None, base=None):
    """Run Codex code review against uncommitted changes."""
    current_info = get_current_info()
    effective_model = model or current_info.get("active_model", "gpt-6.1-sol")

    cmd = [CODEX_BIN, "review", "--uncommitted"]
    if effective_model:
        cmd.extend(["-c", f'model="{effective_model}"'])
    if base:
        cmd.extend(["--base", base])
    if instructions:
        cmd.append(instructions)

    print(f"[*] 启动 Codex 代码审查中 (Model: {effective_model})...", file=sys.stderr)
    res = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, encoding="utf-8", errors="replace")

    if res.returncode != 0:
        err_msg = res.stderr or ""
        print(f"[!] Codex 审查执行失败 (code {res.returncode}):\n{err_msg}", file=sys.stderr)
        return False, err_msg

    output = (res.stdout or "").strip()
    output_lower = output.lower()
    is_approved = (
        "APPROVED" in output.splitlines()[-3:]
        or "APPROVED" in output[-60:]
        or "no actionable regressions" in output_lower
        or "no regressions" in output_lower
        or "looks good" in output_lower
        or "lgtm" in output_lower
    )
    print(output)
    print(f"\n[*] 审查结果判定: {'已通过 (APPROVED)' if is_approved else '需要修改 (REJECTED/ACTION_NEEDED)'}", file=sys.stderr)
    return is_approved, output


def main():
    parser = argparse.ArgumentParser(description="Codex Automation Loop Runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: info
    subparsers.add_parser("info", help="Show current active Codex configuration")

    # Subcommand: plan
    p_plan = subparsers.add_parser("plan", help="Generate task plan via codex exec")
    p_plan.add_argument("prompt", help="Task requirement description")
    p_plan.add_argument("--model", "-m", help="Specific model (default: config or gpt-6.1-sol)")
    p_plan.add_argument("--reasoning", "-r", default="xhigh", help="Reasoning effort (low/medium/high/xhigh)")
    p_plan.add_argument("--out", "-o", help="Target output file (e.g. docs/architecture.md)")

    # Subcommand: review
    p_review = subparsers.add_parser("review", help="Review current uncommitted diff")
    p_review.add_argument("--instructions", "-i", help="Custom review instructions")
    p_review.add_argument("--model", "-m", help="Specific review model")
    p_review.add_argument("--base", "-b", help="Base branch")

    args = parser.parse_args()

    if args.command == "info":
        print(json.dumps(get_current_info(), indent=2, ensure_ascii=False))
    elif args.command == "plan":
        success, _ = run_plan(args.prompt, model=args.model, reasoning_effort=args.reasoning, target_file=args.out)
        sys.exit(0 if success else 1)
    elif args.command == "review":
        approved, _ = run_review(instructions=args.instructions, model=args.model, base=args.base)
        sys.exit(0 if approved else 2)


if __name__ == "__main__":
    main()
