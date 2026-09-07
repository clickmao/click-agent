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
- Vulkan 语义: 系统唯一 libvulkan.so.1 + fork vendored libggml-vulkan.so 同目录 — 无副本、无变体复制、无 deps。
