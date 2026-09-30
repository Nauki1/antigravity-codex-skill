#!/usr/bin/env python3
"""
Codex Automation Loop Script (Dual-Agent Collaboration Engine)
Project: codex-loop
Supports: Google Antigravity (Gemini) <-> OpenAI Codex CLI (gpt-6.1-sol / o3)
Target Project Parameterization: Enables using codex-loop from global skill across any project workspace.
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


def find_agy_binary():
    """Locate the Antigravity CLI executable."""
    in_path = shutil.which("agy")
    if in_path:
        return in_path
    win_agy = Path.home() / "AppData" / "Local" / "agy" / "bin" / "agy.exe"
    if win_agy.exists():
        return str(win_agy)
    return "agy"


CODEX_BIN = find_codex_binary()
AGY_BIN = find_agy_binary()


def resolve_target_project(project_arg=None):
    """
    Resolve the absolute Path of the target project workspace.
    If project_arg is given, resolve and ensure it exists.
    Otherwise, default to current working directory (detecting git root if available).
    """
    if project_arg:
        p = Path(project_arg).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Target project directory does not exist: {p}")
        if not p.is_dir():
            raise NotADirectoryError(f"Target project path is not a directory: {p}")
        return p

    # Default to cwd, preferring git repository root if in one
    cwd = Path.cwd().resolve()
    try:
        git_res = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if git_res.returncode == 0 and git_res.stdout.strip():
            return Path(git_res.stdout.strip()).resolve()
    except Exception:
        pass

    return cwd


def get_current_info(target_project=None):
    """Inspect local codex configuration, active model, auth mode, and target project status."""
    info = {
        "binary_path": CODEX_BIN,
        "binary_exists": os.path.exists(CODEX_BIN) if os.path.isabs(CODEX_BIN) else bool(shutil.which(CODEX_BIN)),
        "agy_binary_path": AGY_BIN,
        "agy_exists": os.path.exists(AGY_BIN) if os.path.isabs(AGY_BIN) else bool(shutil.which(AGY_BIN)),
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

    target = resolve_target_project(target_project)
    info["target_project"] = {
        "root": str(target),
        "agents_md_exists": (target / "AGENTS.md").exists(),
        "codex_loop_toml_exists": (target / ".codex-loop.toml").exists(),
        "is_git_repo": (target / ".git").exists(),
    }

    return info


AGENTS_TEMPLATE = """# Dual-Agent Workspace Constitution (Antigravity & Codex)

本项目采用 **Antigravity (Gemini)** 与 **OpenAI Codex CLI** 双智能体协同模式，两者共享本项目代码与设计上下文。

---

## 1. 核心分工与职责 (Roles & Responsibilities)

| 智能体 | 主要职责 | 执行范式 |
| :--- | :--- | :--- |
| **Antigravity (Gemini)** | 需求梳理、交互反馈、代码编写实施、多模态产物生成、测试执行、会话沉淀 | 终端执行、文件读写、交互式对话 |
| **OpenAI Codex CLI** | 复杂业务深度规划（Plan）、异构无头代码审查（Review）、架构红线检查 | `codex exec` / `codex review` (模型: `gpt-6.1-sol` 等) |

---

## 2. 行为红线与防灾规范 (Safety Guardrails)

所有智能体在本项目中均须严格遵守以下四项铁律：

1. **最小修改原则 (Minimal Blast Radius)**：
   - 严格只修改与目标直接相关的代码。
   - 严禁借“重构”名义未经用户批准擅自重写未受影响的现存功能、配置文件或基础类库。
2. **铁证验收原则 (Evidence-Based Completion)**：
   - 严禁凭主观臆测宣称“代码已写好/Bug已修复”。
   - 任何改动完成前，必须在终端实际运行对应的构建或测试脚本，且退出码（Exit Code）为 0 方可视为通过。
3. **关键任务异构审查 (Heterogeneous Red Teaming)**：
   - 涉及核心算法、架构改造、底层鉴权或跨模块调用的变更，必须调用 `codex review` 获得 `APPROVED` 判定。
4. **Git 物理防灾与版本整洁**：
   - 进行可能具有破坏性的复杂修改前，必须确保 git 工作区 clean，或在独立 feature 分支中进行。
   - 遇到逻辑混乱或失控时，优先使用 `git restore .` 瞬间回滚，严禁在错误代码上持续“盲打补丁”。
"""

CODEX_LOOP_TOML_TEMPLATE = """# codex-loop Dual-Agent Collaboration Configuration
[project]
name = "{name}"
version = "1.0.0"

[collaboration]
mode = "lightweight"
headless_agy = true
max_fix_rounds = 3
review_on_critical_changes = true

[testing]
# 规定验收命令（根据项目技术栈配置，例如: "npm test", "pytest", "cargo test"）
test_command = ""
"""


def init_target_project(target_project=None, dry_run=False):
    """
    Initialize target project with lightweight codex-loop collaboration files:
    1. AGENTS.md (idempotent append or create)
    2. .codex-loop.toml
    """
    target = resolve_target_project(target_project)
    print(f"[*] 正在初始化目标工程: {target}", file=sys.stderr)

    changes = []
    agents_md = target / "AGENTS.md"
    if not agents_md.exists():
        changes.append(("create", agents_md, AGENTS_TEMPLATE))
    else:
        existing_text = agents_md.read_text(encoding="utf-8")
        if "Dual-Agent Workspace Constitution (Antigravity & Codex)" not in existing_text:
            new_text = existing_text.rstrip() + "\n\n" + AGENTS_TEMPLATE
            changes.append(("append", agents_md, new_text))
        else:
            print("  - [已存在] AGENTS.md 已包含双智能体协同规范，跳过增补。", file=sys.stderr)

    config_file = target / ".codex-loop.toml"
    if not config_file.exists():
        content = CODEX_LOOP_TOML_TEMPLATE.format(name=target.name)
        changes.append(("create", config_file, content))
    else:
        print("  - [已存在] .codex-loop.toml 已存在，跳过创建。", file=sys.stderr)

    if dry_run:
        print("[*] Dry-run 模式：以下文件将被创建或修改：", file=sys.stderr)
        for action, path, _ in changes:
            print(f"  - [{action.upper()}] {path}", file=sys.stderr)
        return True

    for action, path, content in changes:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"  - [{action.upper()}] 已写入: {path.name}", file=sys.stderr)

    print(f"[*] 目标工程初始化完成！", file=sys.stderr)
    return True


def run_plan(prompt, model=None, reasoning_effort="xhigh", target_file=None, target_project=None):
    """Run Codex in non-interactive exec mode within target_project to generate an implementation blueprint."""
    target = resolve_target_project(target_project)
    current_info = get_current_info(target_project=target)
    effective_model = model or current_info.get("active_model", "gpt-6.1-sol")

    cmd = [CODEX_BIN, "exec", "--skip-git-repo-check", "--ephemeral", "--sandbox", "read-only"]
    if effective_model:
        cmd.extend(["-c", f'model="{effective_model}"'])
    if reasoning_effort:
        cmd.extend(["-c", f'model_reasoning_effort="{reasoning_effort}"'])

    full_prompt = (
        f"你现在作为首席架构师，负责为当前项目制定实施计划与开发规则。\n"
        f"当前工程目录：{target}\n"
        f"用户需求：\n{prompt}\n\n"
        f"请输出规范清晰的技术设计、步骤分解（Checklist）和质量约束。\n"
        f"要求：输出结构清晰的 Markdown。"
    )
    cmd.append(full_prompt)

    print(f"[*] 启动 Codex 规划中 (Project: {target}, Model: {effective_model}, Reasoning: {reasoning_effort})...", file=sys.stderr)
    res = subprocess.run(
        cmd,
        cwd=str(target),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        encoding="utf-8",
        errors="replace"
    )

    if res.returncode != 0:
        err_msg = res.stderr or ""
        print(f"[!] Codex 规划执行失败 (code {res.returncode}):\n{err_msg}", file=sys.stderr)
        return False, err_msg

    output = (res.stdout or "").strip()
    if target_file:
        p = Path(target_file)
        if not p.is_absolute():
            p = target / p
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(output, encoding="utf-8")
        print(f"[*] 规划已写入文件: {p}", file=sys.stderr)

    print(output)
    return True, output


def run_review(instructions=None, model=None, base=None, target_project=None):
    """Run Codex code review against uncommitted changes in target_project."""
    target = resolve_target_project(target_project)
    current_info = get_current_info(target_project=target)
    effective_model = model or current_info.get("active_model", "gpt-6.1-sol")

    cmd = [CODEX_BIN, "review", "--uncommitted"]
    if effective_model:
        cmd.extend(["-c", f'model="{effective_model}"'])
    if base:
        cmd.extend(["--base", base])
    if instructions:
        cmd.append(instructions)

    print(f"[*] 启动 Codex 代码审查中 (Project: {target}, Model: {effective_model})...", file=sys.stderr)
    res = subprocess.run(
        cmd,
        cwd=str(target),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        encoding="utf-8",
        errors="replace"
    )

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


def run_agy(task_file="docs/task.md", prompt=None, target_project=None):
    """Invoke Antigravity CLI in headless mode to implement changes inside target_project."""
    target = resolve_target_project(target_project)
    p = Path(task_file)
    if not p.is_absolute():
        p = target / p

    instruction = prompt or f"阅读 AGENTS.md 与 {p}，按计划实现代码，仅修改相关文件，并执行规定的验收测试命令；不要再次调用 Codex，不提交代码。"
    cmd = [AGY_BIN, "-p", instruction, "--mode=accept-edits"]
    print(f"[*] 启动 Antigravity CLI (agy) 无头实施中 (Project: {target}, Task: {p})...", file=sys.stderr)
    res = subprocess.run(cmd, cwd=str(target), stdin=subprocess.DEVNULL)
    return res.returncode == 0


def build_parser():
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "--project", "-P",
        default=argparse.SUPPRESS,
        help="Target project root directory (default: current workspace / git root)"
    )

    parser = argparse.ArgumentParser(
        description="Codex Automation Loop Runner",
        parents=[parent_parser]
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: info
    subparsers.add_parser(
        "info",
        parents=[parent_parser],
        help="Show active Codex configuration and target project status"
    )

    # Subcommand: init
    p_init = subparsers.add_parser(
        "init",
        parents=[parent_parser],
        help="Initialize target project with AGENTS.md and .codex-loop.toml"
    )
    p_init.add_argument("--dry-run", action="store_true", help="Preview files to be created without writing")

    # Subcommand: plan
    p_plan = subparsers.add_parser(
        "plan",
        parents=[parent_parser],
        help="Generate task plan via codex exec"
    )
    p_plan.add_argument("prompt", help="Task requirement description")
    p_plan.add_argument("--model", "-m", help="Specific model (default: config or gpt-6.1-sol)")
    p_plan.add_argument("--reasoning", "-r", default="xhigh", help="Reasoning effort (low/medium/high/xhigh)")
    p_plan.add_argument("--out", "-o", help="Target output file (e.g. docs/task.md)")

    # Subcommand: exec-agy
    p_agy = subparsers.add_parser(
        "exec-agy",
        parents=[parent_parser],
        help="Run Antigravity CLI (agy) to implement task"
    )
    p_agy.add_argument("--task", "-t", default="docs/task.md", help="Task specification file (default: docs/task.md)")
    p_agy.add_argument("--prompt", "-p", help="Custom prompt for agy")

    # Subcommand: review
    p_review = subparsers.add_parser(
        "review",
        parents=[parent_parser],
        help="Review current uncommitted diff in target project"
    )
    p_review.add_argument("--instructions", "-i", help="Custom review instructions")
    p_review.add_argument("--model", "-m", help="Specific review model")
    p_review.add_argument("--base", "-b", help="Base branch")

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    # Resolve target project from args.project
    target_project = getattr(args, "project", None)

    if args.command == "info":
        print(json.dumps(get_current_info(target_project=target_project), indent=2, ensure_ascii=False))
    elif args.command == "init":
        success = init_target_project(target_project=target_project, dry_run=args.dry_run)
        sys.exit(0 if success else 1)
    elif args.command == "plan":
        success, _ = run_plan(
            args.prompt,
            model=args.model,
            reasoning_effort=args.reasoning,
            target_file=args.out,
            target_project=target_project
        )
        sys.exit(0 if success else 1)
    elif args.command == "exec-agy":
        success = run_agy(task_file=args.task, prompt=args.prompt, target_project=target_project)
        sys.exit(0 if success else 1)
    elif args.command == "review":
        approved, _ = run_review(
            instructions=args.instructions,
            model=args.model,
            base=args.base,
            target_project=target_project
        )
        sys.exit(0 if approved else 2)


if __name__ == "__main__":
    main()
