# Antigravity 默认实施模型

## 目标与验收标准

暂时将 codex-loop 通过 Antigravity CLI 派发的初次实施与自动返工统一默认为 Gemini 3.8 Flash (High)，准确模型 ID 为 gemini-3.8-flash-high。实际命令必须显式传入 --model，不能依赖提示词或 CLI 隐含默认值。

- exec-agy 的默认任务及自定义提示都传入同一模型 ID。
- fix 保持原有审批、证据和持久预算保护，实际派发时也传入同一模型 ID。
- 模型默认值集中定义，相关技能说明同步更新；不改变 Codex 的规划/审查模型。
- 同步两个全局安装目录，保留 Codex 安装版既有工作区、JSON 完成状态及自动拒绝检查增强；仅给该入口补上模型参数。

## 支持范围与不做事项

仅修改 scripts/codex_loop.py、相关回归测试、SKILL.md 及本任务和审查证据。不修改 Antigravity 全局账户/界面偏好、不调用 Gemini 实施业务任务、不增加模型选择配置系统、不重构现有调用入口。

## 验收命令

python -B -m unittest discover -s tests -p test_*.py -v

源码和两个安装目录分别实际执行上述命令并退出0；核心派发变更取得有效独立 Codex 批准。审查沿用本任务文档并遵守默认三次熔断，不改变任务路径或重置计数。
