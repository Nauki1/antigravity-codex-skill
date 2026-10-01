# Antigravity 默认模型变更验收

任务标准：docs/tasks/gemini-default-model.md；基线与受审文件 SHA256 见同名前缀 manifest.json。

源码将默认值集中定义为 gemini-3.8-flash-high，并在 run_agy 的实际命令中显式传入 --model。初次 exec-agy、自定义提示和 fix 返工共享该入口；Codex 规划/审查模型及原有修复证据与预算规则保持原行为。

真实命令 python -B -m unittest discover -s tests -p test_*.py -v：99项通过，退出0。新增回归验证三个派发场景的实际命令参数，并保留原有全套测试。技能结构 quick_validate 校验也退出0。没有为了验证参数启动 Gemini 实施业务任务。

独立 Codex 审查使用 gpt-6.1-sol，首轮取得有效批准，退出0；通过只读检查和独立内存验证确认符合范围。审查器自身在受限沙箱重跑全套测试遇到临时目录权限限制；真实宿主测试的成功证据见 tests.txt，原始审查结果见 attempt-1.txt。

全局同步以系统临时目录作三方比对，保留各安装版已有 run_agy 工作区绑定、JSON 状态和自动拒绝检查，仅在该函数增加模型参数。两个安装版的实际测试输出与同步信息另存于同名前缀 global-*-tests.txt 和 global-sync.json。不修改 Antigravity 账户或界面默认偏好。

APPROVED
