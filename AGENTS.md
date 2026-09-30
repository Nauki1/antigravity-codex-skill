# Dual-Agent Workspace Constitution (Antigravity & Codex)

本项目采用 **Antigravity (Gemini)** 与 **OpenAI Codex CLI** 双智能体协同模式，两者共享本项目代码与设计上下文。

---

## 1. 核心分工与职责 (Roles & Responsibilities)

| 智能体 | 主要职责 | 执行范式 |
| :--- | :--- | :--- |
| **Antigravity (Gemini)** | 需求梳理、交互反馈、代码编写实施、多模态产物生成、测试执行、会话沉淀 | 终端执行、文件读写、交互式对话 |
| **OpenAI Codex CLI** | 复杂业务深度规划（Plan）、异构无头代码审查（Review）、架构红线检查 | `codex exec` / `codex review` (模型: `gpt-6.1-sol` 等) |

---

## 2. 行为红线与防灾规范 (Safety Guardrails)

为了防止单智能体因自满盲区或过度自信破坏已有代码，所有智能体在本项目中均须严格遵守以下四项铁律：

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

---

## 3. 目录与知识共享规范 (Workspace Layout)

- **核心代码**：`src/` 为唯一事实来源 (Single Source of Truth)，双方只读写此目录。
- **共享文档**：`docs/` 存放系统架构（`docs/architecture.md`）与业务规范。
- **对话沉淀**：`.agents/sessions/` 存放 Antigravity 会话讨论的决策归档，Codex 启动时应先阅读最新 session。
- **Codex 专有区**：`.codex/` 存放 Codex 配置与审查结果缓存。
- **Antigravity 专有区**：`.agents/` 存放 Antigravity 专有规则与工具。
