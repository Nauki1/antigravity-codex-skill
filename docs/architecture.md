# Dual-Agent Architecture & Operating Model

## 1. 架构总览 (Overview)

`codex-loop` 旨在解决 AI 辅助研发中的两大核心痛点：
1. **单智能体自满盲区（Self-Validation Trap）**：单一模型既写代码又审查代码，极易产生确认偏差，导致引入回归缺陷或盲目重构。
2. **上下文孤岛（Context Islands）**：AI 助手的对话与临时思考停留在聊天界面中，无法作为长期资产进入项目版本库，其他模型或团队成员无法感知。

通过将 Google Antigravity (Gemini) 与 OpenAI Codex CLI 部署在同一个项目工作区中，并由 `AGENTS.md` 统领，实现“**松耦合、共享代码库、互补审查**”的闭环。

---

## 2. 角色矩阵 (Role Matrix)

| 维度 | Google Antigravity (Gemini) | OpenAI Codex CLI (`gpt-6.1-sol`) |
| :--- | :--- | :--- |
| **首要定位** | 全栈实施工程师 (Implementer) & 交互前端 | 首席架构师 (Architect) & 代码审查官 (Reviewer) |
| **交互模式** | 实时对话、终端执行、多模态、浏览器自动化 | 非交互式批处理 (`codex exec`, `codex review`) |
| **推理偏好** | 敏捷实现、多工具组合调用、复杂上下文组织 | 高深度链式推演 (`reasoning_effort="xhigh"`) |
| **输入来源** | 用户对话、工作区文件、终端输出、测试报错 | 项目代码、`AGENTS.md`、`git diff`、Session 归档 |
| **产出目标** | 业务代码、单元测试、会话归档 (`.agents/sessions/`) | 架构蓝图 (Plan Markdown)、Review 评定 (APPROVED / FIX) |

---

## 3. 防灾与质量四重防线 (Four Lines of Defense)

1. **异构红队审查 (Heterogeneous Red Teaming)**：
   不同模型厂商（Google vs OpenAI）具有互补的归纳偏好。Codex 对 Antigravity 的 Git Diff 进行代码审查，打碎“自检盲区”。
2. **最小修改原则 (Minimal Blast Radius)**：
   严禁全量覆盖和无关模块重构。代码修改仅限于解决当前 issue 或需求。
3. **测试驱动作为铁证 (TDD Verification)**：
   不接受任何主观形式的“功能已就绪”宣称，必须有终端命令退出码为 0 的实际测试日志作为佐证。
4. **Git 物理隔离与快速回滚**：
   复杂变更必须在分支或干净的工作区进行，出现不可逆逻辑混乱时一秒回滚。

---

## 4. 上下文持久化机制 (Context Persistence)

- 对话不再转瞬即逝：通过 `scripts/sync_session.py`，每次关键迭代的对话记录和决策要点都会被持久化为 Markdown 并受 Git 版本控制。
- Codex 在执行时，可读取 `.agents/sessions/` 下的历史纪要，保持上下文平滑延续。

---

## 5. 衍生文档与历史会话索引 (References & Sessions)

- **环境与模型追踪**：[docs/environment-and-models.md](file:///D:/codex-loop/docs/environment-and-models.md)
  *详细记录跨平台 Codex CLI 探测优先级、CC-Switch 鉴权、与 `gpt-6.1-sol` 零硬编码自动追踪体系。*
- **技能演进史**：[docs/skill-origin-and-evolution.md](file:///D:/codex-loop/docs/skill-origin-and-evolution.md)
  *记录从 Ubuntu 初始 Skill 到 Windows 检索、跨平台迁移及单工作区演进的全过程。*
- **核心会话归档**：
  - [`.agents/sessions/2026-09-29-find-codex-skill.md`](file:///D:/codex-loop/.agents/sessions/2026-09-29-find-codex-skill.md)：*首次在 Windows 检索、安装并解决自动跟进最新模型的讨论记录。*
  - [`.agents/sessions/2026-09-29-dual-agent-architecture.md`](file:///D:/codex-loop/.agents/sessions/2026-09-29-dual-agent-architecture.md)：*单工作区多 Agent 隔离共享架构与四道防灾防线的深度研讨。*
