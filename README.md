# codex-loop 🔄

> **Antigravity (Gemini) + OpenAI Codex CLI 双智能体协同闭环框架与可进化 Skill**  
> GitHub Repository: [https://github.com/Nauki1/codex-loop](https://github.com/Nauki1/codex-loop)

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
│       └── 2026-09-29-dual-agent-architecture.md
│
├── .codex/                               # Codex 专有配置
│   └── config.toml                       # 项目级模型配置 (gpt-6.1-sol / xhigh)
│
├── docs/                                 # 共享知识库与架构文档
│   ├── architecture.md                   # 双 Agent 架构设计与理论规范
│   └── sessions/                         # 导出文档备用目录
│
├── scripts/                              # 核心工具链
│   ├── codex_loop.py                     # 双 Agent 自动化规划与审查引擎
│   └── sync_session.py                   # 会话纪要自动同步工具
│
├── AGENTS.md                             # 最高协作宪法 (Gemini 与 Codex 原生共同遵守)
├── SKILL.md                              # Antigravity Skill 标准定义
├── README.md                             # 项目说明
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
对未提交的代码改动（Git Diff）触发无头审查：
```bash
python scripts/codex_loop.py review
```
- 若返回 `0`：判定为 **APPROVED**，审查通过！
- 若返回 `2`：Codex 指出潜在缺陷与修改建议。

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
# 复制或建立软链接到 ~/.gemini/config/skills/
powershell -Command "Copy-Item -Path 'D:\codex-loop' -Destination '$env:USERPROFILE\.gemini\config\skills\codex' -Recurse -Force"
```
在任何对话中输入 `/codex`，即可直接调用最新的 `gpt-6.1-sol` 协同逻辑！
