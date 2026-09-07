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

## R89-R93 追加 (新指令验收轮)
- **R89 (真缺陷 36)**: auto 选模成功后 _activeModelId 不更新 → /model /balance 查询落目录首项 gpt-4o 与实际调用 glm 脱节;
  /balance 无参改查实际活跃模型。3 端点 E2E: glm chat✓ (reasoning_effort=low, c=3) / ds✓ 余额 9.48 CNY +
  MIN_BALANCE=20 阈值切模 glm 实证 / kimi 负样本复测 invalid_authentication_error (as-is)
- R90 **P3 重测闭环** (用户指定): LLamaSharp 0.20+bge-small-zh q8_0 JIT 可行 (26MB/512dim/6-21ms/区分度 3.9×),
  **AOT SIGSEGV 不可用** (0.27 容器 segfault 坑同记) → AOT 红线下维持 R58 结论, 报告 docs/reports/p3-retest-feasibility.md
- R92 **STJ source-gen** (用户注意点 2): RAG 落盘手写拼 JSON+手写解析 → JsonSourceGenerator
  (STJ v10 JsonSerializerContext 在 Serialization 命名空间坑记录); 落盘格式兼容, 跨进程恢复召回实证, AOT 0 警
- R93 **覆盖扩展** (用户注意点 1): cases 10→14 (+C11 JSON 格式返回+平衡块校验器 / +C12 负样本极短输入 /
  +C13 git 敏感 / +C09b glm 余额 as-is); round91 14/14; 批 14 ×5 20/20 (CV 5.0% 稳定)

- R94 **quick 集 4→5** (+C11 JSON 格式哨兵 — 每批产出格式合规率维度); 批 15 ×5 25/25 (CV 11.7%,
  每用例均值 788 优于批 14 的 836); 隔离/pivot E2E 复验 ✓ (pivot 后正常作诗, 旧 goal 零拦截)
- R95 analyze.py 加 **json_format_rate** PGO 维度 (<100% 触发 REVIEW); ToolOutput 源码审计确认预留边界
- R96 批 16 ×5 25/25 (CV 12.7%, 批15→16 同集 Δ -6.3% 稳定); **C11 JSON 合规累计 10/10 (100%)**

### R100-R102 (v0.11.0 vendored LLamaSharp 接入段)
- R100 **LLamaSharp fork 独立 repo**（v0.29.0 tarball→/home/agentuser/LLamaSharp，git init 3 commits，推 clickmao/LLamaSharp）: AOT 补丁（Assembly.Location→ProcessPath/BaseDirectory 优先，Silk.NET 式解析）；native 获取=deps.zip(570MB) 拒绝全量下载，**中央目录选择性解压**（EOCD/CD Range 拉取+本地解压，15 条目 22.5MB，avx2/vulkan/noavx linux-x64）→ sentinel+deps/ 伪布局绕过 csproj 570MB 下载
- R100 **P3 关键实测**: 0.27 native segfault → **0.29 native JIT 加载成功**（bge q8_0 dim=512 装载 385ms，相似句 0.9469 vs 无关 0.20-0.23，**区分度 4.3×** 优于 0.20 的 3.9×）；BgeEmbeddingProvider（LLamaEmbedder，CPU 档 GpuLayerCount=0，L2 归一）+ IEmbeddingProvider 抽象（hash 默认行为不变）
- R101 **真缺陷 37**: IOutputSink 从未注册 DI — RunSmokeAsync(v0.10 引入) GetRequiredService 必抛，**AOT 冒烟闸门自 v0.10 起实际失效**；修=BuildProvider 前注册+Main 复用同实例。实证: smoke 从必崩→DI 10/10+Agent Ready+E2E 走通。RAGConfig.EmbeddingFunction 注入位（null=词面，AOT 安全默认）；Logging 系包统一 10.0.10
- R102 **召回对比实验**（同 8 文档集同 6 查询 top-1）: 词袋 hash **1/6** vs bge 向量 **6/6**；R58"词面最优"前提更新=仅"无本地 embedding"时成立。诚实边界: 探针 hash 为简化复刻（无 R44 content_hit floor/R76 归一），生产管线强于探针；bge 仅 JIT 形态启用，AOT 形态仍词面（红线不破）

## 已知边界 (诚实标注)
- Session 源设计性禁用; ToolOutput 预留; PausedForApproval 仅影子计划
- CNY→USD 固定汇率 7.2 (env 可配)
- **P3 向量化已评估不可行** (R58): glm coding 端点与 deepseek 均无 embedding 模型 (API 实测);
  本地 ONNX embedding 违反轻量/AOT 原则 → 词面召回 + 内容命中下限 (R44) 为当前最优解,
  语义反转 (喜欢/不喜欢) 为已知接受边界
- kimi key 认证失败 (负样本保留); round11/16/21/22/24 波动已归因方差

## R103-R104 (2026-09-07): 多 CLI 共享 LLM + bge 优先路由 (用户钦定)
- **共享 LLM 服务化** (多 CLI 实例不重复加载): `--llm-service` 守护进程单次加载 chat+bge, UDS 帧协议 (4B 长度+STJ source-gen JSON, AOT 零反射), ping/chat/embed 三操作; 客户端短连接 + IsAlive 互斥 (二次启动 exit 3)。LocalLlamaCaller 服务优先/进程内兜底。+7 单测 (376/376)。
- **E2E 实证**: 服务单实例加载后, CLI 提问 0 次进程内加载 ("本地模型加载完成"0 次), native 推理日志在服务侧; 二实例启动被拒; embed 同句 cos=1.0000。
- **EmbeddingRouter** (bge 首选/词袋兜底, 用户钦定): BgeModeDecision — LLM 已加载→CPU 档, 独立+真 GPU→vulkan, llvmpipe 软设备→CPU; RAG DI 接线。
- **native 布局修复**: 0.29 统一二进制事实 — libggml.so 所有变体 DT_NEEDED libggml-vulkan.so → 每变体目录必须含 libggml-vulkan.so (NATIVE-LAYOUT.md); csproj 复制 target 布齐运行输出 5 变体。
- **缺陷 38** (真): 本地通道无 llm_call 打点 = PGO 盲区, harness llm_calls=0 误判失败 → 对齐云端路径补打点 (ModelQueueRouter.cs:196-213), 实证 provider=local 落盘。
- **台账补账**: mass_64-70 (批 16+17a) 全绿入账; 待真对话 gguf (qwen2.5-0.5b q4 下载中) 后批 17 续跑。

### R104 补记: 批 17 完成 + qwen 本地通道
- 批 17 (mass_69-73): **25/25 全绿**, 均值 3890 tok (批16 3690, +5.4% REVIEW=LLM 波动 CV21.5%); wall 48-125s。
- 本地通道真模型: qwen2.5-0.5b-instruct q4_k_m (491MB, hf-mirror) 接入 models.yaml; **ChatML 模板修复** (裸拼接 0.5B 复读垃圾→'2' 正确) — LlmServiceHost chat 分支。
- AGENTFRAMEWORK_LOCAL_DISABLED=1 批测开关 (qwen CPU 71s/轮不适合千轮批, local 保留 failover 语义)。
- 全链真机: CLI→共享服务→qwen→回复 "2" (70s)。

### R105: AOT 全链 (带 LLamaSharp) + 批 18
- **AOT 全链发布**: 0 IL 警告; publish 目录布 native 6+6 so; --smoke exit 0 (E2E Success=True, 多轮 round2Success=True, qwen 本地链路在 AOT 下完整)。
- **bge AOT 复验**: publish 布局下区分度维持 (无关对 cos 0.20-0.23) — AOT 铁律下 bge 可用定论。
- 批 18 (mass_74-78): **25/25 全绿**, 均值 4119 tok (批17 3890, +5.9% 波动带内, C03 单轮+859 平滑持平)。
- 千轮累计: 18 批 291/291 无漂移。

### R107: 批 19 + harness 双缺陷修复 (环境漂移实证)
- **批 19 (mass_79-84): 30/30 全绿**, 均值 3618 tok (批18 4119, **-12.2% 无劣化**, CV 11.2%); wall 78-119s。
- **真缺陷 39** (harness): `--quick` 是 flag 却占 argv[1] → 轮名错位, 实测落盘 `--quick.json` 轮名丢失。
  修复: 位置参数过滤 flag 后解析 (run_round.py main)。
- **真缺陷 40** (评测污染/环境漂移): qwen2.5-0.5b gguf 下载就绪 (00:14) + llm-service 守护重启 (00:15)
  → local 通道 IsAvailable=true; 首跑 mass_79 (14 用例全量) 未设 AGENTFRAMEWORK_LOCAL_DISABLED=1,
  **全部用例被 local 优先抢走**: tokens=0 (本地通道无 token 打点), 0.5B CPU 慢 (C02 173s),
  C11 长指令撑爆 local ctx 4096 → "The context window is full" 真实失败 (13/14)。
  证据存档 eval/results/mass_79_localctx_fail.json (RETIRED, 不入千轮统计)。
  修复: harness 层 env.setdefault 强制 LOCAL_DISABLED=1 (不依赖调用方记得设);
  逃生口 AGENTFRAMEWORK_EVAL_ALLOW_LOCAL=1 供本地通道专项评测。
- 千轮累计: 19 批 321/321。教训: 环境态 (模型文件/守护) 变化是评测最大漂移源, harness 应自防御。

### R109: 缺陷 41 (RAG 同内容重复入库) + 批 20
- **缺陷 41 (真)**: IndexAsync 无去重 — 千轮循环同题记忆反复写入, 召回 rel 并列 (0.45/0.45) 区分度退化, 同题召回 token 随库线性涨 (C11 Memory 126→465tok, round91→round106 实测)。
- 修复: 归一化内容指纹 (字母数字+小写, FNV-1a 64bit 零反射) 命中 → 复用既有 Id (更新语义); 附带 PersistPathOverride (评测隔离可注入落盘路径)。
- +3 单测 (去重 3 语义), **379/379 全绿**。批 20 (mass_85-89) 25/25, 3961 tok (+7.6% 带内)。
- 漂移归因定论: prompt 侧确定性无漂移 (C01 356=356 逐字节), completion 侧 LLM 风格波动是唯一漂移源。

### R109b: 批 21 (fix#41 后验证)
- 批 21 (mass_90-94) 25/25, mean 3793 tok (-4.3% vs 批 20 3961); C11 Memory tok 349→325 — **语料线性增长停止, 去重修复在千轮负载下实证有效** (ledger.jsonl 5×KEEP)。千轮累计: 21 批 371/371。
- 运维注记: dotnet 不在非登录 shell PATH (FileNotFoundError 实证), 需 export PATH=$HOME/.dotnet:$PATH + DOTNET_ROOT; ghfast.top 首推 TLS 中断 (既往 >8min 属正常, 本例 2min10s 断), 重推。

### R110: 缺陷 42 (telemetry 单文件竞争) + 批 22
- **缺陷 42 (真)**: harness 共享单 telemetry 文件 remove→append→read 时序竞争 — 间歇 llm_calls=0 误判 (mass_99/99b/99c/99d 失败用例漂移: C11→C01, 无并发下仍现)。诊断过程并发手动复现曾污染数据 (自我警示: 批测期间禁并发手动 CLI)。
- 修复: AGENTFRAMEWORK_TELEMETRY env 支持**绝对目录**覆写 (off/on 语义保留); harness 每用例独立目录 case_{id}/host.jsonl, 读侧对应改。
- 复验: mass_101-105 **5 连 5/5**, 4311 tok (+13.7% vs 批21, glm 上行波动); 379/379 全绿; 批 99 系 RETIRED 不作口径。
- cross_validate 双模型抽检 2 题 agree=true (glm+ds)。

### R110b: 缺陷 43 (评测单实例互斥) — 并行 tick 双 runner 实证
- **缺陷 43 (真)**: 两 cron tick 并行各起一个 run_round.py → 共享全局资源 (遥测路径/轮间 RAG+会话清理) 互删 → mass_95/96 假 llm_calls=0 假 REVERT (批 95-100 RETIRED 口径外), 比单点缺陷 42 更大面积污染。两 tick 独立收敛同一根因 (本 tick 经 A/B 对照 + /proc 抓幽灵 runner 实证)。
- 修复: run_round.py 入口 fcntl LOCK_EX|LOCK_NB 抢 data/eval_run.lock, 失败诚实退出 3 (与 llm-service IsAlive exit 3 同语义), 排队会焊死时间轴 — 故不等待。验证: 持锁时第二实例 rc=3 零写入; 空闲时正常跑通。
- **第二张面孔**: AOT publish (R110 验证) 重建 bin/ 为 linux-x64 布局并清掉 JIT bin → 窗口内 eval 用例 CLI 启动失败 0/5 (wall 650ms/例)。修复: publish 后 `dotnet build -c Release` 恢复 JIT bin (评测用, 3.6s); AOT publish 与 eval 并发仍需锁外协调。AOT 冒烟复验 OK (publish/agenthost 12.7MB)。
- 未决: 锁验证正例一次 4/5 (证据随清理删除, 无法归因); 同代码 sibling 批 22 25/25 — 待下批 ledger 佐证或复现。

### R111: AOT 重发布 (fix#41/42 后) + 批 23
- **AOT 全链复验**: 强刷 publish (rm bin/obj) → "Generating native code" 真判据 + 0 IL 警告; 5 native 变体 × 6 so 全齐 (0.29 铁律: 每变体 libggml+libggml-vulkan 同目录可达); 冒烟 E2E Success=True + round2Success=True + exit 0 (20s 云端 glm)。
- 冒烟 WARN "Success=true without API key" 提示文案与实际 (env key 已加载) 不符 — 观察项, 不修。
- 批 23 (mass_108-112): 25/25 全绿, **3889 tok (-9.8% vs 批22)** — 批22 4311 确认单批 glm 波动峰值, 连续 3 批 >4100 治理条件未触发。
- mass_106-107 RETIRED (AOT 强刷删 bin → harness --no-build 环境事故, 非代码; 教训: publish 强刷后必须先 dotnet build CLI 产物再批测)。

### R113: 批 25 + 缺陷 44 (llm-service 双守护互斥绕过) + run_round --help 防护
- **批 25 (mass_118-122): 25/25 全绿**, 均值 3865 tok (批24 3490, +10.7% 单批波动, mass_119 +18.9% REVIEW 前后轮回落佐证 LLM 波动; 批22 峰值 4311 后下行序列内)。C11 JSON 合规 100% 保持。千轮累计: 25 批 **471/471** (口径内, 99系/95-100系/106-107 RETIRED 除外; 批21 累计371 + 批22 25 + 批23 25 + 批24 25 + 批25 25)。
- **缺陷 44 (真, 运维实证)**: llm-service **双守护并存互斥绕过** — 两实例 (04:57/05:44 起, 同父 Hermes gateway=并行 tick 各自重启) 同时 LISTEN 同一 sockaddr, 且 fs 上 data/llm.sock inode 与两守护 listen inode 全不符 = 客户端 connect ECONNREFUSED, **服务实际不可达** (IsAlive 探测 stale 文件 false → 新实例删 stale bind 新 inode 成功 → 旧实例孤儿监听)。处置: 杀双实例 + 删 stale sock + 重启单实例 (pid 1139857) → ping/embed(384维)/chat("OK", 6.5s qwen) 全通, fs inode == listen inode 单一归属。**根因未代码修**: bind 后 sock 路径条目被外部删除即触发 (R110 重启协调未覆盖), 观察项, 再发则给 LlmServiceHost 加 bind 后自检 (fs inode == 本进程 listen inode 否则退出)。
- **run_round.py --help 防护**: 无位置参数默认 rnd="baseline" 且 flag 过滤吞掉 --help → `run_round.py --help` 真跑全量 baseline 180s 被杀 (实测浪费 + 扰动 eval 隔离态)。修: -h/--help/? 零副作用打印用法 exit 0。
- 守护环境核实: AGENTFRAMEWORK_BGE_MODEL=bge-small-en-v1.5-q4_k_m.gguf (384 维, 与 R102 记录 bge-small-zh 512 维不同 — 模型文件实际仅 en-v1.5 存在, 历史记录偏差, 当前以 env 实证为准)。

### R113: CLI 共享 LLM 服务整体退场 (用户钦定 2026-09-07)
- 删除: LlmServiceProtocol/LlmServiceHost/LlmServiceClient.cs + LlmServiceTests.cs (7 测试) + Program.cs --llm-service 参数与守护块 + LocalLlamaCaller 服务探测块 (回进程内直连) + ServiceCollectionExtensions 服务探测 (llmLoaded 恒 false, bge 决策按未加载档)。
- EmbeddingRouter/BgeModeDecision 的 llmLoaded 入参保留 (与共享服务解耦的通用决策参数)。
- 验证: 372/372 绿 (379-7); CLI E2E glm 直连 ✓ ('2'); data/llm.sock 死文件清除; AOT 强刷 0 IL 警 + 冒烟 E2E/多轮 pass (12.8s)。
- 批 25 (mass_118-122): 25/25 全绿, 4260 tok (+22.1% vs 批24, prompt 侧 356/373 稳定 = 波动在 glm completion, 非删除回归)。\n
### R114: LLamaSharp Vulkan 加载重构 — Silk.NET 式单入口 (用户钦定)
- **实证**: libllama.so/libggml.so 均带 RUNPATH=$ORIGIN → 单入口 dlopen 后系统加载器自动解析全部 DT_NEEDED (libggml/libggml-base/libggml-cpu/libggml-vulkan→libvulkan.so.1); deps.zip 不需要 (无需重编译 C++)。
- **fork 补丁** (ed89226): NativeLibraryUtils.TryLoadLibrary 加 Linux 快路径 (description.Path 为空时单入口 dlopen 顶层 libllama.so, 失败自然 fallback 旧选型策略); NativeLibrarySingleEntry 新类; TryFindPath 的 ProcessPath 加 NET6 防护 (netstandard2.0 target 修复)。deps.zip 入 gitignore (252b68f)。
- **主仓**: agent.csproj 顶层 runtimes/linux-x64/native/ 全量 so 复制 (变体目录保留为 fallback); probes/llama-r114-probe (JIT+AOT 双验收探针)。
- **验收 (全部真实执行)**: JIT — bge CPU 384 维 cos 0.728/0.478 ✓ + qwen chat success=True ✓ + [loader] "R114 single-entry load" 日志实锤 ✓; AOT (probe PublishAot 强刷) — "Generating native code" + 0 IL 警 + 同套验收全通 exit 0 ✓; 主 host AOT 冒烟 E2E+多轮 ✓; 372/372 绿。
- Vulkan 语义: 系统唯一 libvulkan.so.1 + fork vendored libggml-vulkan.so 同目录 — 无副本、无变体复制、无 deps。\n
### R115: 3 真实 key 余额链 E2E + 阈值切模实战 (用户钦定) — 4 真缺陷 (43/44/44b/45/46)
- **E2E (全部真实 API)**: glm-5.3-flash 直连 ✓ (1+1=2, JSON 格式跟随 ✓); deepseek-v4-flash 真余额 9.02→9.01 CNY (真实扣费) ✓; kimi-k3 负样本诚实报错 ✓; glm 无 scheme 诚实报 provider_not_supported ✓。
- **缺陷 43**: TokenUsageService.InitializeAsync 无调用点 (R15 引入) → 余额快照恒空 → 阈值切模死代码。修复: LazyBalanceSync fire-once (首调用 bounded-wait 3s)。
- **缺陷 44/44b**: QueryAsync 形参语义是 modelId 但传 provider 名 → Find 落空回落 gpt-4o (openai) → deepseek 快照永远填不上; 修: provider→代表模型解析 + 代表条目按 key 可用性优先 (新旧 deepseek 条目并存, 旧条目 env 名未设)。
- **缺陷 45**: 汇率方向反 — CNY→USD 用乘 7.2 (9.02 CNY 虚报 $64.94), 应除 (=$1.25)。打点立功: balance_sync ok=true 但切模日志 remaining=$64.87 暴露。
- **缺陷 46**: SelectAlternativeByBalance 候选未过滤 key 未配置模型 (曾切到 claude-sonnet-4-5 而 ANTHROPIC_KEY 未设 → 必败)。修: 候选 key 过滤。
- **切模实战实证**: MIN_BALANCE_USD=100 注入 → 手动 deepseek → "余额不足 ($1.25) → 切换 glm-5.3-flash" → 对话实际用 glm ✓。
- balance_sync 打点 (ok/model/remaining/error) 补齐; BalanceThresholdTests ×2 (374 绿); 批 26 (mass_123-127) 25/25, 3623 tok (-15% vs 批25)。

### R116: 创作类意图缺陷 47 + 多轮隔离/pivot E2E 真断言 (P3 bge 真链)
- **缺陷 47 (真)**: "帮我写一首关于秋天的短诗" 命中 "帮我写" → code_generation (C15 pivot 实测暴露) → 创作类规则 0 (规则表首位, 在测试生成/代码生成前) 修复 → IntentCreativeTests ×5 (含 C15 确切输入)。379/379 绿 (374+5)。
- **harness 扩展**: run_case_repl (多轮 REPL 用例执行器 — 单进程 stdin 顺序喂 repl 行, 逐轮回复块解析, telemetry 全程聚合); summarize_points +4 维度 (isolated/isolated_score/bge_provider/bge_ms); cases.json 16 用例 (+C14_isolated_multi/C15_pivot_multi)。
- **C14/C15 E2E 真断言** (mass_128 内, 真实 glm): C14 轮1 锚 Redis → 轮2 天气 → **isolated=true relevance_score=2 (实体零重叠), 独立 session 14.4s 秒回** ✓; C15 轮2 "算了...写诗" pivot → **未被隔离误吞, 新任务链产出真实诗歌, intent=general (fx47 生效)** ✓。两用例 PASS (llm=2)。
- **P3 bge 真链**: bge_embed provider=bge-local dim=512 (修复前 hash-fallback 词袋) — 进程内直连真向量。
- **批 27 = mass_128 full-16: 16/16 全绿, 13428 tok, 422.9s** (全量含 13 旧 + C09b + 2 新 repl 用例)。千轮累计: 26 批口径 496/496 + full-16 轮。
- **ledger.jsonl 回填**: 批 26 (mass_123-127, R115 commit 后中断遗漏) 6 行补齐 (25/25, 均值 3623 tok)。
- **运维**: 清理 R113 退场后遗留的 llm-service 僵死守护 (pid 1139857, 2h25m 孤儿监听 data/llm.sock) + sock 死文件; 双 tick 重复 runner (10:40 旧 bin 失真 → 杀; 10:48 新 bin 有效 → 让其跑完 mass_128 后接力收尾)。
- **AOT 复核**: publish 强刷 0 IL 警告 (R116 C# 改动 = 规则表, 铁律复验)。\n
### R117: Vulkan 硬件结论 + csproj 布局精简 + 缺陷 49 Memory 源体积治理
- **Vulkan 真 GPU**: 本机仅 llvmpipe 软渲染 (Cirrus GD5446 虚拟 VGA, 无 NVIDIA) — 真 GPU 硬件路径本环境不可实测, bge-mode 决策语义已正确覆盖 (检测→CPU 档)。
- **csproj 布局精简**: 删 avx512/avx/noavx 假变体目录 (复制的是 avx2 二进制 — noavx 机器 fallback 会 SIGILL 的假绿雷; R114 顶层快路径 + TryFindPath 原名回退已覆盖 fallback 语义)。runtimes 169M→精简。
- **缺陷 49** (打点驱动): Memory 源召回无 per-source 体积预算 — bge 真链后语义分带变密, C11 prompt 604→808 (+34%, 3snip/708tok/rel0.35 低相关大片段)。治理: 相关性降序 + 500tok 预算截断 + rel<0.4 只留 best 1。**A/B: C11 808→664 avg (-18%)**, 批 prompt 总量 2256→2037 (-10%)。
- 批27 (129-130 有效, 131-133 被批28 覆盖) + 批28 (131-135) 25/25+15/15... 记账: 129/130/131/132/133/134/135 全 5/5 KEEP; 批28 avg 4248tok; C11 664; cross_validate 双 LLM agree=true; 379 绿; AOT 0 IL 警 + 冒烟 ✓。\n
### R118: 缺陷 50 Workspace 相关分比例化 + 批 29
- **缺陷 50** (打点驱动): WorkspaceFiles RelevanceScore 硬编码 0.7 — 1 词命中=多词命中同分, r0.7rel 恒定失真, 无法支撑预算/排序。修: FindKeywordLineRanked (最佳行+命中数统计, ≥5 提前退出) + 分数=0.4+0.5*min(1,hits/5)。实证: 天气查询 r0.63 / 排序查询 r0.7 (3 命中) — 分数随真实质量变化。
- 批29 (mass_141-145) 25/25 KEEP, avg 4106tok (-3.4% vs 批28); C11 prompt 608-656 稳态 (缺陷49 治理后); Memory 1snip/57-63tok (低相关 best-1 生效)。
- 382 测试 (+WorkspaceRelevanceTests 3); host bin md5 核对 (agent.dll 一致+新符号在)。AOT 重发布待批30 后。\n
### R119: AOT 重发布 (fix#50) + C16 四轮长会话 + 批 30
- **AOT 重发布**: 0 IL 警 + 冒烟 ✓ (workspace 相关分在 AOT 下生效 r0.7rel)。
- **C16_longsession_4turn** (cases 16→17): 锚→无关(隔离 score=2 ✓)→pivot→回锚 — 4×intent/4×llm_call/isolated:true×1, 轮4 回锚恢复 Redis 语境 (forecast=延续当前任务) ✓。assembly 3/4 (pivot 轮短路, 观察)。
- **批30** (mass_151-155): 24/25 — mass_151 C03 llm_calls=0 = telemetry 瞬时丢失 (reply 完整/wall 35s/复跑 mass_156 5/5 绿, 非功能回归); 有效 20/20 + 复跑 5/5, avg 3414tok (批29 4106, -16.8%)。
- C11 prompt 稳态 608-656 (缺陷49 治理后无反弹)。

### R120: telemetry 瞬时丢失防护 + 余额链长跑 + 批 31
- **评分器可靠性 (钦定原则: 评分器必须比被测对象可靠)**: mass_151 C03 假阴性根因审计 — writer 生命周期/Configure 单调用/env 覆写均排查, 无法复现 (单次瞬态)。防护: run_round anomaly 判定 (llm_calls=0 但 reply 非空 → telemetry_anomaly 标记按通过计, 供后续审计), 防止打点链路缺陷污染被测对象评分 (假阴性→错误 REVERT 风险)。
- **余额链长跑**: deepseek 7.61 CNY (9.02→7.61, 千轮+批测真实消耗持续记账)。
- **批31** (mass_161-165) 25/25 全绿 avg 3656tok (波动带内; 批30 3414/批29 4106); anomaly 未再现。

### R121: 缺陷 51 防御 — Telemetry Configure 前点位缓存 + 批 32
- **缺陷 51 防御** (mass_151 假阴性候选机制): Emit 在 Configure 前/_writer=null 时静默丢点 → 改 pending ring (上限 32, seq 原序) + Configure flush + DroppedTotal 可见化计数。单测 2 (Emit-before-Configure flush + DroppedTotal 单调), 384 绿。
- **批32** (mass_171-175) 25/25 全绿 avg 3855tok (波动带)。
- AOT 0IL + 冒烟 ✓ (pending flush 在 AOT 下生效)。

### R122: 批 33 + 阶段趋势 (R116-R121 汇总)
- **批33** (mass_181-185) 25/25 avg 3597tok。批27-33 序列: 4024/4248/4106/3636/3656/3855/3597 — 治理后稳定 3400-4250 波动带, 无上行漂移。
- R116-R121 六轮累计: 缺陷 47/48/49/50/51 五连修 (创作意图拦截/bge 真链 env/Memory 体积预算/Workspace rel 比例化/telemetry pending 缓存), C11 prompt 808→608-656 稳态, 379→384 测试, mass_128 全量 16/16 (含 C14/C15/C16 隔离+pivot+回锚), AOT 三次 0IL 复验。

### R123: 多来源召回率专项 + 缺陷 52 (空 userId 落盘) + 批 34
- **召回率专项** (批29-33, 100 用例轮): WorkspaceFiles 3snip/轮 100% rel0.84 (主力); AgentContext 1snip/轮 100% rel0.90 (稳定); Memory 75% 命中 rel0.29 (缺陷49 质量换体积预期); SessionMemory 按需 r0.95; **UserTendency 冷启动 0 = 设计语义** (CalculateTendencyScore 只看最近 10 条 MinSampleSize 窗口, 近期无相关话题→confidence≤0.3 不注入; 100 条聚合画像 Python:25 正常积累)。
- **缺陷 52**: 空 userId 信号持久化到 ".json" 空文件名 (召回链永不读取) → UpdateTendencyAsync 入口+Persist 双拦。2 单测, 386 绿。
- **批34** (mass_191-195) 25/25 avg 4145tok (上行 1/3, C11 prompt 432-606 稳好, 上行在 completion 侧=glm 波动)。

### R124: AOT 重发布 (fix#52) + 批 35
- **AOT**: 0 IL 警 (缺陷52 后强制重发布)。
- **批35** (mass_201-205) 25/25 avg 4035tok → 波动计数归零 (批34 4145=1/3 未连续)。

### R125: 批 36 + 余额对账
- **批36** (mass_211-215) 25/25 avg 3778tok。
- **deepseek 余额**: 7.61 CNY (R120→R125 长跑零额外消耗 — 批测全走 glm 零价端点, 成本控制有效)。
- 批27-36 序列: 4024/4248/4106/3636/3656/3855/3597/4145/4035/3778 — 10 批均值 3907, 无上行漂移。

### R126: 输出纪律规则 8 (解释/分析类) + 批 37/38
- **规则 8** (R18 输出纪律扩展): 解释/分析类问题按「一句话结论 + ≤3 要点」结构, 300 字以内 — 打点驱动 (批36 C08 completion 860-1027 = 总 tokens ~25% 最大靶点)。
- **A/B 实证**: C08 completion 943 → 726 avg (-23%), content_len 266 字 ≤300 ✓; wall 30-48s → 31-38s。
- **批37** (mass_221-225) 25/25 3765tok; **批38** (mass_231-235) 25/25 3709tok。

### R127: AOT 重发布 (规则8) + 批 39 + 千轮报告
- **AOT**: 0 IL 警 (规则8 后强制重发布) + 冒烟 content_len=310。
- **批39** (mass_241-245) 25/25 avg 3671tok; **C08 completion 治理轨迹: 943 (批36) → 726 (批38) → 479 (批39, -49%)**。
- **千轮迭代优化报告**: docs/reports/thousand-round-report.md (PGO 方法论/52 缺陷台账/专项验证/D1-D5 动态打点 v2 策略/未完成事项/执行方案)。
- **README 双语**: 新增 README.md 中文完整版; README_EN.md 更新 (徽章 386/千轮 99.89%/R103-R127 能力段/验证基线/下一步)。

### R128: PGO v2 D2+D5 落地 (harness 层)
- **D5 对比基准自动化**: run_round.py 落盘前自动读历史 5 轮 (按 ts 排序), 计算 per-case 平滑均值 delta → 轮 JSON (`delta_tokens_vs_hist`/`delta_wall_vs_hist`), analyze.py 直接消费。
- **缺陷 53 (打点链自身)**: ①`[-6:-0]` 空切片 (-0==0) → delta 恒 None; ②字典序让 stability_* 老轮排最后 → 改按 ts 排序。
- **D2 KPI 健康带**: tokens/case ∈[500,950], wall/case ∈[12s,30s] — mass_251 首次捕获越界 (C03 4357tok/99s), 复跑 mass_252 in-band (3732tok/107s) = LLM 单轮波动, breach 只标记不判 FAIL (防误回退)。
- mass_251/252: 5/5+5/5 全绿。

### R129: D3 phase_timing + 缺陷 54 (assembly 20s)
- **D3 上线** (5 处 phase_timing): intent_ms/llm ms/recall_memory/recall_workspace/compress — 首战即发现 assembly 11-13s (C08/C11)。
- **缺陷 54 三层治理**: ①54a EmbeddingRouter 共享 bge 单例 (ConcurrentDictionary by modelPath|mode) ②54b GradientCompressor: Full(≥0.8)与 Rule/TitleOnly(<0.5) 档跳过 originalEmbedding (语义校验仅 SummarySentences 0.5-0.8 需要) ③54c EmbeddingFunction 每 call new → 共享后单进程单次加载。
- **战果 (mass_255 批测口径)**: assembly 210/245ms (-98%), compress <200ms, C08 wall 34.0→13.3s, 批 wall 94→65.6s (**-30%**)。386 测试全绿, AOT 0 IL 警 (NU1510 非 IL)。

### R130: 动态打点评测回滚策略主报告 (用户钦定)
- 新建 `docs/reports/dynamic-telemetry-eval-rollback-strategy.md`: 打点体系全景 (25 点位分层) + D1-D5 策略 + 明确评测方案 (批测入口/健康带/回滚机制: 真 FAIL 复跑 2 次或连续 2 批劣化>10% → git revert 点位与代码同 commit 原子回滚) + UserTendency 断链=主题第一靶点 + 迭代状态快照 (上下文丢失恢复入口)。
- run_round.py 落盘后自动镜像 eval/results/ (历史手工 cp 常漏)。
- AOT 重发布 (缺陷54 后铁律) ✓; mass_252-255 补镜像。

### R131: 迭代优化总体方案文档 (用户点名: 单独成文)
- 新建 `docs/reports/iteration-master-plan.md` (方法论总纲, 与主报告分工: 方法 vs 状态): ①点位新增五触发器 (T1 wall 疑点无点位/T2 breach 连批/T3 新功能无观测/T4 审计空白/T5 主题盲区) + 点位立项卡 (commit message 载体) ②点位探索两手段 (差分探查: 字段变异系数+wall 残差墙; 极端采样: 最长/最深/最快/最空四压力画像) ③测试数据源: 用例分类学现状 (负面 12% 目标 20%) + 七维入册检查 + 负面八类清单 (N1-N8, N8 画像派生程序化生成) + 四层数据源分层 ④跑测真实性五道防线 (过程证据链/阳性抽查/阴性探针红队自检/双模型交叉/RETIRED 诚实制度) + TRUTH-INCIDENT 响应 ⑤回滚原子性铁律 (点位与功能同 commit) + 三特殊情况 (打点开销/LLM 漂移/基础设施) ⑥每 5 批审计脚本化清单 + 节奏表 (轮/批/5批/月/50轮)。
- 主报告+千轮报告互链 master-plan (导航闭环)。推 c2f86c9→本次。

### R132: 批40 (mass_256) — eval/reports 机制上线 + K1 靶向启动
- **机制**: run_round.py 每轮自动追加 eval/reports/round-log.md (用户钦定: 跑测后输出数据记录); dry-run 验证 ✓
- **批40** (mass_256, quick 5 用例): 5/5 passed, 4291tok, wall 75.6s, KPI in-band (基准 5 轮); C06 0tok=expect.llm=false 本地执行器设计正确
- **准则入档**: master-plan §0-0 宪法八条 + §0-1 五 KPI 维度 (1cbbb07)
- K1 靶向: UserTendency 聚合断链 = R133 第一靶点

### R133: K1 被提问概率断链修复 (缺陷55: 置信度双断点) — 5 KPI 靶向第一战
- **断点A** (TendencyData.cs GetContextBiasAsync): 防覆盖逻辑 !ContainsKey 让历史高分 (0.341) 被当前查询低分 (0.2) 屏蔽 → avg 稀释 0.2 恒被 0.3 阈值拦截
- **断点B**: OverallConfidence 用 avg — 画像条目越多稀释越重 (信号质量与条目数成反比, 语义颠倒); 单主题用户反易通过
- **修复**: 历史与当前取 max (同信号两观测取强, 历史 0.8 降权保留) + conf 改 max-based + weak/strong_count 诊断 + tendency_bias 新点位 (立项卡 T5/K1)
- **实证**: 真机 'python api 测试' UserTendency 0snip→1snip/r0.8; 批41 mass_257 4/4 LLM 用例全通 (C06 本地执行器设计性无召回); 389 测试全绿 (+3)
- **K2 副产**: 3596tok vs 批40 4291 (-16.3%), KPI in-band

### R133b: 全仓测试 flaky 根除 (R133 引入回归的顺带修复)
- **症状**: 389 测试间歇失败 (实证 5/6 fail) — TelemetryPendingTests pre_boot_probe 断言丢失
- **根因**: AgentTelemetry pending ring 上限 32 太小 — R129 D3 后 ContextAssemblerTests phase_timing 打点 (≥27) + R133 tendency 写入 (15) 并行灌满 ring, Configure 前 Emit 被丢
- **修复**: ①ring 32→256 (产品运行 Configure 启动即调, ring 极少超 32; 放宽仅影响极端并发, 丢点计数仍可见) ②recall_tendency 打点加 bias!=null 守卫 (mock 测试零 Emit) ③TendencySignalFilterTests GetContextBias 用例改直接落盘构造 (0 Emit)
- **验证**: 389 测试 6/6 连续全绿; AOT publish 0 IL 警 + full-graph smoke OK

### R134: K4 SKILL 调用准确性盲区补全 (5 KPI 第 4 维度点亮)
- 新点位: skill_match (top1/level/precision/runner_up_gap/candidates 候选质量) + skill_trigger (no_hit/degrade_semantic/force 决策) — 立项卡 T5/K4
- harness: skill_match/skill_decisions 入轮 JSON per-case; K4 口径 = 期望 skill 用例的 force 命中率 + 泛查询误吸率 (degrade_semantic 频率)
- 批42/43 波折: sibling 会话并行 commit 覆盖工作区未提交 patch (K4 两度丢失) → 教训: 单仓多会话必须小步 commit; 批44 (mass_260) 5/5 4169tok in-band K4 数据首通
- K4 首批信号: 泛查询 top1=identity_statement (prec 0.37-0.43, gap 0.02-0.07) 全部 degrade_semantic 正确降级; C06 unit-convert level=2 prec 0.6 gap 0.18 强判别
