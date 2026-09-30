---
name: codex-loop
description: >-
  Autonomous Dual-Agent collaboration loop between Google Antigravity (Gemini) and OpenAI Codex CLI.
  Orchestrates Codex as the Lead Architect/Reviewer (using the latest reasoning models, e.g. gpt-6.1-sol / o3)
  and Antigravity as the Full-Stack Implementer, operating concurrently within any shared target project workspace.
---

# Codex-Loop Dual-Agent Orchestration Skill

`codex-loop` is a continuous, evolvable skill and framework that coordinates **Google Antigravity (Gemini)** and the **OpenAI Codex CLI** inside a single shared repository or any target business project workspace.

It enforces a **Loosely Coupled, Shared-Workspace** architecture:
- **Lead Architect & Code Reviewer**: OpenAI Codex CLI (powered by `gpt-6.1-sol` with `xhigh` reasoning effort).
- **Full-Stack Implementer & Interactive Partner**: Google Antigravity (Gemini).
- **Shared Constitution**: `AGENTS.md` at workspace root.
- **Persistent Memory**: Session logs and architectural decisions saved under `.agents/sessions/`.

---

## 目录分工与工作区绑定 (Workspace Architecture)

| 目录类型 | 说明 | 职责与产物 |
| :--- | :--- | :--- |
| **Skill 源码母港** (`D:\codex-loop`) | 技能本身的开发仓库 | 核心脚本、测试用例、发布构建与文档 |
| **Skill 全局安装目录** (`~/.gemini/config/skills/codex` 等) | 供 Antigravity/Codex 全局加载 | 运行入口、规则模板与协议 |
| **目标业务工程** (Target Project，如 `D:\projects\my-app`) | 实际业务代码工程 | 业务源码、`AGENTS.md`、`.codex-loop.toml`、任务与审查证据 |

> [!NOTE]
> **智能工作区继承**：所有命令默认自动绑定当前编辑器或终端所在的工作区目录为目标工程；也可以在任意位置通过 `--project <PATH>`（或 `-P <PATH>`）显式指定目标工程。

---

## 常用操作与协作流程 (Workflow & Commands)

### 0. 目标工程接入与初始化 (Target Init)
在目标业务工程中接入双智能体协同规范（轻量幂等增补 `AGENTS.md` 与 `.codex-loop.toml`）：
```bash
python <SKILL_PATH>/scripts/codex_loop.py init [--project <TARGET_DIR>] [--dry-run]
```

查看当前 Codex 环境与目标工程状态：
```bash
python <SKILL_PATH>/scripts/codex_loop.py info [--project <TARGET_DIR>]
```

---

### 1. 正向协同闭环 (Antigravity 发起 ➔ Codex 规划 ➔ Antigravity 实施 ➔ Codex 审查)

#### Step 1: 架构深度规划 (Codex Plan)
调用 Codex CLI 无头推理，根据项目实际代码分析需求并生成技术设计与步骤 Checklist：
```bash
python <SKILL_PATH>/scripts/codex_loop.py plan "<TASK_REQUIREMENT>" [--out docs/task.md] [--project <TARGET_DIR>]
```

#### Step 2: 代码实施与验证 (Antigravity Execute)
- Antigravity 读取目标工程规则与生成的任务文档（`docs/task.md`）。
- 实施具体代码修改与单元测试。
- 在终端运行工程验收命令，确保退出码为 `0`。

#### Step 3: 异构独立审查 (Codex Review)
Codex 审查工作区未提交变更，拦截逻辑漏洞与回归隐患：
```bash
python <SKILL_PATH>/scripts/codex_loop.py review [--project <TARGET_DIR>]
```
- 返回码 `0`：有效结论为 **APPROVED**，审查通过。
- 返回码 `2`：有效结论为 **NEEDS_FIX**，进入修复循环。
- 返回码 `1`：调用失败或报告没有有效结论，保持待审查，不能提交交付。

审查模式互斥：默认审查 staged、unstaged 和 untracked 变更；`--base <REF>` 先解析 REF 与 HEAD 的 merge base，再审查其后的已跟踪差异；`--instructions "审查重点"` 增加未提交变更的审查重点。`--base` 与 `--instructions` 不能组合。底层统一使用原生自定义审查 PROMPT，以便附加结果协议；不与原生 `--base` / `--uncommitted` 标志混用。

原生审查器保持自己的 JSON schema，在 `overall_explanation` 字符串内输出审查协议 JSON（协议版本、审查完成状态、发现数量、整体正确性及理由）。CLI 渲染此解释并附加发现详情。包装器仅在审查完整、发现数量为零、整体结论为 `patch is correct` 且没有额外内容时批准。有发现或整体结论错误时需修复；结构缺失、字段重复和类型错误均不放行。

底层通过 `codex exec review --ephemeral --output-last-message <临时文件>` 取得渲染后的最终报告，并保留完整内容。此选项不导出原生 JSON。调用、基线解析或结果读取失败时返回 `1`，临时文件读取后自动清理，不写入目标工程。

包装器负责输出项目约定的 `APPROVED` / `NEEDS_FIX` 末行结论。协议通过调用提示词传入，已有目标工程无需修改规则来适配审批解析。不能把 CLI 执行成功、自然语言措辞、否定、引用或代码示例中的批准词当成批准。

#### Step 4: 修复闭环 (Remediation Loop)
- Antigravity 读取审查反馈意见。
- 遵循最小修改原则修复缺陷并复测。
- 重新运行 `review` 直至获得 `APPROVED` 判定。

---

### 2. 反向协同闭环 (Codex 发起 ➔ Antigravity 静默执行 ➔ Codex 审查)

当在 Codex 侧或脚本流中需要由 Antigravity 自动编写代码并执行测试时：
```bash
python <SKILL_PATH>/scripts/codex_loop.py exec-agy [--task docs/task.md] [--project <TARGET_DIR>]
```
Antigravity CLI (`agy`) 将在目标工程后台以静默无头模式（`--mode=accept-edits`）实施代码并执行测试，完成后交还 Codex 执行复审。

---

### 3. 会话与决策沉淀 (Session Archival)
将 Antigravity 的高价值会话决策导出为目标工程可读的 Markdown 记录：
```bash
python <SKILL_PATH>/scripts/sync_session.py --title "<TASK_NAME>" [--project <TARGET_DIR>]
```

---

## 行为红线与防灾规范 (Safety Guardrails)

1. **最小修改原则 (Minimal Blast Radius)**：严格只修改与目标直接相关的代码，严禁非受权重构。
2. **铁证验收原则 (Evidence-Based Completion)**：任何修改必须通过终端真实测试验证，退出码为 0 方可放行。
3. **异构审查机制 (Heterogeneous Red Teaming)**：关键架构与核心逻辑必须获得异构模型（Codex `gpt-6.1-sol`）明确批准。
4. **Git 物理防灾**：确保工作区清洁，多任务或可能破坏性修改必须依托独立分支。
