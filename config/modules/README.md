# 模块定制配置 (L3) — 同名文件覆盖 config/base/ 同名配置
#
# 本目录每个 {module}.yaml 只写需要覆盖 base 的字段 (增量覆盖),
# 未写字段自动继承 config/base/{module}.yaml (规范 §3.2-2)。
# 示例: modules/core.yaml 中写 agentframework.agent.max_token_budget: 50000
#       → 生效值变 50000, 其余字段仍取 base。
