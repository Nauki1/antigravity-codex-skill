#!/usr/bin/env python3
"""
Codex Automation Loop Script (Dual-Agent Collaboration Engine)
Project: codex-loop
Supports: Google Antigravity (Gemini) <-> OpenAI Codex CLI (gpt-6.1-sol / o3)
Target Project Parameterization: Enables using codex-loop from global skill across any project workspace.
"""

import argparse
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
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
   - 开工前在任务文档写清目标、可验证的验收标准、支持范围、不做事项和验收命令。实施与审查沿用同一标准；扩大范围需用户授权。
   - 严格只修改与目标直接相关的代码。
   - 严禁借“重构”名义未经用户批准擅自重写未受影响的现存功能、配置文件或基础类库。
2. **铁证验收原则 (Evidence-Based Completion)**：
   - 严禁凭主观臆测宣称“代码已写好/Bug已修复”。
   - 任何改动完成前，必须在终端实际运行对应的构建或测试脚本，且退出码（Exit Code）为 0 方可视为通过。
3. **关键任务异构审查 (Heterogeneous Red Teaming)**：
   - 必须修复的问题须给出稳定 ID、位置、支持范围内的触发条件、预期与实际行为、影响，以及复现或确定的可达代码证据。未经核验的猜测保持待验证，不直接派给实施方修改。
   - 实施方可针对问题 ID 提交修复或反驳证据；审查方须独立核验并逐项裁定。证据无法解决争议时交由用户决定，不自动批准或继续返工。
   - 涉及核心算法、架构改造、底层鉴权或跨模块调用的变更，必须调用 `codex review` 获得 `APPROVED` 判定。
   - 审查报告先给出发现和理由，最后一行只写 `APPROVED`（无待修复问题）或 `NEEDS_FIX`（存在待修复问题）。
   - 结论只出现一次，不放入引用、代码块或示例；未完成审查时不得输出批准。
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
        "要求：输出结构清晰的 Markdown，明确列出目标、可验证的验收标准、支持范围、"
        "不做事项和验收命令。区分用户要求与待确认假设；未经用户确认的假设不能成为"
        "额外的验收门槛。实施和审查沿用这份标准，扩大范围需用户授权。"
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


REVIEW_PROTOCOL = (
    "Keep your native review JSON schema and all actionable findings. "
    "The CLI renders overall_explanation but hides the other native fields. "
    "Therefore overall_explanation MUST be a string containing exactly one JSON "
    "object with these fields: protocol (\"codex-loop-review-v2\"), review_complete "
    "(boolean), findings_count (integer equal to the native findings list length), "
    "overall_correctness (same as the native overall_correctness: \"patch is correct\" "
    "or \"patch is incorrect\"), reason (nonempty explanation string), findings "
    "(one evidence record per native finding, with the same count). Every record "
    "must contain nonempty strings id, title, location, trigger, expected, actual, "
    "impact, evidence, plus verified=true. Use unique stable IDs such as F1. "
    "Copy each native title exactly; location must match its rendered absolute "
    "path and line range (file:start-end, or file:start for a single line). "
    "Describe a concrete supported triggering condition, the expected and actual "
    "behavior, material impact, and reproduction or a definite reachable code path. "
    "Do not classify speculation or preferences as verified defects. If a "
    "potential material defect cannot be established, report an incomplete review "
    "with the remaining uncertainty rather than assigning unverified repair work. "
    "Also include adjudications (an array, empty without implementer responses or "
    "prior unresolved disputes). Carry forward every prior needs_human ID and "
    "adjudicate it explicitly; never silently drop an unresolved dispute. "
    "For each supplied response, independently check its evidence against code "
    "and tests. Return exactly one decision with finding_id, decision "
    "(closed, confirmed, or needs_human), reason, and evidence, all nonempty "
    "strings. Closed IDs must not remain findings; confirmed IDs must remain. "
    "Do not accept a rebuttal merely because the implementer asserts it. "
    "If evidence cannot resolve the dispute, use needs_human; do not assign more "
    "repairs or claim approval. Retain supplied finding IDs. "
    "Do not wrap this object in Markdown or add text outside it. If review could "
    "not be completed, set review_complete to false. The wrapper preserves this "
    "report and emits APPROVED only for a complete, correct review with zero findings; "
    "otherwise it emits NEEDS_FIX or fails without approval."
)

REVIEW_CRITERIA = (
    "Judge the change against the user's acceptance criteria and supported scope. "
    "Do not turn naming preferences, optional refactoring, speculative future "
    "features, or inputs outside the supported scope into required work. "
    "Check relevant regressions, security, and data integrity even if the task "
    "did not list each existing guarantee. Do not silently expand or redefine "
    "the agreed acceptance criteria."
)


class ReviewError(RuntimeError):
    """Review execution or output was invalid; no approval may be issued."""

    def __init__(self, message, output=""):
        super().__init__(message)
        self.output = output


def unique_json_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate field: {key}")
        result[key] = value
    return result


def parse_review_report(output):
    """Validate the explicit envelope exported by the native review renderer."""
    try:
        report, end = json.JSONDecoder(object_pairs_hook=unique_json_fields).raw_decode(output.lstrip())
    except (ValueError, TypeError) as exc:
        raise ReviewError("审查协议 JSON 不完整或包含重复字段，未取得批准。", output) from exc
    required = {"protocol", "review_complete", "findings_count", "overall_correctness", "reason", "findings"}
    if (
        not isinstance(report, dict) or not required <= set(report) or set(report) - required - {"adjudications"}
        or report["protocol"] != "codex-loop-review-v2"
        or report["review_complete"] is not True
        or type(report["findings_count"]) is not int or report["findings_count"] < 0
        or report["overall_correctness"] not in ("patch is correct", "patch is incorrect")
        or not isinstance(report["reason"], str) or not report["reason"].strip()
    ):
        raise ReviewError("审查协议缺少有效的完整结论，未取得批准。", output)
    if not isinstance(report["findings"], list) or len(report["findings"]) != report["findings_count"]:
        raise ReviewError("审查发现数量与证据记录不一致，未取得批准。", output)
    finding_fields = {"id", "title", "location", "trigger", "expected", "actual", "impact", "evidence", "verified"}
    ids = set()
    for finding in report["findings"]:
        if (
            not isinstance(finding, dict) or set(finding) != finding_fields
            or finding["verified"] is not True
            or any(not isinstance(finding[key], str) or not finding[key].strip() for key in finding_fields - {"verified"})
            or finding["id"] in ids
        ):
            raise ReviewError("审查发现缺少可核验的完整证据或 ID 重复，保持待审查。", output)
        ids.add(finding["id"])
    decisions = report.get("adjudications", [])
    if not isinstance(decisions, list):
        raise ReviewError("争议裁定格式无效，保持待审查。", output)
    decided = set()
    for decision in decisions:
        if (
            not isinstance(decision, dict) or set(decision) != {"finding_id", "decision", "reason", "evidence"}
            or any(not isinstance(value, str) or not value.strip() for value in decision.values())
            or decision["decision"] not in ("closed", "confirmed", "needs_human")
            or decision["finding_id"] in decided
            or (decision["decision"] == "closed" and decision["finding_id"] in ids)
            or (decision["decision"] == "confirmed" and decision["finding_id"] not in ids)
        ):
            raise ReviewError("争议裁定缺少证据、重复或与当前发现矛盾，保持待审查。", output)
        decided.add(decision["finding_id"])
    # The renderer appends native findings after overall_explanation. Such text
    # must never be ignored when a zero-findings approval is claimed.
    trailer = output.lstrip()[end:].strip()
    if trailer and report["findings_count"] == 0:
        raise ReviewError("零发现结论后仍有额外内容，未取得批准。", output)
    if report["findings"]:
        lines = trailer.splitlines()
        if not lines or lines[0] not in ("Review comment:", "Full review comments:"):
            raise ReviewError("缺少对应的原生问题列表，保持待审查。", output)
        rows = []
        def normalize_row(row):
            row = row.replace("\\", "/")
            prefix, colon, span = row.rpartition(":")
            start, dash, finish = span.partition("-")
            if colon and start.isascii() and start.isdigit() and (not dash or (finish.isascii() and finish.isdigit() and int(start) == int(finish))):
                return f"{prefix}:{int(start)}"
            return row
        for line in lines[1:]:
            if line.startswith("- "):
                rows.append(normalize_row(line))
            elif line.strip() and not line.startswith("  "):
                raise ReviewError("原生问题列表含有未知或矛盾内容，保持待审查。", output)
        expected_rows = [normalize_row(f"- {finding['title']} — {finding['location']}") for finding in report["findings"]]
        if sorted(rows) != sorted(expected_rows):
            raise ReviewError("原生问题与证据记录不对应，保持待审查。", output)
    if not report["findings"] and report["overall_correctness"] == "patch is incorrect" and not any(item["decision"] == "needs_human" for item in decisions):
        raise ReviewError("整体结论错误但没有具体缺陷证据，保持待审查。", output)
    return report


def parse_review_verdict(output):
    report = parse_review_report(output)
    if any(item["decision"] == "needs_human" for item in report.get("adjudications", [])):
        raise ReviewError("争议证据尚未达成结论，需用户决定；不批准或自动返工。", output)
    if report["findings_count"] or report["overall_correctness"] == "patch is incorrect":
        return "NEEDS_FIX"
    return "APPROVED"


def load_review_task(target, task_file=None):
    """Read a target-project task snapshot; an explicit missing task is an error."""
    path = Path(task_file) if task_file is not None else Path("docs/task.md")
    if not path.is_absolute():
        path = target / path
    if task_file is None and not path.exists():
        return None
    try:
        content = path.read_bytes()
        text = content.decode("utf-8-sig")
    except (OSError, UnicodeError) as exc:
        raise ReviewError(f"无法读取任务验收标准 {path}: {exc}") from exc
    if not text.strip():
        raise ReviewError(f"任务验收标准为空: {path}")
    return path, hashlib.sha256(content).hexdigest(), text


def load_review_discussion(target, previous_review=None, response_file=None):
    if response_file is not None and previous_review is None:
        raise ReviewError("实施方回应必须与 --previous-review 一起提供。")
    previous = load_review_task(target, previous_review) if previous_review is not None else None
    response = load_review_task(target, response_file) if response_file is not None else None
    prior = parse_review_report(previous[2]) if previous else None
    replies = []
    if response:
        try:
            data = json.loads(response[2], object_pairs_hook=unique_json_fields)
        except (ValueError, TypeError) as exc:
            raise ReviewError("实施方回应不是完整的 JSON。") from exc
        if not isinstance(data, dict) or set(data) != {"responses"} or not isinstance(data["responses"], list) or not data["responses"]:
            raise ReviewError("实施方回应必须包含非空 responses 列表。")
        known = {item["id"] for item in prior["findings"]} | {item["finding_id"] for item in prior.get("adjudications", [])}
        ids = set()
        for reply in data["responses"]:
            if (
                not isinstance(reply, dict) or set(reply) != {"finding_id", "position", "reason", "evidence"}
                or any(not isinstance(value, str) or not value.strip() for value in reply.values())
                or reply["position"] not in ("fixed", "disputed")
                or reply["finding_id"] not in known or reply["finding_id"] in ids
            ):
                raise ReviewError("实施方回应缺少证据、ID 未知或重复。")
            ids.add(reply["finding_id"])
        replies = data["responses"]
    return previous, response, prior, replies


def run_review(instructions=None, model=None, base=None, target_project=None, task_file=None, previous_review=None, response_file=None, output_file=None):
    """Review one scope; return (approved, raw output), or raise ReviewError."""
    if base is not None and instructions is not None:
        raise ReviewError("--base 与 --instructions 不能同时使用。")
    if base is not None and not base.strip():
        raise ReviewError("--base 不能为空。")
    if instructions is not None and not instructions.strip():
        raise ReviewError("--instructions 不能为空。")
    target = resolve_target_project(target_project)
    task = load_review_task(target, task_file)
    previous, response, prior, replies = load_review_discussion(target, previous_review, response_file)
    saved_path = (target / output_file).resolve() if output_file is not None else None
    criteria_path = (target / (task_file if task_file is not None else "docs/task.md")).resolve()
    if saved_path and (saved_path == criteria_path or any(saved_path == snapshot[0].resolve() for snapshot in (previous, response) if snapshot)):
        raise ReviewError("审查输出不能覆盖任务、上轮报告或实施方回应。")
    current_info = get_current_info(target_project=target)
    effective_model = model or current_info.get("active_model", "gpt-6.1-sol")

    # Use the native custom review target to attach the protocol without mixing
    # a PROMPT with the mutually exclusive --base/--uncommitted targets.
    cmd = [CODEX_BIN, "exec", "review", "--ephemeral"]
    if effective_model:
        cmd.extend(["-c", f'model="{effective_model}"'])
    if base is not None:
        try:
            merge_base = subprocess.run(
                ["git", "merge-base", "--", "HEAD", base], cwd=str(target),
                stdin=subprocess.DEVNULL, capture_output=True, encoding="utf-8", errors="replace",
            )
        except OSError as exc:
            raise ReviewError(f"无法解析审查基线: {exc}") from exc
        revision = (merge_base.stdout or "").strip()
        if merge_base.returncode != 0 or len(revision) not in (40, 64) or any(c not in "0123456789abcdef" for c in revision):
            raise ReviewError(f"无法解析审查基线 {base!r}: {merge_base.stderr or ''}")
        scope = (
            f"Review the tracked changes against the merge base {revision} of HEAD "
            f"and base branch {json.dumps(base)}. Inspect git diff {revision}, including "
            "staged and unstaged changes. Do not review unrelated untracked files."
        )
    else:
        scope = "Review all staged, unstaged, and untracked changes in the current project."
    task_context = (
        f"Agreed task snapshot ({task[0]}, SHA-256 {task[1]}):\n{task[2]}"
        if task else "No task document supplied. Use explicit user instructions and existing project guarantees; do not invent requirements."
    )
    discussion = f"Previous validated review:\n{json.dumps(prior, ensure_ascii=False)}\nImplementer responses:\n{json.dumps(replies, ensure_ascii=False)}" if prior else "No previous review or implementer responses supplied."
    prompt = f"{scope}\n{REVIEW_CRITERIA}\n{task_context}\n{discussion}\nAdditional review instructions:\n{instructions or ''}\n\n{REVIEW_PROTOCOL}"
    cmd.extend(["--", "-"])

    print(f"[*] 启动 Codex 代码审查中 (Project: {target}, Model: {effective_model})...", file=sys.stderr)
    try:
        with tempfile.TemporaryDirectory(prefix="codex_review_") as review_dir:
            report_path = Path(review_dir) / "result.txt"
            # Place options before the custom prompt's -- delimiter.
            cmd[4:4] = ["--output-last-message", str(report_path)]
            res = subprocess.run(
                cmd,
                cwd=str(target),
                input=prompt,
                capture_output=True,
                encoding="utf-8",
                errors="replace"
            )
            if res.returncode != 0:
                print(res.stdout or "")
                raise ReviewError(f"Codex 审查执行失败 (code {res.returncode}):\n{res.stderr or ''}", res.stdout or "")
            with report_path.open(encoding="utf-8", newline="") as report_file:
                output = report_file.read()
    except (OSError, UnicodeError) as exc:
        raise ReviewError(f"Codex 审查调用或结果读取失败: {exc}") from exc

    print(output, end="" if output.endswith("\n") else "\n")

    try:
        latest_task = load_review_task(target, task_file)
    except ReviewError as exc:
        raise ReviewError(f"审查后任务验收标准无法读取: {exc}", output) from exc
    if (latest_task[1] if latest_task else None) != (task[1] if task else None):
        raise ReviewError("审查期间任务验收标准发生变化，需重新审查。", output)

    for snapshot in (previous, response):
        if snapshot:
            try:
                current = load_review_task(target, str(snapshot[0]))
            except ReviewError as exc:
                raise ReviewError(f"审查后讨论证据无法读取: {exc}", output) from exc
            if current[1] != snapshot[1]:
                raise ReviewError("审查期间上轮报告或实施方回应发生变化，需重新审查。", output)
    report = parse_review_report(output)
    reply_ids = {item["finding_id"] for item in replies}
    reply_ids |= {item["finding_id"] for item in (prior or {}).get("adjudications", []) if item["decision"] == "needs_human"}
    decision_ids = {item["finding_id"] for item in report.get("adjudications", [])}
    if decision_ids != reply_ids:
        raise ReviewError("实施方回应未逐项裁定，或存在未经请求的裁定。", output)
    if saved_path:
        saved_path.parent.mkdir(parents=True, exist_ok=True)
        saved_path.write_text(output, encoding="utf-8")

    verdict = parse_review_verdict(output)
    is_approved = verdict == "APPROVED"
    # Preserve the exported report, then emit the explicit project verdict.
    print(verdict)
    print(f"\n[*] {'审查已通过' if is_approved else '审查需要修复'}", file=sys.stderr)
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
    review_scope = p_review.add_mutually_exclusive_group()
    review_scope.add_argument("--instructions", "-i", help="Custom review instructions for uncommitted changes (conflicts with --base)")
    p_review.add_argument("--model", "-m", help="Specific review model")
    p_review.add_argument("--task", "-t", help="Acceptance criteria file (default: target docs/task.md if present)")
    p_review.add_argument("--previous-review", help="Previous raw review report")
    p_review.add_argument("--response", help="Evidence-backed implementer response JSON")
    p_review.add_argument("--out", "-o", help="Save the raw report without the wrapper verdict")
    review_scope.add_argument("--base", "-b", help="Base branch (conflicts with --instructions)")

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
        try:
            approved, _ = run_review(
                instructions=args.instructions,
                model=args.model,
                base=args.base,
                target_project=target_project,
                task_file=args.task,
                previous_review=args.previous_review,
                response_file=args.response,
                output_file=args.out,
            )
        except (ReviewError, OSError) as exc:
            print(f"[!] {exc}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0 if approved else 2)


if __name__ == "__main__":
    main()
