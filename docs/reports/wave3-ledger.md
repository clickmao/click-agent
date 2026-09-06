# wave3 优化循环台账 (R15-R50)

## 累计指标 (vs baseline_final 7354tok/154s, 全量 10 用例)
- **最优 tokens**: round51 3902 (-47%)
- **最快 wall**: round51 53.0s (-66%)
- **阶段均值演进**: 早期 (R3-R15) 7887tok/124s → 近期 5512tok/88.7s (tokens -30%, wall -29%)
- **质量**: 362/362 测试全绿; AOT 0 IL 警; 千轮批量 3 批 60/60 全绿且递减 (3243→3098→2981)

## 修复台账 (打点驱动, 每项真机实证)
| 轮 | 缺陷 | 修复 | 实证 |
|---|---|---|---|
| R15 | 余额币种混用 (CNY 当 USD, 比价错 7.2x) | Currency 解析+CNY→USD 换算+余额感知降权 | /balance 真机 9.49 CNY 币种正确 |
| R16 | unit-convert 触发词缺失 | 触发动词扩展+脚本重写 | 温度换算 executive 0 LLM |
| R18 | C08 输出冗长 (1875tok) | 输出纪律 | A/B -35% |
| R19 | glm reasoning 吃光 2000 配额 content 空 | MaxTokens 8192 | content_len 1756 字 |
| R20 | 搜索 failover 问凭据吞 stdin 多轮输入 | 非交互 ReadLine 保护 | 管道 2 轮全执行 |
| R21-22 | 简单题深推理浪费 | reasoning_effort=low 智能档+全链透传 | 同题 27tok, wall -55% |
| R23 | failover 名存实亡 (需 3 请求累计) | 请求内重试+立即切备 | glm 不可达→deepseek 3.1s |
| R24 | HttpClient 默认 100s 超时不够 | 显式 180s 可配 | C03 14.6s |
| R25 | 输出 4 倍方差 | 多步任务 300-500 字预算 | C03 554 字 |
| R26 | 裸词'项目'误锚 goal 致 8/10 误隔离 | IsGoalWorthy 排除记忆性陈述 | subagent 0 |
| R29/48 | ContextSnippet EstimatedTokens 缺赋 (3 处) | 补赋值 | 打点 tok 非 0 |
| R30 | workspace 扫描目录序截断 | mtime 降序 | 最新文件优先 |
| R33 | 记忆记录流水账格式 | 内容优先 | 偏好不被淹没 |
| R34 | Tendency 内存字典跨进程丢光 | 手写 JSON 落盘 (禁反射)+同步化 | 跨进程召回 1snip |
| R39 | goal 永不更新+ascii 黏连+实现询问误隔离 (25/26) | pivot 重锚+4-gram+否决 | 转向隔离 2→0 |
| R42 | 澄清回复冗长 | 问询纪律 | wall -15% |
| R44 | RAG 中英黏连+长文稀释+Keywords 失活 (27) | 边界切分+命中下限 0.45+自动提词 | Memory 0→1snip 跨轮召回 |

## 评测基建
run_round.py (--quick 60s/轮+reply_contains)、analyze.py (3 轮平滑)、
phase_report.py (阶段对比)、cross_validate.py (双 LLM 校验)、
AgentTelemetry 25+ 点位 (goal pivot/memory store/sensitive/tendency…)

## R58-R63 追加 (第九轮循环 — 可行性闭环与度量补全)
- R59 跨进程记忆恢复实证 ("项目代号 Alpha")
- R60 阶段全量 10/10 4011tok (阶段判定改善)
- R62 loop_turn 加 asked/executive 度量 + executive 直达补打点 (度量盲区消除, 实测 wordcount 466ms 直达可见)
- 千轮五批 92/92 全绿 (3243→3098→2981→3128→3314, CV 稳定带)
- R63 analyze round60/round51 对比: +2.8% 方差带内 KEEP

## R64-R71 追加 (第十轮循环 — 画像链路三连修)
- R65 (真缺陷 28): git 词表补中文动作 ("推送到/推送/上传到/检出") — "把代码推送到github" sensitive False→True 实证
- R66 (真缺陷 29): Milestones 记消息摘要而非意图名 ('general' → 实际任务描述)
- R70 (真缺陷 30): SetGoal constraints 死代码链修复 — ExtractConstraints 规则提取, 跨轮注入 prompt 【约束】行 ("继续" 轮遵守标准库约束实证), +3 单测
- round67 3831tok / round71 3817tok 连续新低 (-48% vs baseline)
- 千轮六批 112/112 全绿 (批6 CV 6.4% 历史最稳)

## R72-R73 追加 (第十一轮循环 — pivot 死区)
- R72 (真缺陷 31): pivot 重锚死区 — 隔离判定 (321 行) 先于重锚 (455 行), "不要之前的目标写诗"
  零重叠轮被先行拦截, 重锚代码永远不执行。三段修复: 词表+7 标记 / pivot 脱离 IsGoalWorthy /
  判定前 pivotRequested 跳过。实证: 隔离→主链 + goal pivot 打点 + 后续轮正常。+4 单测 369 绿
- 千轮批 7 ×3 (12/12); AOT 0 警

## R76-R80 追加 (第十三轮循环 — RAG 持久化闭环)
- R76 (真缺陷 32): cross_validate 数值前缀精度归一 (3.14159 vs 3.14 误判 disagree, R41 遗留闭环); 负例不误放
- R78 千轮批 9 ×5 (20/20, 九批 156/156)
- **R79 (真缺陷 33)**: RAGRecall 索引落盘持久化 — 内存索引重启全丢 (与 R34 Tendency 同类)。
  手写 JSONL (零反射), 写侧 IndexAsync 后 Persist (512 上限), 读侧构造 LoadPersisted。
  路径 CWD 优先 + AppContext 回退。实证: 进程1 记忆 → index.jsonl → 进程2 召回 1snip/56tok/r0.45
- R80 AOT 常态化: 手写 JSON 落盘过 AOT (0 警), AOT 二进制落盘 5→6 行 + wordcount 489ms 正常

## R81-R82 追加 (第十四轮循环 — 评测隔离)
- R81: run_round 评测隔离 — R79 落盘使前轮记忆泄入本轮 (C01 prompt 342→752 实测污染)。
  每轮启动前清 RAG 索引+会话记忆; **真机持久化功能不受影响** (这是评测口径修正, 非功能回退)
- 隔离后 mass_44 3105 (恢复 3000 带); round82 10/10 4212; 十一批 172/172

## R83-R84 追加 (第十五轮循环 — skill 失败降级)
- **R83 (真缺陷 34)**: skill 脚本错误 JSON ({"error":...}) 被当成功结果直出用户 (Content 非空 + Success=true)。
  修: dispatcher 检测输出含 "error" JSON → script_error_degraded → 降级 LLM。
  实证: '把100光年转成摄氏度' 裸错误 JSON → 友好解释 ("光年是距离单位，摄氏度是温度单位"); wordcount 正例不回归
- R84 全量 10/10 (4952, completion 方差带内, prompt 全正常); AOT 0 警

## R85-R87 追加 (第十六轮循环)
- R86 (缺陷 35): /help 未注册送 LLM 浪费一轮 → 本地应答 (0.98s / 0 LLM 实证)
- 千轮批 12-13 (24/24, 十三批 196/196); 阶段判定改善 (tokens/wall 均 -38.2%)

## 已知边界 (诚实标注)
- Session 源设计性禁用; ToolOutput 预留; PausedForApproval 仅影子计划
- CNY→USD 固定汇率 7.2 (env 可配)
- **P3 向量化已评估不可行** (R58): glm coding 端点与 deepseek 均无 embedding 模型 (API 实测);
  本地 ONNX embedding 违反轻量/AOT 原则 → 词面召回 + 内容命中下限 (R44) 为当前最优解,
  语义反转 (喜欢/不喜欢) 为已知接受边界
- kimi key 认证失败 (负样本保留); round11/16/21/22/24 波动已归因方差
