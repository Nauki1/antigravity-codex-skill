# codex-loop 🔄

> **Antigravity (Gemini) + OpenAI Codex CLI 双智能体协同闭环框架与可进化 Skill**  
> GitHub Repository: [https://github.com/Nauki1/antigravity-codex-skill](https://github.com/Nauki1/antigravity-codex-skill)

---

## 💡 项目初衷 (Motivation)

在现代 AI 辅助研发中，单一 Agent 常常面临两大困境：
1. **过度自信与自检盲区（Self-Validation Trap）**：同一模型写代码又自我审查，容易因确认偏差引入回归缺陷或盲目扩大修改范围。
2. **上下文孤岛（Context Islands）**：AI 助手的思维过程和方案讨论留存在聊天窗，一旦换工具或开启新会话，上下文直接断层。

`codex-loop` 提供了完整的**单工作区、松耦合、多智能体协同范式**：
- **OpenAI Codex CLI** 担任**首席架构师与独立审查官**（默认启用 `gpt-6.1-sol`，深度推理模式 `xhigh`）。
- **Google Antigravity (Gemini)** 担任**全栈实施工程师与交互助手**。
- 以根目录 **`AGENTS.md`** 为共同最高宪章，代码与测试全量共享，会话讨论自动沉淀为持久化文档。

---

## 📂 项目结构规范 (Project Layout)

```text
codex-loop/
├── .agents/                              # Antigravity 专有配置与数据
│   ├── rules/                            # 团队规范与代码约束
│   └── sessions/                         # 自动同步的会话纪要与设计决策 (Git 追踪)
│       ├── 2026-09-29-find-codex-skill.md         # 【会话沉淀一】Windows 技能检索、探测与模型追踪讨论
│       └── 2026-09-29-dual-agent-architecture.md  # 【会话沉淀二】双 Agent 架构设计与四道防灾防线研讨
│
├── .codex/                               # Codex 专有配置
│   └── config.toml                       # 项目级模型配置 (gpt-6.1-sol / xhigh)
│
├── docs/                                 # 共享知识库与架构文档
│   ├── architecture.md                   # 双 Agent 架构设计与协作规范
│   ├── environment-and-models.md         # 跨平台探测逻辑、CC-Switch 对接与零硬编码模型追踪
│   └── skill-origin-and-evolution.md     # 技能溯源 (Ubuntu -> Windows) 与同步维护指南
│
├── scripts/                              # 核心工具链
│   ├── codex_loop.py                     # 双 Agent 自动化规划与审查引擎
│   └── sync_session.py                   # 会话纪要自动同步与导出工具 (支持 --list / --conv-id)
│
├── AGENTS.md                             # 最高协作宪法 (Gemini 与 Codex 原生共同遵守)
├── SKILL.md                              # Antigravity Skill 标准定义
├── README.md                             # 项目说明与上手文档
└── .gitignore                            # Git 忽略配置
```

---

## 🚀 快速上手 (Quick Start)

### 1. 检查运行环境
确保本地已安装 Python 与 Codex CLI，验证配置：
```bash
python scripts/codex_loop.py info
```
输出将确认当前 active model（默认 `gpt-6.1-sol`）及 CLI 二进制路径。

### 2. 标准协作 5 步循环 (The 5-Step Loop)

#### Step 1: 架构规划 (Codex Plan)
让 Codex 以顶级架构师身份出具技术方案与任务清单：
```bash
python scripts/codex_loop.py plan "为项目增加基于 JWT 的认证与双因子验证" --out docs/auth_plan.md
```

#### Step 2: 实施落地 (Antigravity Implement)
由 Antigravity 读取方案，编写业务代码并运行本地单元测试：
- 严格遵循 `AGENTS.md` 中的“最小修改原则”。
- 以终端测试通过（Exit Code 0）为准绳。

#### Step 3: 异构无头代码审查 (Codex Review)
先按 [任务模板](docs/task-template.md) 记录目标、验收标准、支持范围、不做事项和验收命令。审查默认读取目标工程的 `docs/task.md`，可用 `--task <PATH>` 指定；审查期间标准变化则批准失效。未提供任务文档时沿用明确的用户指令和既有功能约束，不凭空增加要求。详见 [审查与收工规则](docs/review-policy.md)。
对未提交的代码改动（Git Diff）触发无头审查：
```bash
python scripts/codex_loop.py review
```
- 返回 `0`：有效结论为 **APPROVED**，审查通过。
- 返回 `2`：有效结论为 **NEEDS_FIX**，需要修复后复审。
- 返回 `1`：调用失败，或报告为空、缺少有效结论、存在引用或矛盾；任务保持待审查。

默认审查 staged、unstaged 和 untracked 变更；`--base` 审查指定分支与 HEAD 的 merge base 之后的已跟踪差异；`--instructions` 增加未提交变更的审查重点。`--base` 与 `--instructions` 不能同时使用。包装器统一使用原生自定义审查 PROMPT，附加结果协议，不混用原生 CLI 的 `--uncommitted` / `--base` 与 PROMPT。[OpenAI 参数文档](https://learn.chatgpt.com/docs/developer-commands)

原生审查器保持自己的 JSON schema，在 `overall_explanation` 字符串内输出审查协议 JSON（协议版本、审查完成状态、发现数量、整体正确性及理由）。CLI 会渲染此解释，并在其后附加发现详情。包装器仅在审查完整、发现数量为零、整体结论为 `patch is correct` 且没有额外内容时批准；字段缺失、重复、类型错误或不完整都不放行。

底层使用 `codex exec review --ephemeral --output-last-message <临时文件>` 取得渲染后的最终报告，而不是假设它导出原生 JSON。包装器保留完整报告，再输出对应的末行结论。进程失败、基线解析失败或临时结果缺失时返回 `1`；结果文件在读取后自动清理，不写入目标工程。

普通的 `LGTM`、否定、引用或代码示例中的批准词不会放行。协议通过调用提示词传入；已有目标工程无需修改规则来适配审批解析。

必须修复的发现还需提供唯一稳定 ID、位置、触发条件、预期与实际行为、影响、可核验证据和核验状态。发现数量必须与证据记录一致；未经核验或没有具体证据的错误结论返回 `1`，保持待审查，避免把猜测直接转成返工任务。

#### Step 4: 修复闭环 (Antigravity Fix)
Antigravity 针对 Codex 的 Review 意见进行微调，再次运行 `review` 直至获得 `APPROVED`。

#### Step 5: 会话归档沉淀 (Sync Session)
将本次开发的重要讨论与结论一键归档到项目中：
```bash
python scripts/sync_session.py --title "jwt-auth-implementation"
```

---

## 🛡️ 防灾与质量四重防线

1. **异构红队校验**：不同模型厂商的归纳偏差互补，彻底掐灭自满盲区。
2. **最小爆破半径**：代码变动仅限于目标本身，严禁借机乱动无关代码。
3. **测试作为铁证**：拒绝主观臆断，必须有终端真实构建和测试通过记录。
4. **Git 物理隔离**：任何试错均可一秒回滚（`git restore .`）。

---

## 📦 作为 Antigravity Skill 安装

你可以将本项目作为长期进化的 Skill 挂载到 Antigravity 全局配置中：
```bash
# 同步运行时文件至全局技能目录（安全排除 .git 与 .agents）
powershell -Command "Get-ChildItem -Path 'D:\codex-loop' -Exclude '.git', '.agents' | Copy-Item -Destination '$env:USERPROFILE\.gemini\config\skills\codex' -Recurse -Force"
```
在任何对话中输入 `/codex`，即可直接调用最新的 `gpt-6.1-sol` 协同逻辑！
