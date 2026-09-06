# wave3 阶段性评测报告 (打点驱动优化循环)

日期: 2026-09-06 | 模型: glm-5.3-flash (主) / deepseek-v4-flash (副) / kimi-k3 (负样本)

## 1. 基建产出

- **AgentTelemetry 打点层** (src/agent.config): 14 个点位 JSONL — boot / skill_load / skill_parse /
  skill_scan / skill / skill_exec / intent / assembly(source级) / prompt_build / llm_call /
  loop_turn / compression / evidence_gate / subagent
- **eval/ 评测基建**: 10 用例跑批 harness (run_round.py) + 对比分析 (analyze.py, 含 LLM 波动平滑) +
  ledger 台账 (REVERT/KEEP 判定) + 双 LLM 交叉校验 (cross_validate.py) + 召回报告 (recall_report.py)
- **虚拟 skills**: wordcount / unit-convert (executive, 脚本实跑) + 2 normative

## 2. 打点驱动修复台账 (14 项)

| # | 缺陷 | 修复 |
|---|---|---|
| 1 | bge 语义疑似 (level=1) force_use 吞掉正常提问 | normative 仅词面 (level≥2) 才 force |
| 2 | auto 模式选无 key 模型 | Policy/Scheduler key 可用性过滤 |
| 3 | /balance 带参未拦截 | 拦截条件支持参数 |
| 4 | BalanceScheme 键名 endpoint≠request_address | 键名同步 |
| 5 | deepseek 余额 shape 不符 (真实 API 溯源) | total_balance 解析 + CNY 币种标注 |
| 6 | 排他+语义疑似淹没词面强命中 | Level 优先于 Exclusive |
| 7 | executive skill 无 scriptRunner DI | DI 注入 + 输出直达回复 |
| 8 | FromCache 默认 true 统计失真 | 默认 false |
| 9 | goal 锚定不抽实体 → 隔离判定永不触发 | SetGoal 时 ExtractEntities |
| 10 | IsolatedTaskRunner DI 缺注册 (隔离子代理休眠) | 补注册 |
| 11 | 存储/召回双存储割裂 → Memory 源召回率恒 0% | StoreToMemory 双写 IRAGRecall |
| 12 | RAG 中文无分词 (整句 hash) → 词面/嵌入全失效 | 中文 2-gram 滑窗 (score 0→0.57) |
| 13 | WorkspaceFiles 源只有配额无实现 | RecallFromWorkspaceAsync (2-gram+行命中) |
| 14 | Workspace.Initialize 无人调用 → RootPath 恒空 | 装配 fallback Environment.CurrentDirectory |

## 3. 真机验证记录 (E2E)

- **余额查询**: deepseek-v4-flash 真实 9.49 CNY; kimi-k3 负路径 (invalid_authentication, 与用户预判一致);
  zhipu provider_not_supported 诚实标注
- **auto 模式选模**: key 可用性过滤后自动选 glm-5.3-flash, 真实调用 631 tokens
- **余额阈值切模**: 单进程 /model 切换 → 记账 (796 tok, $0.0005 估算) → /balance 再同步 9.49 CNY
- **隔离子代理**: 「电商项目」目标下问「写宇宙诗」→ score=4 (实体零重叠+意图不同+离题词) → 独立 session 执行
- **EvidenceGate 问询**: 「帮我处理一下那个数据」→ conf 0.55<0.60 → 批量问询 → 用户答「搜索资料」并入
- **记忆召回**: 5 条记忆 → 「项目代号?」→ Memory 源 1snip/64tok/rel0.39 → 正确回答 ZETA-7
- **workspace 召回**: readme 提问 → WorkspaceFiles 3snip/rel0.7
- **AOT**: 0 警重发布, 22 模型 JSON + wordcount 冒烟 (0.54s)
- **双 LLM 交叉校验**: 3 事实问题 (国土面积/光速/化学式) 3/3 agree

## 4. Round 台账 (ledger 全量)

| round | passed | tokens | verdict | label |
|---|---|---|---|---|
| round2 | 8/10 | 7615 | KEEP | 裁决修复+executive DI 承载修复后 |
| round3 | 10/10 | 7444 | KEEP | 隔离DI+goal实体+缓存标记+assembly统计 修复后 |
| round4 | 10/10 | 7329 | KEEP | prompt_build+compression 打点 + R5 历史滚动摘要 |
| round5 | 10/10 | 7457 | KEEP | R6 存储召回同源+中文2gram 分词 (召回率 0→有效) |
| round6 | 10/10 | 8241 | KEEP | evidence_gate 打点 (问询触发率观测) |
| round6 | 10/10 | 8241 | KEEP | evidence_gate 打点 (问询触发率观测) |
| round7 | 10/10 | 8554 | KEEP | R11 workspace 召回实现 (0→3snip)+R11b root f |
| round8 | 10/10 | 8650 | KEEP | assembly/prompt_build/gate 全指标采集版 |

- 召回覆盖 (round8): 6/10 用例有上下文片段 (4 指令类无需上下文), 总片段 24
- 历史治理 (R5): 7 轮长会话历史 token 封顶 (滚动摘要), 摘要化后信息保留实测正确

## 5. 已知边界 (诚实标注)

1. deepseek 余额 CNY vs 配置价格 USD 混用 — 换算率未硬编码, EstimateBalance 标注币种
2. 结果缓存 TTL 跨进程无效 (每进程新 DI) — harness 每用例独立进程不受影响
3. PausedForApproval 状态机在影子计划内, 主链 git/file_op 由 LLM 行为层确认 (未接状态机)
4. C01 平滑 token +24% — workspace 召回引入的 prompt 内容代价 (~200 tok), 在 1000 tok 配额内
5. GitHub 推送待新 token (GITHUB_TOKEN 过期), 4 commits 本地待发

## 6. 下轮候选

- ToolOutput / Session 源真机验证与实现补齐
- agent 画像胜率统计 (任务类别胜率/工具亲和) 定量报告
- 敏感意图主链状态机接入 (PausedForApproval)
- deepseek 余额 CNY→USD 换算配置化
