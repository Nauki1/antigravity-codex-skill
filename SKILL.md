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
任务文档必须写清目标、可验证的验收标准、支持范围、不做事项和验收命令；未确认假设保持待确认，不转成强制要求。可参考 [任务模板](docs/task-template.md)。实施与审查沿用这份标准，扩大范围需用户授权。
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
审查默认读取目标工程的 `docs/task.md`（存在时），也可用 `--task <PATH>` 指定验收标准。路径相对目标工程解析；显式文件缺失、为空或无法读取时不启动审查。任务内容以快照传入，审查期间标准变化则本次批准失效。可选优化和支持范围之外的需求不成为强制返工任务；相关安全、数据完整性及已有功能回归仍须检查。
- 返回码 `0`：有效结论为 **APPROVED**，审查通过。
- 返回码 `2`：有效结论为 **NEEDS_FIX**，进入修复循环。
- 返回码 `1`：调用失败或报告没有有效结论，保持待审查，不能提交交付。

审查模式互斥：默认审查 staged、unstaged 和 untracked 变更；`--base <REF>` 先解析 REF 与 HEAD 的 merge base，再审查其后的已跟踪差异；`--instructions "审查重点"` 增加未提交变更的审查重点。`--base` 与 `--instructions` 不能组合。底层统一使用原生自定义审查 PROMPT，以便附加结果协议；不与原生 `--base` / `--uncommitted` 标志混用。

原生审查器保持自己的 JSON schema，在 `overall_explanation` 字符串内输出当前 `codex-loop-review-v3` 协议 JSON。CLI 渲染此解释并附加发现详情。审查完成、验收达标、整体正确、没有已核验实质缺陷或待决疑点/争议时批准；可选建议放入 `advisories`，可带建议收工。未核验实质疑点放入 `uncertainties`，不能直接派发返工。结构缺失、字段重复、类型错误或未知附加内容不放行。v2 仅可作历史输入。

每个发现必须包含唯一稳定 ID、位置、具体触发条件、预期行为、实际行为、影响、复现或确定的可达代码证据，以及明确的核验状态。包装器检查证据字段与数量的一致性；证据缺失、未经核验、ID 重复，或只给出“整体错误”却无具体问题时，保持待审查，不自动要求返工。字段检查不能替代审查器对证据真实性的核验。

底层通过 `codex exec review --ephemeral --output-last-message <临时文件>` 取得渲染后的最终报告，并保留完整内容。此选项不导出原生 JSON。调用、基线解析或结果读取失败时返回 `1`，临时文件读取后自动清理，不写入目标工程。

包装器负责输出项目约定的 `APPROVED` / `NEEDS_FIX` 末行结论。协议通过调用提示词传入，已有目标工程无需修改规则来适配审批解析。不能把 CLI 执行成功、自然语言措辞、否定、引用或代码示例中的批准词当成批准。

#### Step 4: 修复闭环 (Remediation Loop)
- 首次审查用 `--out reviews/first.txt` 保存原始报告。
- Antigravity 修复已核验问题并复测，或提交有证据的反驳；回应 JSON 引用 `finding_id`，包含 `position`（`fixed` / `disputed`）、`reason` 与 `evidence`。
- 复审用 `--previous-review reviews/first.txt --response reviews/response.json --out reviews/second.txt`，审查器逐项独立裁定 `closed` / `confirmed` / `needs_human`。证据未解决争议时返回 `1`，不批准或自动返工。具体格式见 [审查与收工规则](docs/review-policy.md)。
- 后续使用最近报告聚焦复审上轮问题、修复及相关回归，延续全部旧 ID 和关闭记录。已关闭问题须用 `reopened` 和额外 `new_evidence` 明确重开；范围内新发现仍需核验证据，不追加无关优化要求。
- 自动修复须用 `fix --review reviews/first.txt --task docs/task.md`，读取 `review --out` 保存的原报告与 `.context.json`。默认最多2轮，配置可在新周期前设置；启动前计数，失败或中断也消耗轮次，同一审查不得重复派发。
- `fix` 返回 `3` 表示到达上限、验收变化或存在待决问题，停止并交由用户决定。不得改用 `exec-agy`、删除计数、换任务路径或调高参数绕过。新周期须用户明确授权并记录；工具不自动重置。返回 `0` 的实施执行仍须复测与独立审查，不等同交付批准。

---

### 2. 反向协同闭环 (Codex 发起 ➔ Antigravity 静默执行 ➔ Codex 审查)

当在 Codex 侧或脚本流中需要由 Antigravity 自动编写代码并执行测试时：
```bash
python <SKILL_PATH>/scripts/codex_loop.py exec-agy [--task docs/task.md] [--project <TARGET_DIR>]
```
Antigravity CLI (`agy`) 将在目标工程后台以静默无头模式（`--mode=accept-edits`）实施代码并执行测试，完成后交还 Codex 执行复审。

`exec-agy` 用于初次实施。审查后自动返工使用上面的 `fix` 入口和持久化预算，不能重复调用初次实施入口绕过上限。

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
