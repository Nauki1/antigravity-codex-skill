# Codex × Antigravity 单工作区双向协作技术设计

**建议采用：同一物理 Git 工作区 + 本地任务调度器 + 双向 CLI/MCP 接口 + 可追溯的验收证据。**

Codex 负责规划和最终审查，Antigravity 负责实施与测试。两端都可以发起任务，由同一调度器管理执行顺序、写入锁、日志和验收状态。

## 1. 当前项目基线与能力确认

本次已读取项目规则、最新会话、现有脚本和测试规划，并核对本机 CLI 帮助信息。

| 项目 | 已确认现状 | 设计影响 |
|---|---|---|
| 工作区 | `D:\codex-loop`，当前分支 `main` | 两端应绑定这个物理目录 |
| Codex | `codex-cli 0.159.0`，可通过绝对路径调用 | 当前 PATH 未找到 `codex`，需保留二进制探测 |
| Antigravity | 已安装 `agy 1.2.7` | 支持原生无头执行 |
| 正向流程 | 已有 `plan`、`review` 包装脚本 | 保留现有入口，逐步加固 |
| 反向流程 | 尚未看到执行适配器和任务协议 | 需要新增本地桥接层 |
| 工作区状态 | `scripts/codex_loop.py` 已修改，`docs/test_plan.md` 未跟踪 | 实施前必须保全现有修改 |

`agy` 的官方无头接口支持 `-p`、JSON/流式 JSON 输出和按会话 ID 恢复。因此，**Codex 调用 Antigravity 执行任务已有原生基础**。[Google：Headless mode](https://antigravity.google/docs/cli/headless/)

现有 [codex_loop.py](/D:/codex-loop/scripts/codex_loop.py:143) 仍有两个必须优先处理的问题：

- 审查参数可能同时组合 `--uncommitted`、`--base` 和自定义提示词，而这些审查目标互斥。
- 使用 `APPROVED`、`lgtm` 等关键词判断通过，存在否定结论被误放行的风险；项目 [test_plan.md](/D:/codex-loop/docs/test_plan.md) 已登记相关缺陷。[OpenAI：Developer commands](https://learn.chatgpt.com/docs/developer-commands?surface=cli)

**实施顺序应先修复验收判定，再开放自动执行闭环。**

## 2. 单文件夹共享与隔离机制

### 2.1 共享范围

双方始终操作同一份已保存到磁盘的文件：

| 路径 | 职责 | 管理规则 |
|---|---|---|
| `src/` | 业务代码、可复用编排逻辑 | 共同读取；实施阶段由当前任务写入 |
| `tests/` | 单元测试、集成测试、合成样本 | 共享，纳入同一审查 |
| `AGENTS.md` | 项目共同开发约束 | 双方加载，变更须明确列入任务范围 |
| `docs/` | 架构、业务规范、决策和任务定义 | 作为共享持久化上下文 |
| `.agents/` | Antigravity 规则、技能和会话摘要 | Antigravity 维护 |
| `.codex/` | Codex 项目配置、提示模板和审查摘要 | Codex 维护 |
| `.loop/` | 中立任务状态、锁、运行日志和证据 | 调度器维护，默认不提交 Git |

`.agents/` 与 `.codex/` 的隔离属于**配置和写入职责隔离**。两者使用同一 Windows 用户时，目录名称本身不构成安全访问边界。

需要双方理解的业务决策，应写入 `docs/`；各自会话摘要可以留在专有目录中，通过任务显式引用。

### 2.2 物理共享如何生效

两端读取同一个物理文件，因此无需文件复制、Git 推送拉取或网络同步：

1. Antigravity 保存文件。
2. 文件系统更新该文件。
3. Codex 下次读取同一路径时获得新内容。
4. 编辑器或调度器通过文件系统通知刷新缓存、标记状态变化。

在 Windows 上，可使用 `ReadDirectoryChangesW`，或通过 `.NET FileSystemWatcher` 等封装监听目录变化。通知可能因缓冲区溢出而丢失，因此必须提供重新扫描机制。[Microsoft：ReadDirectoryChangesW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-readdirectorychangesw)

必须明确以下边界：

- **磁盘内容共享，不代表模型对话记忆实时更新。** 每次实施、测试、审查前，都要重新读取相关文件。
- 编辑器中尚未保存的内容不会进入共享磁盘状态。
- 文件事件用于提示重新检查；任务是否完成，以持久化状态和证据为准。
- 同盘不同 clone、不同 worktree，仍然是不同工作目录。
- 无需网络搬运是指工作区文件同步；模型调用仍可能访问各自服务。

建议将普通本地变更的发现延迟设为 **1～2 秒验收目标**，通过实际测试确认，不承诺所有环境都固定秒级。

### 2.3 监听策略

- 监听源码、测试、任务定义和构建输入。
- 对连续事件进行约 300～500 毫秒合并。
- 排除依赖目录、构建产物和 `.loop/` 日志，防止循环触发。
- 启动、恢复和通知异常时执行完整扫描。
- 测试和审查前重新计算文件摘要，避免依赖过期缓存。

### 2.4 规则加载与配置边界

Codex 与 Antigravity 均支持项目 `AGENTS.md`，但两者都有目录级规则和覆盖机制。因此，“最高宪法”应通过项目治理实现：**目录规则只允许细化要求，禁止削弱根目录约束。** Codex 的规则链通常在启动时构建，规则更新后应启动新任务或会话。[OpenAI：AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)、[Google：Rules](https://antigravity.google/docs/rules/)

原生配置不必全部搬入项目：

- `.codex/config.toml` 保存项目级配置。
- `.agents/` 保存项目规则、技能和摘要。
- 用户级登录凭证及原生会话继续由各自产品管理。
- 不将用户级凭证目录复制进仓库。

## 3. 推荐目录组织

以下为目标结构；现有 `scripts/` 保持兼容，新模块逐步进入 `src/`，避免为目录统一附带大规模迁移。

```text
D:\codex-loop\
├── AGENTS.md
├── README.md
├── SKILL.md
│
├── src/
│   └── codex_loop/
│       ├── controller.py          # 状态机与任务调度
│       ├── protocol.py            # 协议校验
│       ├── workspace.py           # 工作区身份、锁与基线
│       ├── evidence.py            # 日志、差异与文件摘要
│       ├── adapters/
│       │   ├── codex.py
│       │   └── antigravity.py
│       └── mcp_server.py
│
├── scripts/
│   ├── codex_loop.py              # 保留现有 CLI，增加新入口
│   └── sync_session.py
│
├── tests/
│   ├── fixtures/
│   └── test_*.py
│
├── docs/
│   ├── architecture.md
│   ├── tasks/
│   ├── decisions/
│   └── protocol/
│       ├── task.schema.json
│       ├── result.schema.json
│       ├── review.schema.json
│       └── commands.json
│
├── .agents/
│   ├── rules/
│   ├── skills/
│   └── sessions/
│
├── .codex/
│   ├── config.toml
│   ├── instructions/
│   ├── sessions/
│   └── reviews/
│
└── .loop/                         # Git 忽略的本地运行区
    ├── locks/
    └── tasks/
        └── <task-id>/
            ├── task.json
            ├── state.json
            └── attempt-1/
                ├── agent.events.jsonl
                ├── agent.stderr.log
                ├── tests/
                ├── diff.patch
                ├── manifest.json
                └── review.json
```

建议保留脱敏后的任务定义和决策记录；完整原始会话、运行日志和临时证据默认留在本地。

## 4. 双向闭环工作流

### 4.1 调度组件

| 组件 | 责任 |
|---|---|
| Controller | 校验任务、取得写入锁、控制状态和重试 |
| Codex Adapter | 调用规划和审查，固定模型，解析结构化结果 |
| Antigravity Adapter | 启动 `agy`，读取进度，保存会话 ID，处理取消和超时 |
| Test Runner | 实际启动测试进程，独立捕获日志与退出码 |
| Evidence Collector | 收集完整差异、文件摘要和环境信息 |
| CLI/MCP 接口 | 向两端提供同一套任务操作 |

**双向互调意味着双方都能发起任务；每个任务只有一个调度器负责推进。** 子任务中的智能体禁止再次启动同一个完整闭环，避免递归调用。

### 4.2 正向流程：Antigravity 发起

1. Antigravity 提交需求和任务范围。
2. Controller 调用 Codex 生成规划。
3. Antigravity 根据规划实施。
4. Test Runner 收集实际测试结果。
5. Collector 固定当前文件状态和差异。
6. Codex 审查代码与验收证据。
7. 需要修改时，由 Antigravity 修复并重新验证。
8. 通过后归档结论。

现有 `plan` 和 `review` 入口继续保留，内部逐步接入统一协议。

### 4.3 反向流程：Codex CLI / IDE 发起

这是本次重点：

1. **Codex 完成规划。** 明确目标、允许路径、测试要求和验收条件。
2. **Codex 提交结构化任务。** 通过本地 CLI 或 MCP 调用 Controller。
3. **Controller 检查基线并取得写入锁。** 保全已有修改，记录提交与文件状态。
4. **Controller 在同一目录启动 `agy`。** Antigravity 读取任务、项目规则和规划，执行代码修改及测试。
5. **Controller 收集执行证据。** 保存进度、实际测试日志、退出码、完整差异及文件摘要。
6. **结果返回 Codex。** 返回任务状态、证据索引和可读取的文件路径。
7. **Codex 最终 Review。** 验收当前代码及对应证据。
8. **修复或完成。** 修复后重测重审；通过后归档。

反向调用启动的是 Antigravity CLI 会话。不能默认它继承当前 Antigravity IDE 聊天窗口的全部上下文；应通过任务文件和明确的会话 ID传递上下文。

### 4.4 权限前提

现有 `plan` 使用只读沙箱，适合分析源码。后续实施必须由具备相应授权的执行会话或 Runner 启动。

**调用外部智能体执行写入，同样属于写入操作。** 不得通过子进程、后台服务或 MCP 绕过当前会话的权限限制。

## 5. 原生命令与项目互调接口

### 5.1 原生 Antigravity 调用

以下是实施阶段可使用的原生命令示例，本次未执行任务：

```powershell
Set-Location -LiteralPath 'D:\codex-loop'

& 'C:\Users\Nauki\AppData\Local\agy\bin\agy.exe' `
  -p '读取 AGENTS.md 和 docs/tasks/T001.json，按任务实施并运行规定测试；报告未完成项。' `
  --mode=accept-edits `
  --output-format=stream-json `
  --print-timeout=20m
```

正式适配器应：

- 将子进程 `cwd` 固定为校验后的工作区根目录。
- 同时读取 stdout 和 stderr，防止管道阻塞。
- 使用 `agy models` 返回的实际标识固定 Gemini 模型。
- 保存返回的 `conversation_id`；修复时显式指定该 ID。
- 设置 CLI 超时和 Controller 总超时。
- 取消时终止整个任务进程树。

`accept-edits` 管理文件编辑行为，Shell 命令仍受工具权限规则约束。[Google：Execution modes](https://antigravity.google/docs/cli/modes/)

尤其要处理官方文档说明的情况：无头模式下某些权限请求可能被软拒绝，但进程仍退出 `0`。因此，`agy` 成功返回不能替代测试证据。[Google：Headless permissions](https://antigravity.google/docs/cli/headless/)

### 5.2 项目包装命令

以下为**待实现协议**：

```powershell
# 环境与接口诊断
python -B scripts/codex_loop.py doctor

# 执行 Antigravity 实施阶段
python -B scripts/codex_loop.py execute --task docs/tasks/T001.json

# 查看任务状态
python -B scripts/codex_loop.py status --task-id T001

# 对任务证据进行审查
python -B scripts/codex_loop.py review-task --task-id T001

# 运行完整闭环
python -B scripts/codex_loop.py loop --task docs/tasks/T001.json
```

Controller 内部使用参数数组调用子进程，避免将任务内容拼接成 Shell 命令。

### 5.3 Codex CLI 与 IDE 共用 MCP

第二阶段提供本地 STDIO MCP 服务：

| 工具 | 行为 |
|---|---|
| `submit_task` | 校验并提交任务，快速返回任务 ID |
| `get_task_status` | 查询阶段、进度和失败原因 |
| `get_task_result` | 返回差异、测试与审查证据索引 |
| `cancel_task` | 取消指定任务 |

任务应异步运行，避免一个 MCP 调用长期等待。

Codex CLI 与 IDE 支持共享同一 Codex host 的 MCP 配置，可使用项目 `.codex/config.toml` 注册此服务。[OpenAI：MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)

后台模式采用受管理的本地 Runner。Google 的 `agy remote-control start` 面向官方远程交互界面，不应直接视作 Codex 可调用的任务 API。[Google：Remote Control](https://antigravity.google/docs/remote-control?tab=cli)

## 6. 任务、结果与审查协议

### 6.1 任务协议

示例中的摘要和模型值由实际环境生成：

```json
{
  "schema_version": "1.0",
  "task_id": "T001",
  "origin": "codex",
  "workspace": "D:/codex-loop",
  "baseline_commit": "<实际提交 SHA>",
  "baseline_manifest_sha256": "<实际基线摘要>",
  "goal": "实现 Antigravity 反向执行适配器",
  "plan_file": "docs/tasks/T001-plan.md",
  "allowed_paths": [
    "src/codex_loop/",
    "tests/",
    "scripts/codex_loop.py"
  ],
  "required_checks": [
    "unit-tests",
    "adapter-integration"
  ],
  "acceptance_criteria": [
    "执行结果返回完整证据索引",
    "测试失败不能进入完成状态",
    "同一工作区禁止两个任务同时写入"
  ],
  "models": {
    "codex": "gpt-6.1-sol",
    "antigravity": "<经 agy models 确认的 Gemini 标识>"
  },
  "max_attempts": 3,
  "timeout_seconds": 1800
}
```

协议约束：

- 校验任务 ID、路径穿越、符号链接及 junction 越界。
- 固定提交、规划、规则和命令注册表的摘要。
- 测试使用 `command_id`，由可信命令注册表解析执行。
- 命令注册表本身属于受保护输入，不能随任务任意修改。
- 同一任务 ID和同一请求重复提交，不得重复启动实施进程。
- 修改目标或扩大允许范围时，产生新版本任务定义。

### 6.2 执行结果协议

执行结果分成两类：

- **智能体报告：** 实施说明、未完成项、会话 ID。
- **调度器事实：** 实际改动、测试进程、退出码、文件摘要。

调度器生成的结果示例：

```json
{
  "task_id": "T001",
  "attempt": 1,
  "execution_status": "IMPLEMENTED",
  "agent_exit_code": 0,
  "checks": [
    {
      "command_id": "unit-tests",
      "exit_code": 0,
      "test_count": 24,
      "log": ".loop/tasks/T001/attempt-1/tests/unit-tests.log"
    }
  ],
  "changed_paths": [
    "src/codex_loop/adapters/antigravity.py"
  ],
  "manifest_sha256": "<实际文件状态摘要>",
  "diff_file": ".loop/tasks/T001/attempt-1/diff.patch"
}
```

`IMPLEMENTED` 只表示实施阶段结束。测试和审查全部通过后，才能标记整个任务完成。

### 6.3 审查协议

```json
{
  "task_id": "T001",
  "attempt": 1,
  "reviewed_manifest_sha256": "<被审查文件状态摘要>",
  "verdict": "APPROVED",
  "blocking_findings": [],
  "acceptance_checks": [
    {
      "id": "tests-passed",
      "passed": true
    }
  ]
}
```

允许的结论限定为：

- `APPROVED`
- `CHANGES_REQUESTED`
- `INCONCLUSIVE`

字段缺失、格式错误、状态矛盾或证据不匹配时，均不得批准。

保留项目要求的 Codex Review 门禁。本机 `0.159.0` 的帮助信息还确认 `codex exec review` 支持 `--output-schema`、`--json` 和 `-o`，可作为结构化审查入口。应在新规则中明确其与 `codex review` 的对应关系；需要保留字面命令时，可先保存原生审查，再生成结构化验收结论。

**退出码 `0` 表示调用成功；最终批准必须通过严格协议校验。** 禁止继续使用宽松关键词匹配。

## 7. 并发、防灾与证据约束

### 7.1 一个工作区同一时间只有一个写入任务

同一 Git 工作目录中的分支、索引和文件都被两端共享。创建 feature 分支不会隔离两个进程对文件的修改。

建议：

- Controller 使用操作系统文件锁或命名互斥量。
- 写入锁覆盖实施、最终测试、证据固定和审查阶段。
- `.git/index.lock` 只保护特定 Git 操作，不能充当工作区任务锁。
- 手工编辑绕过锁时，文件状态校验必须发现变化并使旧验收失效。

确需并行写入时，另建 worktree；每项任务中的 Codex 和 Antigravity 仍应绑定同一个 worktree。

### 7.2 证据必须覆盖完整改动

Collector 至少保存：

- staged 和 unstaged 的差异。
- 新增未跟踪文件及其内容摘要。
- 删除、重命名和二进制变更。
- 测试命令、cwd、版本、开始结束时间、退出码及测试数量。
- 规划、规则与构建输入摘要。

不能仅靠普通 `git diff`，因为它不能完整覆盖上述所有状态。

最终验收条件：

```text
规定测试实际通过
AND 被审查状态与被测试状态一致
AND 当前状态仍与被审查状态一致
AND verdict == APPROVED
AND 无阻塞问题、无范围越界
```

审查后任何相关文件继续变化，都需要重新验证。

### 7.3 有限修复与安全恢复

建议状态序列：

`PREPARED → EXECUTING → VERIFYING → REVIEWING → COMPLETED`

需要修复时进入 `CHANGES_REQUESTED`，随后启动下一次 attempt。执行失败、取消、超时和验收无法确认必须分别记录。

- 默认最多三次自动修复。
- 达到上限后保留证据，报告尚未解决的问题。
- 进程崩溃后先检查真实文件状态，再决定恢复。
- 不自动重放可能已经完成的副作用操作。
- 状态文件采用临时文件写入后原子替换。

建议修订现有回滚规则：**禁止在存在用户未提交修改的共享工作区自动执行全量 `git restore .`。** 先保全基线和差异，明确回滚范围；Git 不能恢复所有未提交内容。

## 8. 实施 Checklist

### 阶段一：固定基线与修复验收

- [ ] 保全当前未提交修改，记录基线。
- [ ] 明确 `src/`、现有 `scripts/` 和 `tests/` 的职责。
- [ ] 修复审查目标参数互斥问题。
- [ ] 替换关键词审查判定，加入严格协议校验。
- [ ] 覆盖否定结论、空输出、非零退出、损坏输出等回归场景。
- [ ] 建立 `doctor`，核对实际版本、路径和支持参数。

**交付：可靠的原有正向流程。**

### 阶段二：建立最小反向闭环

- [ ] 定义任务、结果、审查 Schema 和命令注册表。
- [ ] 实现工作区身份检查、写入锁和状态机。
- [ ] 实现 `agy` 无头适配器、流式日志、超时和取消。
- [ ] 实现完整差异与测试证据采集。
- [ ] 固定 Codex 为 `gpt-6.1-sol`，固定实际 Gemini 模型。
- [ ] 打通 Codex 规划 → Antigravity 实施 → Codex Review。
- [ ] 使用独立测试仓库进行真实冒烟，避免影响当前未提交工作。

**交付：可通过终端运行的双向闭环。**

### 阶段三：接入 Codex CLI / IDE

- [ ] 实现异步 MCP 工具。
- [ ] 在项目配置中注册本地服务。
- [ ] 验证 CLI 与 IDE 都能提交、查询、读取结果和取消。
- [ ] 实现受管理后台 Runner，确保任务状态持久化。
- [ ] 验证客户端关闭、服务重启和重复提交场景。

**交付：两端共用任务入口。**

### 阶段四：建立长期维护约束

- [ ] 实现文件通知、事件合并和扫描恢复。
- [ ] 验证审查期间外部修改会使证据失效。
- [ ] 验证含空格、中文路径及 Windows 编码。
- [ ] 建立版本兼容记录和受影响测试检查。
- [ ] 更新 `AGENTS.md`、架构文档、README 和 Skill。
- [ ] 对核心编排及跨模块调用变更执行 Codex Review。

**交付：可持续维护的协作框架。**

## 9. 最终质量门槛

| 维度 | 必须满足 |
|---|---|
| 物理共享 | 双端与子进程指向同一校验后的目录 |
| 写入控制 | 并发写入被阻止，现有修改得到保全 |
| 范围控制 | 改动限定在任务允许路径内 |
| 测试真实性 | 实际退出码为 `0`；测试发现数量符合要求 |
| 证据完整性 | 新文件、暂存改动、删除和二进制变更均可追溯 |
| 审查可靠性 | 严格解析 `APPROVED`，拒绝否定、引用和矛盾结论 |
| 版本一致性 | 测试、审查和最终交付对应相同文件状态 |
| 故障行为 | 超时、软拒绝、取消、崩溃和解析失败不被放行 |
| 调用边界 | 无递归闭环，无借互调绕过权限 |
| 可维护性 | 保留原有入口，变更具备对应测试与文档 |

本次交付为技术设计与实施计划；已核对本机接口和仓库状态，尚未修改代码或执行真实双向闭环。