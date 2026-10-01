#!/usr/bin/env python3
"""
Codex Automation Loop Script (Dual-Agent Collaboration Engine)
Project: codex-loop
Supports: Google Antigravity (Gemini) <-> OpenAI Codex CLI (gpt-6.1-sol / o3)
Target Project Parameterization: Enables using codex-loop from global skill across any project workspace.
"""

import argparse
import contextlib
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
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
   - 复审聚焦上轮问题、修复及相关回归，延续全部旧 ID 和关闭记录；已关闭问题只有经核验的新证据才可明确重开，不能换 ID 重复派发。
   - 验收达标、无已核验实质缺陷和待决疑点/争议时允许带建议项批准。自动修复遵守持久化轮次上限；到上限交由用户决定，不自动批准、重置或绕过，实施执行成功仍须复测与审查。
   - 涉及核心算法、架构改造、底层鉴权或跨模块调用的变更，必须调用 `codex review` 获得 `APPROVED` 或 `APPROVED_WITH_NOTES` 判定。
   - BLOCKER/CRITICAL（数学逻辑、数据完整性、验收测试非0、违反适用规则）才阻断；文风、额外理论推导与非核心命名归 SUGGESTION/MINOR。
   - 审查报告先给出发现和理由，最后一行只写 `APPROVED`、`APPROVED_WITH_NOTES`（只有建议，退出0）或 `NEEDS_FIX`（存在实质缺陷，退出2）。默认连续3次仍未获批时熔断，退出3并提供《待裁决争议报告》。
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
max_fix_rounds = 2
review_on_critical_changes = true

[testing]
# 规定验收命令（根据项目技术栈配置，例如: "npm test", "pytest", "cargo test"）
test_command = ""
"""

INIT_IGNORE_PATTERNS = (".review*", ".agents/sessions/*.tmp", ".codex/codex-loop/")

PHASE_CHECKPOINT_RULES = """
## 阶段里程碑脉冲卡片协议

<!-- codex-loop:phase-checkpoint-v1 -->
复杂任务依次执行四阶段：
`[Phase 1: 资产摸底与约束冻结] -> [Phase 2: 核心实施与测试] -> [Phase 3: 异构独立审查] -> [Phase 4: 交付归档与提交]`。
进入和结束阶段时给用户简短卡片：当前阶段、已完成事项、可核验证据、下一步与实际阻塞。未完成或没有证据的事项不能标为完成。
Phase 1 阅读规则与最新会话，冻结资产、支持范围和验收标准；Phase 2 按范围实施并真实运行验收；Phase 3 独立审查并逐项处理已核验问题；Phase 4 仅在批准后整理交付证据、归档并按用户授权提交。
审查比对和调用临时资产只在工程外的系统临时目录创建并在 finally 中清理；禁止手工创建根目录 .review* 或时间戳临时文件夹。
以下分级覆盖旧模板的结论格式：BLOCKER/CRITICAL 才阻断交付并返回 NEEDS_FIX；只有 SUGGESTION/MINOR 时输出建议及 APPROVED_WITH_NOTES；无问题则 APPROVED。报告结论只出现一次，放在末行。
同一任务默认连续最多3次未获批审查。达到上限后生成《待裁决争议报告》，停止并交用户决定；不得换路径、删状态或提高参数绕过。验收未完成、证据不足或争议未决时不宣称批准。
"""

AGENTS_TEMPLATE += "\n" + PHASE_CHECKPOINT_RULES


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
            if "<!-- codex-loop:phase-checkpoint-v1 -->" not in existing_text:
                changes.append(("append", agents_md, existing_text.rstrip() + "\n\n" + PHASE_CHECKPOINT_RULES))
            else:
                print("  - [已存在] AGENTS.md 已包含当前协同规范，跳过增补。", file=sys.stderr)

    config_file = target / ".codex-loop.toml"
    if not config_file.exists():
        content = CODEX_LOOP_TOML_TEMPLATE.format(name=target.name)
        changes.append(("create", config_file, content))
    else:
        print("  - [已存在] .codex-loop.toml 已存在，跳过创建。", file=sys.stderr)

    ignore_file = target / ".gitignore"
    existing_ignore = ignore_file.read_bytes().decode("utf-8") if ignore_file.exists() else ""
    missing = [pattern for pattern in INIT_IGNORE_PATTERNS if pattern not in existing_ignore.splitlines()]
    if missing:
        addition = ("" if not existing_ignore or existing_ignore.endswith("\n") else "\n") + "\n# codex-loop runtime and temporary assets\n" + "\n".join(missing) + "\n"
        changes.append(("append" if ignore_file.exists() else "create", ignore_file, existing_ignore + addition))

    if dry_run:
        print("[*] Dry-run 模式：以下文件将被创建或修改：", file=sys.stderr)
        for action, path, _ in changes:
            print(f"  - [{action.upper()}] {path}", file=sys.stderr)
        return True

    for action, path, content in changes:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8"))
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
    "object with these fields: protocol (\"codex-loop-review-v4\"), review_complete "
    "(boolean), findings_count (integer equal to the native findings list length), "
    "overall_correctness (same as the native overall_correctness: \"patch is correct\" "
    "or \"patch is incorrect\"), reason (nonempty explanation string), findings "
    "(one evidence record per native finding, with the same count), acceptance_met "
    "(boolean), advisories (array of objects with severity SUGGESTION or MINOR "
    "and a nonempty message string), "
    "and uncertainties (array of nonempty strings for unresolved material facts). "
    "Triage each finding with severity BLOCKER, CRITICAL, SUGGESTION, or MINOR. "
    "Mathematical logic errors, data alteration/corruption, nonzero required "
    "test exit codes and violations of applicable AGENTS.md invariants must be "
    "BLOCKER or CRITICAL. Wording polish, unrequested extra theory derivations "
    "and non-core naming are SUGGESTION or MINOR and never block delivery. "
    "Prefer advisories for optional suggestions; native findings may also carry "
    "nonblocking severity. Every finding evidence record "
    "must contain nonempty strings id, title, location, trigger, expected, actual, "
    "impact, evidence, severity, plus verified=true. Use unique stable IDs such as F1. "
    "Copy each native title exactly; location must match its rendered absolute "
    "path and line range (file:start-end, or file:start for a single line). "
    "Describe a concrete supported triggering condition, the expected and actual "
    "behavior, material impact, and reproduction or a definite reachable code path. "
    "Do not classify speculation or preferences as verified defects. If a "
    "potential material defect cannot be established, list it in uncertainties "
    "rather than assigning unverified repair work or claiming approval. "
    "Also include adjudications (an array, empty without implementer responses or "
    "prior review). Carry forward every prior finding and adjudication ID and "
    "adjudicate it explicitly, including closed and unresolved IDs. "
    "For each supplied response, independently check its evidence against code "
    "and tests. Return exactly one decision with finding_id, decision "
    "(closed, confirmed, reopened, or needs_human), reason, and evidence, all nonempty "
    "strings. Closed IDs must not remain findings; confirmed IDs must remain. "
    "Do not accept a rebuttal merely because the implementer asserts it. "
    "If evidence cannot resolve the dispute, use needs_human; do not assign more "
    "repairs or claim approval. Retain supplied finding IDs. Reopened IDs must "
    "have been closed in the prior review, must remain current findings, and "
    "must include an additional nonempty new_evidence field establishing a "
    "new fact since closure; repeating the closure evidence is insufficient. "
    "Include a history array copied exactly from the supplied claim identities; "
    "retain it after closure so a claim cannot return under a different ID. "
    "Do not wrap this object in Markdown or add text outside it. If review could "
    "not be completed, set review_complete to false. The wrapper preserves this "
    "report and emits APPROVED only for a complete, correct review with acceptance_met "
    "true, zero BLOCKER/CRITICAL findings and no unresolved uncertainties or disputes. "
    "With SUGGESTION/MINOR findings or advisories it emits APPROVED_WITH_NOTES "
    "and lists notes; optional polish alone never causes another repair iteration. "
    "otherwise it emits NEEDS_FIX or fails without approval."
)

REVIEW_CRITERIA = (
    "Judge the change against the user's acceptance criteria and supported scope. "
    "Do not turn naming preferences, optional refactoring, speculative future "
    "features, or inputs outside the supported scope into required work. "
    "Check relevant regressions, security, and data integrity even if the task "
    "did not list each existing guarantee. Do not silently expand or redefine "
    "the agreed acceptance criteria."
    " Perform read-only inspection. Never create .review* or timestamped "
    "comparison directories in the target project; use only the wrapper-provided "
    "system scratch directory if a temporary comparison asset is necessary. "
    "Do not edit codex-loop runtime state or invoke another reviewer."
)

REVIEW_FOLLOWUP = (
    "This is a focused follow-up review: adjudicate every previous finding and "
    "decision, check the repairs and relevant regressions they introduce. "
    "Keep closed issues closed unless new concrete evidence establishes a "
    "defect; do not relabel a closed or existing claim under a new ID. "
    "New material defects within the agreed scope may be reported with evidence. "
    "Do not restart a general preference or unrelated improvement review."
)


def review_history(prior):
    """Keep the original claim identity even after its finding is closed."""
    records = {}
    for item in (prior or {}).get("history", []) + (prior or {}).get("findings", []):
        identity = {key: item[key] for key in ("id", "title", "location", "trigger")}
        records[tuple(identity.values())] = identity
    return [records[key] for key in sorted(records)]


def normalize_review_location(row):
    row = row.replace("\\", "/")
    prefix, colon, span = row.rpartition(":")
    start, dash, finish = span.partition("-")
    if colon and start.isascii() and start.isdigit() and (not dash or (finish.isascii() and finish.isdigit() and int(start) == int(finish))):
        return f"{prefix}:{int(start)}"
    return row


class ReviewError(RuntimeError):
    """Review execution or output was invalid; no approval may be issued."""

    def __init__(self, message, output=""):
        super().__init__(message)
        self.output = output


class HumanDecisionRequired(ReviewError):
    """Automatic remediation must stop; exhaustion is never an approval."""


def atomic_json_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def unique_json_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate field: {key}")
        result[key] = value
    return result


def parse_review_report(output, require_current=False):
    """Validate the explicit envelope exported by the native review renderer."""
    try:
        report, end = json.JSONDecoder(object_pairs_hook=unique_json_fields).raw_decode(output.lstrip())
    except (ValueError, TypeError) as exc:
        raise ReviewError("审查协议 JSON 不完整或包含重复字段，未取得批准。", output) from exc
    required = {"protocol", "review_complete", "findings_count", "overall_correctness", "reason", "findings"}
    if isinstance(report, dict) and report.get("protocol") in ("codex-loop-review-v3", "codex-loop-review-v4"):
        required |= {"acceptance_met", "advisories", "uncertainties"}
    if (
        not isinstance(report, dict) or not required <= set(report) or set(report) - required - {"adjudications", "history"}
        or report["protocol"] not in ("codex-loop-review-v2", "codex-loop-review-v3", "codex-loop-review-v4")
        or (require_current and report["protocol"] != "codex-loop-review-v4")
        or report["review_complete"] is not True
        or type(report["findings_count"]) is not int or report["findings_count"] < 0
        or report["overall_correctness"] not in ("patch is correct", "patch is incorrect")
        or not isinstance(report["reason"], str) or not report["reason"].strip()
    ):
        raise ReviewError("审查协议缺少有效的完整结论，未取得批准。", output)
    if report["protocol"] in ("codex-loop-review-v3", "codex-loop-review-v4") and (
        type(report["acceptance_met"]) is not bool
        or not isinstance(report["advisories"], list)
        or not isinstance(report["uncertainties"], list)
        or any(not isinstance(item, str) or not item.strip() for item in report["uncertainties"])
    ):
        raise ReviewError("验收、建议或待验证记录无效，保持待审查。", output)
    for note in report.get("advisories", []):
        if report["protocol"] == "codex-loop-review-v4":
            if not isinstance(note, dict) or set(note) != {"severity", "message"} or note["severity"] not in ("SUGGESTION", "MINOR") or not isinstance(note["message"], str) or not note["message"].strip():
                raise ReviewError("建议项分级或内容无效，保持待审查。", output)
        elif not isinstance(note, str) or not note.strip():
            raise ReviewError("建议项内容无效，保持待审查。", output)
    if not isinstance(report["findings"], list) or len(report["findings"]) != report["findings_count"]:
        raise ReviewError("审查发现数量与证据记录不一致，未取得批准。", output)
    finding_fields = {"id", "title", "location", "trigger", "expected", "actual", "impact", "evidence", "verified"}
    if report["protocol"] == "codex-loop-review-v4":
        finding_fields.add("severity")
    ids = set()
    for finding in report["findings"]:
        if (
            not isinstance(finding, dict) or set(finding) != finding_fields
            or finding["verified"] is not True
            or any(not isinstance(finding[key], str) or not finding[key].strip() for key in finding_fields - {"verified"})
            or finding["id"] in ids
            or (report["protocol"] == "codex-loop-review-v4" and finding["severity"] not in ("BLOCKER", "CRITICAL", "SUGGESTION", "MINOR"))
        ):
            raise ReviewError("审查发现缺少可核验的完整证据或 ID 重复，保持待审查。", output)
        ids.add(finding["id"])
    decisions = report.get("adjudications", [])
    if not isinstance(decisions, list):
        raise ReviewError("争议裁定格式无效，保持待审查。", output)
    decided = set()
    for decision in decisions:
        decision_fields = {"finding_id", "decision", "reason", "evidence"}
        if isinstance(decision, dict) and decision.get("decision") == "reopened":
            decision_fields.add("new_evidence")
        if (
            not isinstance(decision, dict) or set(decision) != decision_fields
            or any(not isinstance(value, str) or not value.strip() for value in decision.values())
            or decision["decision"] not in ("closed", "confirmed", "reopened", "needs_human")
            or decision["finding_id"] in decided
            or (decision["decision"] == "closed" and decision["finding_id"] in ids)
            or (decision["decision"] in ("confirmed", "reopened") and decision["finding_id"] not in ids)
        ):
            raise ReviewError("争议裁定缺少证据、重复或与当前发现矛盾，保持待审查。", output)
        decided.add(decision["finding_id"])
    history = report.get("history", [])
    if not isinstance(history, list):
        raise ReviewError("问题历史格式无效，保持待审查。", output)
    history_records = set()
    for item in history:
        if (
            not isinstance(item, dict) or set(item) != {"id", "title", "location", "trigger"}
            or any(not isinstance(value, str) or not value.strip() for value in item.values())
            or tuple(item[key] for key in ("id", "title", "location", "trigger")) in history_records or item["id"] not in ids | decided
        ):
            raise ReviewError("问题历史缺少身份信息、重复或没有对应裁定，保持待审查。", output)
        history_records.add(tuple(item[key] for key in ("id", "title", "location", "trigger")))
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
        for line in lines[1:]:
            if line.startswith("- "):
                rows.append(normalize_review_location(line))
            elif line.strip() and not line.startswith("  "):
                raise ReviewError("原生问题列表含有未知或矛盾内容，保持待审查。", output)
        expected_rows = [normalize_review_location(f"- {finding['title']} — {finding['location']}") for finding in report["findings"]]
        if sorted(rows) != sorted(expected_rows):
            raise ReviewError("原生问题与证据记录不对应，保持待审查。", output)
    if not report["findings"] and report["overall_correctness"] == "patch is incorrect" and not report.get("uncertainties") and not any(item["decision"] == "needs_human" for item in decisions):
        raise ReviewError("整体结论错误但没有具体缺陷证据，保持待审查。", output)
    return report


def parse_review_verdict(output):
    report = parse_review_report(output)
    if any(item["decision"] == "needs_human" for item in report.get("adjudications", [])):
        raise ReviewError("争议证据尚未达成结论，需用户决定；不批准或自动返工。", output)
    if report.get("uncertainties"):
        raise ReviewError("存在未核验的实质疑点，保持待验证，不批准或自动返工。", output)
    if blocking_findings(report):
        return "NEEDS_FIX"
    if report.get("acceptance_met", True) is not True:
        raise ReviewError("验收未达标且没有已核验的具体修复问题，保持待决。", output)
    if report.get("advisories") or report["findings"]:
        return "APPROVED_WITH_NOTES"
    return "APPROVED"


def blocking_findings(report):
    return [item for item in report["findings"] if item.get("severity", "CRITICAL") in ("BLOCKER", "CRITICAL")]


def review_notes(report):
    return [note["message"] if isinstance(note, dict) else note for note in report.get("advisories", [])] + [f"[{item['severity']}] {item['title']}" for item in report["findings"] if item.get("severity") in ("SUGGESTION", "MINOR")]


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
    if prior:
        identities = {item["id"] for item in review_history(prior)}
        if any(item["finding_id"] not in identities for item in prior.get("adjudications", [])):
            raise ReviewError("上轮关闭或争议记录缺少原问题身份，请从保留原问题的报告重新复审。")
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


def review_output_paths(target, task_file, previous, response, output_file):
    saved_path = (target / output_file).resolve() if output_file is not None else None
    context_path = Path(str(saved_path) + ".context.json") if saved_path else None
    criteria_path = (target / (task_file if task_file is not None else "docs/task.md")).resolve()
    runtime_root = (target / ".codex/codex-loop").resolve()
    if saved_path and any(
        path.resolve() == criteria_path or path.resolve().is_relative_to(runtime_root)
        or any(path.resolve() == snapshot[0].resolve() for snapshot in (previous, response) if snapshot)
        for path in (saved_path, context_path)
    ):
        raise ReviewError("审查输出不能覆盖任务、讨论输入或熔断状态。")
    return saved_path, context_path


def _run_review_once(instructions=None, model=None, base=None, target_project=None, task_file=None, previous_review=None, response_file=None, output_file=None):
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
    saved_path, context_path = review_output_paths(target, task_file, previous, response, output_file)
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
    history = review_history(prior)
    discussion = f"{REVIEW_FOLLOWUP}\nPrevious validated review:\n{json.dumps(prior, ensure_ascii=False)}\nImplementer responses:\n{json.dumps(replies, ensure_ascii=False)}" if prior else "No previous review or implementer responses supplied."
    discussion += f"\nReturn history exactly as these claim identities (unchanged even after closure):\n{json.dumps(history, ensure_ascii=False)}"
    prompt = f"{scope}\n{REVIEW_CRITERIA}\n{task_context}\n{discussion}\nAdditional review instructions:\n{instructions or ''}\n\n{REVIEW_PROTOCOL}"
    cmd.extend(["--", "-"])

    print(f"[*] 启动 Codex 代码审查中 (Project: {target}, Model: {effective_model})...", file=sys.stderr)
    system_temp = Path(tempfile.gettempdir()).resolve()
    if system_temp.is_relative_to(target.resolve()):
        raise ReviewError("系统临时目录落在目标工程内，请调整 TMP/TEMP；不在工程中创建审查资产。")
    review_assets = tempfile.TemporaryDirectory(prefix="codex_review_", dir=system_temp)
    try:
        try:
            report_path = Path(review_assets.name) / "result.txt"
            # Place options before the custom prompt's -- delimiter.
            cmd[4:4] = ["--output-last-message", str(report_path)]
            res = subprocess.run(
                cmd,
                cwd=str(target),
                input=prompt + f"\nSystem review scratch directory (cleaned after this call): {review_assets.name}\n",
                capture_output=True,
                encoding="utf-8",
                errors="replace"
            )
            if res.returncode != 0:
                print(res.stdout or "")
                raise ReviewError(f"Codex 审查执行失败 (code {res.returncode}):\n{res.stderr or ''}", res.stdout or "")
            with report_path.open(encoding="utf-8", newline="") as report_file:
                output = report_file.read()
        finally:
            review_assets.cleanup()
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
    report = parse_review_report(output, require_current=True)
    reply_ids = {item["finding_id"] for item in replies}
    reply_ids |= {item["finding_id"] for item in (prior or {}).get("adjudications", [])}
    reply_ids |= {item["id"] for item in (prior or {}).get("findings", [])}
    decision_ids = {item["finding_id"] for item in report.get("adjudications", [])}
    if decision_ids != reply_ids:
        raise ReviewError("上轮问题或实施方回应未逐项裁定，或存在未知裁定。", output)
    if sorted(report.get("history", []), key=lambda item: tuple(item[key] for key in ("id", "title", "location", "trigger"))) != history:
        raise ReviewError("原问题身份历史被遗漏或修改，保持待审查。", output)
    old_decisions = {item["finding_id"]: item for item in (prior or {}).get("adjudications", [])}
    for decision in report.get("adjudications", []):
        old = old_decisions.get(decision["finding_id"])
        was_closed = old is not None and old["decision"] == "closed"
        if was_closed and decision["decision"] not in ("closed", "reopened"):
            raise ReviewError("已关闭问题只能凭新证据明确重开，保持待审查。", output)
        if decision["decision"] == "reopened" and (
            not was_closed or " ".join(decision["new_evidence"].split()).casefold() == " ".join(old["evidence"].split()).casefold()
        ):
            raise ReviewError("重开问题缺少不同于关闭依据的新证据，保持待审查。", output)
    for finding in report["findings"]:
        if any(
            finding["id"] != old["id"] and all(finding[key] == old[key] for key in ("title", "trigger"))
            and normalize_review_location(finding["location"]) == normalize_review_location(old["location"])
            for old in history + (prior or {}).get("findings", [])
        ):
            raise ReviewError("同一上轮问题被更换 ID，保持待审查。", output)
    if saved_path:
        saved_path.parent.mkdir(parents=True, exist_ok=True)
        saved_path.write_bytes(output.encode("utf-8"))
        atomic_json_write(context_path, {
            "version": 1, "review_id": str(uuid.uuid4()), "target": os.path.normcase(str(target.resolve())),
            "task_path": os.path.normcase(str(task[0].resolve())) if task else None,
            "task_sha256": task[1] if task else None,
            "report_sha256": hashlib.sha256(saved_path.read_bytes()).hexdigest(),
        })

    verdict = parse_review_verdict(output)
    is_approved = verdict in ("APPROVED", "APPROVED_WITH_NOTES")
    # Preserve the exported report, then emit the explicit project verdict.
    notes = review_notes(report)
    if notes:
        print("建议清单（不要求返工）：")
        for note in notes:
            print(f"- {note}")
    print(verdict)
    print(f"\n[*] {'审查已通过' if is_approved else '审查需要修复'}", file=sys.stderr)
    return is_approved, output


def review_cycle_path(target, task_file=None):
    path = (target / (task_file if task_file is not None else "docs/task.md")).resolve()
    key = hashlib.sha256(os.path.normcase(str(path)).encode("utf-8")).hexdigest()
    return target / ".codex/codex-loop" / f"review-{key}.json", path


def read_review_cycle(path):
    if not path.exists():
        return None
    try:
        state = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_json_fields)
    except (OSError, ValueError) as exc:
        raise ReviewError("审查熔断状态不可读，不自动清空或重新开始。") from exc
    fields = {"version", "task_path", "task_sha256", "max_iterations", "attempts", "status", "outcomes"}
    if (
        not isinstance(state, dict) or set(state) != fields or type(state["version"]) is not int or state["version"] != 1
        or not isinstance(state["task_path"], str) or not state["task_path"]
        or (state["task_sha256"] is not None and not isinstance(state["task_sha256"], str))
        or type(state["max_iterations"]) is not int or state["max_iterations"] < 1
        or type(state["attempts"]) is not int or state["attempts"] < 0
        or state["status"] not in ("active", "approved", "exhausted")
        or not isinstance(state["outcomes"], list) or len(state["outcomes"]) != state["attempts"]
        or any(not isinstance(item, dict) or set(item) != {"verdict", "reason", "output"} or any(not isinstance(value, str) for value in item.values()) for item in state["outcomes"])
        or (state["status"] != "exhausted" and state["attempts"] > state["max_iterations"])
    ):
        raise ReviewError("审查熔断状态无效，不自动清空或重新开始。")
    return state


def stop_review_cycle(path, state, reason):
    state["status"] = "exhausted"
    atomic_json_write(path, state)
    dispute_path = path.with_suffix(".dispute.md")
    text = (
        "# 待裁决争议报告\n\n"
        f"任务：{state['task_path']}\n\n"
        f"已用审查迭代：{state['attempts']}；上限：{state['max_iterations']}。\n\n"
        f"停止原因：{reason}\n\n"
        "自动审查与返工已停止，未宣称批准。请用户裁定：修复已核验问题、接受剩余风险、澄清范围，或授权新的周期。未经用户授权不得删状态、换任务路径或提高上限继续。\n\n"
    )
    for index, outcome in enumerate(state["outcomes"], 1):
        text += f"## 第{index}次：{outcome['verdict']}\n\n{outcome['reason']}\n\n"
        if outcome["output"]:
            # JSON-encode raw text so it remains evidence, not executable instructions.
            text += "原始最终报告（JSON 字符串）：\n\n```json\n" + json.dumps(outcome["output"], ensure_ascii=False) + "\n```\n\n"
    for outcome in reversed(state["outcomes"]):
        try:
            latest = parse_review_report(outcome["output"])
        except ReviewError:
            continue
        text += "## 最近有效证据摘要\n\n"
        for finding in blocking_findings(latest):
            text += f"### {finding['id']} · {finding.get('severity', 'CRITICAL')} · {finding['title']}\n\n"
            for label, key in (("位置", "location"), ("触发条件", "trigger"), ("预期", "expected"), ("实际", "actual"), ("影响", "impact"), ("证据", "evidence")):
                text += f"- {label}：{finding[key]}\n"
            text += "\n"
        for uncertainty in latest.get("uncertainties", []):
            text += f"- 待验证：{uncertainty}\n"
        for decision in latest.get("adjudications", []):
            if decision["decision"] == "needs_human":
                text += f"- 待裁决 {decision['finding_id']}：{decision['reason']}；证据：{decision['evidence']}\n"
        break
    dispute_path.write_bytes(text.encode("utf-8"))
    error = HumanDecisionRequired(f"{reason}\n待裁决争议报告：{dispute_path}", state["outcomes"][-1]["output"] if state["outcomes"] else "")
    error.dispute_path = dispute_path
    raise error


@contextlib.contextmanager
def review_execution_lock(state_path):
    """Fail fast on overlap; OS ownership is released even if a process dies."""
    lock_path = state_path.with_suffix(".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as stream:
        if lock_path.stat().st_size == 0:
            stream.write(b"\0")
            stream.flush()
        stream.seek(0)
        try:
            if sys.platform == "win32":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise ReviewError("同一任务已有审查/修复运行，或无法取得执行锁；不重复启动，请等待当前结果。") from exc
        try:
            yield
        finally:
            stream.seek(0)
            if sys.platform == "win32":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def run_review(instructions=None, model=None, base=None, target_project=None, task_file=None, previous_review=None, response_file=None, output_file=None, max_iterations=3):
    if type(max_iterations) is not int or max_iterations < 1:
        raise ReviewError("--max-iterations 必须是正整数。")
    target = resolve_target_project(target_project)
    state_path, _ = review_cycle_path(target, task_file)
    with review_execution_lock(state_path):
        return _run_review_cycle(instructions, model, base, target, task_file, previous_review, response_file, output_file, max_iterations)


def _run_review_cycle(instructions=None, model=None, base=None, target_project=None, task_file=None, previous_review=None, response_file=None, output_file=None, max_iterations=3):
    """Bound consecutive unsuccessful reviews across invocations of the CLI."""
    if type(max_iterations) is not int or max_iterations < 1:
        raise ReviewError("--max-iterations 必须是正整数。")
    # Validate inputs before reserving an iteration or creating persistent state.
    if base is not None and instructions is not None:
        raise ReviewError("--base 与 --instructions 不能同时使用。")
    if (base is not None and not base.strip()) or (instructions is not None and not instructions.strip()):
        raise ReviewError("审查范围或重点不能为空。")
    target = resolve_target_project(target_project)
    task = load_review_task(target, task_file)
    previous, response, _, _ = load_review_discussion(target, previous_review, response_file)
    review_output_paths(target, task_file, previous, response, output_file)
    state_path, task_path = review_cycle_path(target, task_file)
    digest = task[1] if task else None
    state = read_review_cycle(state_path)
    if state and state["status"] == "exhausted":
        stop_review_cycle(state_path, state, "本任务审查已熔断，需要用户裁决后才能继续。")
    if state and state["status"] != "approved":
        if state["task_sha256"] != digest:
            stop_review_cycle(state_path, state, "未获批期间验收标准变化，需要用户裁决；不自动重置。")
        state["max_iterations"] = min(max_iterations, state["max_iterations"])
        if state["attempts"] >= state["max_iterations"]:
            stop_review_cycle(state_path, state, "连续审查已达到上限，停止自动执行。")
    else:
        state = {"version": 1, "task_path": str(task_path), "task_sha256": digest, "max_iterations": max_iterations, "attempts": 0, "status": "active", "outcomes": []}
    state["attempts"] += 1
    state["outcomes"].append({"verdict": "INTERRUPTED", "reason": "审查已启动但尚未取得完整结论。", "output": ""})
    atomic_json_write(state_path, state)
    try:
        approved, output = _run_review_once(instructions, model, base, target, task_file, previous_review, response_file, output_file)
    except BaseException as exc:
        reason = str(exc).splitlines()[0] if str(exc).splitlines() else type(exc).__name__
        error_output = getattr(exc, "output", "")
        state["outcomes"][-1] = {"verdict": "INTERRUPTED" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else "PENDING", "reason": reason, "output": error_output if isinstance(error_output, str) else ""}
        atomic_json_write(state_path, state)
        if state["attempts"] >= state["max_iterations"]:
            stop_review_cycle(state_path, state, "连续审查未取得有效批准，已达到上限。")
        raise
    state["outcomes"][-1] = {"verdict": parse_review_verdict(output), "reason": parse_review_report(output)["reason"], "output": output}
    state["status"] = "approved" if approved else "active"
    atomic_json_write(state_path, state)
    if not approved and state["attempts"] >= state["max_iterations"]:
        stop_review_cycle(state_path, state, "连续修改与审查仍未获批，已达到上限。")
    return approved, output


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


def run_fix(review_file, task_file="docs/task.md", target_project=None):
    target = resolve_target_project(target_project)
    state_path, _ = review_cycle_path(target, task_file)
    with review_execution_lock(state_path):
        return _run_fix_once(review_file, task_file, target)


def _run_fix_once(review_file, task_file="docs/task.md", target_project=None):
    """Dispatch one bounded repair attempt; execution success is not approval."""
    target = resolve_target_project(target_project)
    cycle_file, _ = review_cycle_path(target, task_file)
    cycle = read_review_cycle(cycle_file)
    if cycle and (cycle["status"] == "exhausted" or (cycle["status"] != "approved" and cycle["attempts"] >= cycle["max_iterations"])):
        stop_review_cycle(cycle_file, cycle, "本任务审查已熔断，停止自动修复并等待用户裁决。")
    task = load_review_task(target, task_file)
    saved = load_review_task(target, review_file)
    report = parse_review_report(saved[2], require_current=True)
    context_file = Path(str(saved[0]) + ".context.json")
    try:
        context = json.loads(context_file.read_text(encoding="utf-8"), object_pairs_hook=unique_json_fields)
    except (OSError, ValueError) as exc:
        raise ReviewError("修复需要 review --out 生成的原报告与上下文记录，请重新审查并保存。") from exc
    fields = {"version", "review_id", "target", "task_path", "task_sha256", "report_sha256"}
    if (
        not isinstance(context, dict) or set(context) != fields or type(context["version"]) is not int or context["version"] != 1
        or not isinstance(context["review_id"], str) or not context["review_id"].strip()
        or context["target"] != os.path.normcase(str(target.resolve()))
        or context["task_path"] != os.path.normcase(str(task[0].resolve())) or context["task_sha256"] != task[1]
        or context["report_sha256"] != saved[1]
    ):
        raise ReviewError("报告上下文与当前工程、验收标准或报告内容不一致，请重新审查。")
    if report.get("uncertainties") or any(item["decision"] == "needs_human" for item in report.get("adjudications", [])) or (not report["acceptance_met"] and not blocking_findings(report)):
        raise HumanDecisionRequired("报告存在待验证或待用户决定的问题，停止自动修复。")
    if parse_review_verdict(saved[2]) in ("APPROVED", "APPROVED_WITH_NOTES"):
        print("[*] 审查已通过，无需启动修复；建议项不产生返工。", file=sys.stderr)
        return True
    limit = 2
    config_file = target / ".codex-loop.toml"
    if config_file.exists():
        try:
            import tomllib
            config = tomllib.loads(config_file.read_text(encoding="utf-8-sig"))
            limit = config.get("collaboration", {}).get("max_fix_rounds", 2)
        except (ImportError, OSError, ValueError, AttributeError) as exc:
            raise ReviewError(f"无法读取修复预算配置（需要 Python 3.11+）: {exc}") from exc
    if type(limit) is not int or limit < 1:
        raise ReviewError("max_fix_rounds 必须是正整数。")
    task_key = hashlib.sha256(os.path.normcase(str(task[0].resolve())).encode("utf-8")).hexdigest()
    state_file = target / ".codex/codex-loop" / f"fix-{task_key}.json"
    state = {"version": 1, "task_sha256": task[1], "limit": limit, "attempts": 0, "used_reviews": []}
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"), object_pairs_hook=unique_json_fields)
        except (OSError, ValueError) as exc:
            raise ReviewError("修复计数记录不可读，不能自动重置。") from exc
        if (
            not isinstance(state, dict) or set(state) != {"version", "task_sha256", "limit", "attempts", "used_reviews"}
            or type(state["version"]) is not int or state["version"] != 1
            or not isinstance(state["task_sha256"], str)
            or type(state["limit"]) is not int or state["limit"] < 1
            or type(state["attempts"]) is not int or not 0 <= state["attempts"] <= state["limit"]
            or not isinstance(state["used_reviews"], list)
            or any(not isinstance(item, str) or not item.strip() for item in state["used_reviews"])
            or len(state["used_reviews"]) != state["attempts"] or len(set(state["used_reviews"])) != state["attempts"]
        ):
            raise ReviewError("修复计数记录无效，不能自动重置。")
        if state["task_sha256"] != task[1]:
            raise HumanDecisionRequired("验收标准已变化，需用户确认新的修复周期；不自动重置轮次。")
        limit = min(limit, state["limit"])
    if state["attempts"] >= limit:
        raise HumanDecisionRequired(f"已达到 {limit} 轮修复上限，停止自动执行并交由用户决定；未宣称批准。")
    if context["review_id"] in state["used_reviews"]:
        raise ReviewError("同一次审查已用于修复，请复测并重新审查后再继续。")
    state["limit"] = limit
    state["attempts"] += 1
    state["used_reviews"].append(context["review_id"])
    # Consume before dispatch: failed or interrupted attempts still count.
    atomic_json_write(state_file, state)
    prompt = (
        f"读取规则 {target / 'AGENTS.md'}、任务 {task[0]} 和已核验报告 {saved[0]}。"
        "核对报告与当前代码是否一致，仅处理 findings 中已核验的 BLOCKER/CRITICAL；"
        "advisories 不要求修复。已修复或过期指控提交证据回应，不照单改代码。"
        "遵循最小修改范围并执行验收命令，保留真实结果。不要调用 Codex、其他实施入口、"
        "删除轮次记录或绕过修复上限，不提交代码；证据无法解决的争议停止并报告。"
    )
    print(f"[*] 修复执行 {state['attempts']}/{limit}；执行成功后仍需复测与独立审查。", file=sys.stderr)
    return run_agy(task_file=str(task[0]), prompt=prompt, target_project=target)


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

    p_fix = subparsers.add_parser("fix", parents=[parent_parser], help="Run one bounded repair attempt from a saved review")
    p_fix.add_argument("--review", required=True, help="Raw report saved by review --out")
    p_fix.add_argument("--task", "-t", default="docs/task.md", help="Acceptance criteria file")

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
    p_review.add_argument("--max-iterations", type=int, default=3, help="Maximum consecutive unapproved review iterations (default: 3)")
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
    elif args.command == "fix":
        try:
            success = run_fix(args.review, task_file=args.task, target_project=target_project)
        except HumanDecisionRequired as exc:
            print(f"[!] {exc}", file=sys.stderr)
            sys.exit(3)
        except (ReviewError, OSError) as exc:
            print(f"[!] {exc}", file=sys.stderr)
            sys.exit(1)
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
                max_iterations=args.max_iterations,
            )
        except HumanDecisionRequired as exc:
            print(f"[!] {exc}", file=sys.stderr)
            sys.exit(3)
        except (ReviewError, OSError) as exc:
            print(f"[!] {exc}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0 if approved else 2)


if __name__ == "__main__":
    main()
