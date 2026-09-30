# Codex + Antigravity 极简协同工程规范

**一个 Git 仓库、一份代码、轮流执行：Codex 负责计划和审查，Antigravity 负责实现和测试。**

## 1. 技术设计：共享文件，按目录分工

```text
project/
├── AGENTS.md          # 双方共同遵守的开发规则
├── src/               # 项目源码
├── tests/             # 测试
├── docs/
│   └── task.md        # 当前任务的目标、计划和验收命令
├── .agents/           # Antigravity 专属配置、规则
│   └── sessions/      # 简短的决策与交接记录
└── .codex/            # Codex 专属配置、审查记录
```

- **仓库是唯一真相源。** 双方打开同一个本地工作目录，修改直接落到同一份文件上。
- **文件保存后，另一端重新读取即可看到。** 本地交接靠文件系统，Git 负责版本记录与回退。
- **聊天上下文需要显式交接。** 目标、修改范围、关键决定和验收命令写入 `docs/task.md`。
- **专属目录隔离配置。** `.agents/` 和 `.codex/` 是职责划分，不是安全边界；账号密钥和临时日志不入库。
- **同一工作目录轮流操作。** 实现结束后再审查，审查期间冻结改动；切换 Git 分支也必须串行。

直接使用 CLI 和 Markdown。无需 JSON Schema、分布式锁、消息队列或常驻调度服务。

## 2. 双向调用：终端命令就是接口

以下命令均在仓库根目录执行。

### 正向：Antigravity 发起

**用户交互 → Codex 计划 → Antigravity 实现与测试 → Codex 审查。**

生成计划：

```powershell
codex exec --sandbox read-only -o docs/task.md "阅读 AGENTS.md 和最新 session，为【用户需求】制定最小实现计划。输出目标、修改范围、步骤、验收命令和风险；只做计划。"
```

Antigravity 读取计划，修改代码，运行验收命令。完成后审查：

```powershell
codex review --uncommitted
```

发现问题后，由 Antigravity 修复、重新测试，再交给 Codex 审查。

### 反向：Codex 发起

Codex 在终端完成规划，并将计划保存到 `docs/task.md`，随后一行调用：

```powershell
agy -p "阅读 AGENTS.md、docs/task.md 和最新 session；按计划实现，仅修改相关文件，执行验收命令，报告改动、测试结果和退出码；不要再次调用 Codex，不提交代码。" --mode=accept-edits
```

等待 Antigravity 返回后，Codex 检查实际改动和测试证据，再执行：

```powershell
codex review --uncommitted
```

**双向调用按任务选择入口。** 被调用方完成本阶段后返回，避免相互递归调用。

Codex 的 `exec`、`-o` 和审查目标参数见 [OpenAI 官方命令文档](https://learn.chatgpt.com/docs/developer-commands?surface=cli)。`--uncommitted`、`--base`、`--commit` 和自定义审查提示不能混用。

## 3. 开发与质量约束

| 约束 | 执行要求 |
|---|---|
| 最小修改 | 只改任务直接涉及的代码、测试和文档；扩大范围前说明原因。 |
| 测试验收 | 实际运行计划中的测试与构建命令，必要检查退出码为 0，并确认覆盖目标行为。 |
| 审查职责 | Codex 检查正确性、回归、边界条件和范围；修复交回实现方。 |
| 关键变更 | 核心算法、鉴权、架构和跨模块调用必须经过 Codex 审查。 |
| 审查结论 | 在 `AGENTS.md` 约定末行输出 `APPROVED` 或 `NEEDS_FIX`；存在未解决的阻断问题不得通过。 |
| Git 防灾 | 复杂修改前保存已有工作，再建立 feature 分支。分支本身不会隔离未提交改动。 |
| 回退范围 | 先检查差异，只撤销本任务改动；全量回退必须确认不会覆盖用户工作。 |

`APPROVED` 是项目约定的审查结论。**CLI 退出码为 0 只表示命令执行成功。** 禁止仅凭出现 “LGTM” 等关键词判断验收通过。

调用失败、超时或结果不完整时，保留现场，检查原因后重试；未取得有效测试或审查结果，任务保持未完成。

## 4. 落地 Checklist

- [ ] 确认两端使用同一个仓库根目录，`codex` 与 `agy` 均可调用。
- [ ] 精简 `AGENTS.md`，统一分工、修改范围、验收和审查规则。
- [ ] 更新 `docs/architecture.md`，记录上述目录与双向命令流程。
- [ ] 每项任务只维护一份计划，写清目标、修改范围和验收命令。
- [ ] 用一个小改动分别走通正向、反向流程，检查真实 diff 和测试结果。
- [ ] 现有包装脚本按需保留，仅转发命令、保存输出、返回退出码；移除关键词猜测审批和冲突参数组合。
- [ ] 完成验收后再提交，交接记录只保留关键决定、证据和遗留问题。

本机已确认 `agy -p` 和 `--mode=accept-edits` 可用；Codex 可执行文件存在，但当前终端的 PATH 尚未包含 `codex`，落地前需配置。