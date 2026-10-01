# MEC597 实战反馈驱动的审查升级

## 目标与验收

- 审查调用与临时比对资产只使用目标工程之外的系统临时目录；成功、失败、缺失/无效结果、执行异常及可捕获中断均清理临时资产。
- `init` 创建或幂等增补 `.gitignore`，包含 `.review*`、`.agents/sessions/*.tmp`，保留既有规则，dry-run 不落盘。
- 当前协议明确分级：BLOCKER/CRITICAL 要求修复并返回2；SUGGESTION/MINOR 不阻断，输出建议及 APPROVED_WITH_NOTES，返回0。证据与验收标准保护、原生结果一致性、历史问题身份和争议裁定继续有效。
- `review --max-iterations` 默认3；同一任务连续未获批的审查不能通过重新启动命令绕过。第3次仍未获批后生成《待裁决争议报告》，停止自动执行并返回3；后续不再调用模型。批准结束连续失败序列。持久记录放在 `.codex/codex-loop/`，不是根目录临时快照。
- 文档及初始化规则明确四阶段生命周期。用户消息在第3项的“规定”处截断，补充要求暂未收到；按阶段进入/结束及实际阻塞输出“阶段、完成、证据、下一步、阻塞”的最小卡片，不推断额外任务。

## 支持范围与不做事项

修改现有 scripts/、tests/、AGENTS.md、SKILL.md、.gitignore 与直接相关说明，不迁移 src/、修改业务工程文件、清理既有用户文件、重写鉴权或新增后台调度系统。默认两个自动修复轮次与三个审查迭代分别约束实施和审查，显式配置仍可设置更低预算。

## 验收命令

```text
python -B -m unittest discover -s tests -p test_*.py -v
python C:/Users/Nauki/.codex/skills/.system/skill-creator/scripts/quick_validate.py D:/codex-loop
```

核心审查逻辑须取得真实 Codex 审查的有效批准，保留测试输出、原始报告及受审文件哈希。审查本次升级本身也遵守默认熔断；超过上限时交用户裁决，不另起无计数循环。
