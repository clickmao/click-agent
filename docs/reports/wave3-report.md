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

## 4.5 R12-R14 追加 (同日第二轮)

- **多源召回率定量** (round8 全指标采集): 6/10 用例有上下文片段 (4 指令类无需), 总片段 24;
  各源命中 — WorkspaceFiles+AgentContext 常规命中, Memory 按需, Session 设计性禁用
  (历史走 BuildWithHistory 专用通道, 双路注入浪费 token — 架构决策非缺陷)
- **R14 用户倾向全链路** (写入断链修复): 消息→ExtractSignals→UpdateTendencyAsync (fire-and-forget)
  →画像→GetContextBiasAsync 融合历史→UserTendency 召回 0→1snip/rel0.8
- **隔离判定 3 修**: Check 第2参 GoalText 原文→GoalIntent (意图相同误判 +1);
  goal 锚定收窄 IsGoalWorthy (偏好陈述"我喜欢简洁"不再锚成项目目标 → 误隔离修复);
  CalculateTendencyScore 样本计数→关键词命中占比×衰减
- **双向实测**: 偏好陈述→技术问题 不隔离+倾向召回 ✓; 任务锚→离题诗 隔离保留 score=2 ✓

## 4.7 R15-R19 追加 (第二轮循环)

- **R15 币种链**: deepseek 余额 CNY 被当 USD 比价 (差 7.2 倍) → BalanceSnapshot.Currency +
  EstimateBalance 换算 (FX env 可覆写) + ChannelScheduler.BalanceProbe 余额感知排序 +
  MIN_BALANCE env; 教训: 测试假绿 (旧 DLL), no-incremental 强编后 357 全绿
- **R16 触发链**: unit-convert regex 动词组 "转换成" 不命中 → C06 executive 直达 0 LLM (749tok→0)
- **R18 输出纪律**: System Prompt 统一附加简洁约束 — C08 completion -25~35%, round14 总 token -18.7%
- **R19 截断修复 (打点确诊)**: glm/deepseek reasoning 模型思维链计入 max_tokens, 2000 被
  reasoning 吃满 → C03 空白回复 (26.8s/2000tok, content_len=0) → 8192 + content_len 打点;
  复验 content 1756 字完整报告
- round15 基线: 10/10 KEEP, wall 88s (最快), 357 测试全绿, AOT 0 警

## 4.8 R20-R22 追加 (第三轮循环 — token/延迟双降)

- **R20 REPL 吞输入 (真 bug, 探针法确诊)**: 管道多轮第二轮静默丢失 — T1 处理期间
  SearchFailoverService 对未配置源发起凭据问询, Console.ReadLine 同步吞掉用户下一轮输入。
  修复: IsInputRedirected 保护 (凭据/确认/问询 全部非交互自动拒绝/默认值, 审计留痕);
  R14 隔离双向结论复验成立
- **R21 推理档位路由**: 实测 bigmodel glm-5.3-flash 支持 reasoning_effort=low
  (thinking.type=disabled 被拒); 简单意图轻思考 (简单题 reasoning 0 vs 8910ch),
  复杂信号词/长输入优先保留深推理不降智; round18 tokens -27%
- **R22 档位透传全链**: deepseek 同样支持; QueuePrompt/QueueChatRequest/Adapter
  全链透传 (source-gen WhenWritingNull, 不支持 provider 零影响)
- **round19 vs baseline_final**: tokens 7354→4909 (-33%), wall 154s→68.8s (-55%), 10/10 KEEP

## 4.9 R23-R26 追加 (第四轮循环 — 可靠性+长会话)

- **R23 failover (真 bug 21)**: 瞬态失败计数跨请求致单请求超时直接报错、从不切备 →
  请求内重试 1 次 + 切 key 可用备选; llm_retry/llm_failover 打点; 注入实测 glm 不可达→
  deepseek 接管 3.1s 真答
- **R24 超时余量**: HttpClient 100s 偶发掐断 reasoning 长输出 → 180s (llm.timeout_seconds 可配)
- **R25 输出方差治理**: C03 同题 completion 948↔3946 (4 倍) → 多步任务"先结论+要点 ≤500 字"
  (对照实验: 字数约束比 temperature 更有效)
- **R26 goal 误锚 (真 bug 22)**: 裸词"项目"命中"记住我的项目名是X" → 长会话 8/10 轮误隔离;
  记忆性陈述显式排除; 10 轮长会话复验隔离 0、history 0→7 条封顶 tokens 431 (滚动摘要实证)
- **round26 基线**: 10/10, 4373 tok (vs baseline_final 7354: **-40%**), wall 69s (**-55%**)

## 4.10 R27-R32 追加 (第五轮循环 — 快测基建+边界)

- **R27 --quick 模式**: 4 关键用例 ~60s/轮 (全量 70-140s) — 千轮级高频回归可行
- **R28 稳定性采样 ×3**: 4/4 全绿, tokens CV 12.8% (LLM 方差正常), wall 均值 57s
- **R29 真 bug 23**: workspace/agent_context snippet 缺 EstimatedTokens (0tok 显示瑕疵真因)
  → 打点/配额/压缩判定真实化 (82tok/22tok)
- **R30 数据边界**: workspace 扫描 300 上限改按修改时间降序 — 最近工作优先
- **R31 敏感可观测**: intent 打点带 sensitive 标记 (git push 请求实测 sensitive:true);
  行为级防护复验: git push 请求 → LLM 主动要求确认不盲执行
- **round32 全量**: 10/10, 4937 tok (vs baseline_final -33%)

## 4.11 R33-R35 追加 (第六轮循环 — 画像持久化)

- **R33 会话记忆格式**: LongTermMemory "[intent] 完成: X" 流水账 → 内容优先 (前60字+状态后置);
  双轮真机: 偏好陈述后 SessionMemory 1snip/rel0.95
- **R34 真 bug 24**: TendencyAnalyzer 内存字典跨进程丢光 (UserTendency 恒 0 的真因之一) →
  落盘 data/tendency/; 反射序列化被全局禁用 (打点确诊 InvalidOperationException) → 手写 JSON
  (零反射约束下字典+标量手写可控); fire-and-forget 在 /exit 快退时被杀 → 同步化
- **跨进程实战**: 进程1 Rust 偏好 (信号 2) → 落盘 → **独立进程2 召回 UserTendency 1snip/rel0.33**
- **AOT**: 手写序列化路径 0 IL 警; 358 全绿 (+TendencyPersistenceTests); round35 10/10 4401tok

## 4.12 R36-R40 追加 (第七轮循环 — 目标演化与隔离精修)

- **R37 阶段级对比固化**: eval/phase_report.py (早期 R3-R15 vs 近期 R17-R36:
  tokens -26.5%, wall -22.8%, 判定: 改善); 修正 glob 字典序 → 轮次数值序
- **R38 稳定性批 2**: ×3 quick 采样 6/6 全绿, tokens -13.4% vs 批 1 (无回归漂移)
- **R39 真缺陷 25/26 — goal 演化与隔离精修** (长会话实测驱动):
  - goal 永不更新: 任务转向 ("算了改成X") 后新方向全误隔离 → 转向标记词 pivot 重锚 + goal 打点
  - ascii 连写技术名 (RESTAPI vs FastAPI) 互不 Contains 误判零重叠 → 4-gram 交叉匹配
  - 技术细节追问 ("用 requests 怎么写") 与任务标题实体零重叠 → 实现询问 ≤30 字一票否决
  - 实战: 任务转向场景隔离 2→0; 真隔离 (离题诗) 保留
- **round36**: 10/10, 3977 tok — **新低, vs baseline_final -46%**
- **R40**: TaskRelevanceCheckerTests ×3 单测; 361 全绿; AOT 0 警

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
