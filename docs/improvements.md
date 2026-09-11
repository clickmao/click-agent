# AgentFramework 改进文档 (improvements.md)

> **记录规则 (2026-09-08 重梳)**: 顶部 = 最新版本, 逐版本向下递减; 每节格式统一
> (版本 / 日期 / 状态 / 主题 / 完成记录 / 基线)。v7.x 为历史遗留版本号体系 (v0.x 前身),
> 原始记录见文末「历史遗留」区, 详情走 git log。
>
> **⚠ 文档严谨性铁律 (2026-09-09 用户钦定, 长期有效)**: 凡【以文档为驱动的循环开发迭代方案】
> 中的文档 (README 双语 / api.md / architecture.md / CLI指令说明.md / improvements.md 等),
> 任何修改必须做**全文整体/大区域合法性校验** — 标题与内容对齐 (版本号、批次趋势行归属)、
> 数据时效 (测试数/批号/评测口径)、版本引用一致性、死链检查; **禁止只改局部不做整体校验**。
> 空间位置相邻但语义不同段的错挂 (如旧版本标题下挂新数据) 视同违例。

---

## R365 v0.21.0 Role 系统交付 + 凭据加密 + FrontendApi 鉴权 (批523 13/13, 提交 `7ed4031`)

- **用户指令 (逐字)**: ①"凭据静态加密 请用跨平台统一方案" ②"完善 6 个硬缺口" ③R360 "不做前置人格语料，倾向=对用户问题置信度的赏罚涌现" ④R361 "用对抗用例验证后有效在接近V2 并记得 role 可以外挂依据给 V2" ⑤**R363 "去掉roles目录相关，仅能外部挂载单文件且不可是明文，需压缩友好的快读快写可扩展结构，提供API读取修改写入 并实现 ① 推理中止→失败簇三件实现 ② 赏罚信号接 V2 主链（:1270 替换 llmResponse.Success）"** ⑥"全部提交github，并更新全部文档到当前项目状态"。
- **凭据静态加密 (R358)**: 新建 src/agent/CredentialEncryption.cs — **AES-256-GCM**（跨平台统一原语，AOT 全支持；不用 DPAPI/libsecret 分叉）；master.key 32B 落盘 600 权限；明文自动迁移（Load 兼容 + 首次 Save 即加密）；GCM 篡改拒绝。PromptPersistence 接入；6 单测。
- **Role 单文件 `.rbin` (R363, 用户钦定修订)**: 新建 src/agent.roles/RoleBinaryFile.cs（191 行）— 16B 头（magic `ARBL`+version+flags+压缩长度+原始长度）+ `AES-256-GCM(gzip(JSON))`；密钥=`data/master.key` 持久层级（跨会话可解/换机不可解）；未知 `x:` 前缀键读写往返保留（可扩展）；tmp+rename 原子写；Read/Write API。**目录方案废除**：RoleRegistry.cs 删（照 SkillRegistry 的 roles/ 目录包扫模式终弃），Program `--role` 改接 .rbin 路径、`--roles-dir` 删。实测 700B 文本 → **306B**；hex dump 仅见 magic + 密文（非明文实证）。
- **赏罚涌现倾向 (R360, 用户钦定非前置语料)**: CorrectionDetector.cs 两级判定 — L1 规则词面（"不对/错了/不是这个意思"等强模式，**0 token**，14 轮模拟拦 12/14）+ L2 微 prompt（**单字母 C/A/N 输出协议**，~140 tok/次，均摊 20.7 tok/轮，省 85%）→ RoleGrowthLedger.cs 域级 Beta 计数，confidence=(赏+1)/(总+2)（Laplace），**<0.4 先怀疑 / >0.7 信任 / 样本<5 观察中**。实证：docker 域 5 罚 0 赏 → 0.143 Distrust（"先怀疑"自动涌现）；git 3 赏 0 罚 → 0.800 观察中；跨会话重载保持。
- **推理中止→失败簇 (R364, "三件")**: FailureClusters.cs — 中止检测（超时 / token 超限 / **自证循环**：窗口 3 轮回复 trigram Jaccard ≥0.95 判原地打转）→ 问题指纹簇归类（落盘跨会话）→ **罚分 ≥3 前置注入**策略警告（先澄清/降级/诚实坦白）。Jaccard 修 `last.Count(prev.Contains)` 歧义为 `last.Count(t => prev.Contains(t))`。
- **R365 文档同步期审查（自查发现 3 真缺陷，已修）**: ①**前置注入实际未接线**——`RenderWarning` 有实现但 V2 prompt 组装处从未消费（"三件"只有两件在跑，属宣称与实现不符）→ 接入 Role 块（`message.Content` 指纹命中且罚分≥阈值 → 注入），无 role 时不进分支；②**簇键跨进程不稳定**——`string.GetHashCode()` 在 .NET Core 对 string 每进程随机化种子，落盘的 `failureClusters.json` 重启后键全失配 → "跨会话簇归类"静默失效（同进程测试测不出：`落盘重载_簇保持` 恰好骗过）→ 改 **FNV-1a 32bit 自实现**；③**指纹排序文化相关**——`List<string>.Sort()` 默认文化比较，同问题换 locale 得不同键 → 改 `StringComparer.Ordinal`。新增回归锁 `簇键_进程间稳定`（硬编码 3 键值，期望值由独立 Python FNV 实现交叉验证，非抄实现输出）。
- **赏罚接 V2 主链 (R364)**: CorrectionDetector 后台 Task（不阻塞响应）挂记忆回写区，`GrowthLedger.Record` + LLM 失败 → `FailureClusters.RecordAbort`；L2 判定走模型队列 ContextCompression 通道（微 prompt 隔离）。
- **无 role 门禁 (用户 OOB 校验令)**: 查实 2 处漏洞（纠正检测 Task 无 role 仍起 → 白烧 LLM token；失败簇仍写盘）→ 加门禁：`GrowthLedger == null` 整链失效 — 不起 Task / 不调 LLM / 不写盘 / 联想前置注入关闭（null 安全空返回）；无角色行为与 v0.20.5 一致。
- **对抗验证 (R361)**: /tmp/adversarial 30 例（判罚正例10 / 判赏正例8 / 误杀陷阱7 / 模糊灰区5）；首轮 23/30 → 修 L1 语境豁免（转述/假设/历史）+ L2 单字母协议 + max_tokens 自适应重试（deepseek-flash 是 reasoning 模型，思维链吃光 token 致 content 空）→ **30/30（判分题 25/25 = 100%）**；固化 CorrectionDetectorTests.cs 22 用例（脱 LLM，L1 规则 / L2 mock）。
- **FrontendApi 鉴权 + 限流 (sec2/sec3 部分)**: FrontendAccessControl.cs（共享 token：随机 hex 或 env 注入 / 令牌桶限流 / 并发上限）。
- **真机 E2E**: `agenthost --frontend-api 47819 --role skeptic.rbin` → 同对抗问题回复"前提澄清: 没有证据表明…"（人格从加密单文件加载，4.2s）✓；R355 TCP 47812 chat.send E2E（meta.ping→pong / "回复两个字:收到"→"收到" / 未知 api 结构化错误）。
- **基线**: **730/730 全绿**（729 + 1 新增回归锁 `簇键_进程间稳定`；R362 为 718）；AOT **13.75MB** 零 IL 警告；批 523（DS 主力首测）13/13。
- **诚实边界**: ①R2 能力绑定（Role 绑独立二级召回源）未实施；②`/role` 指令族未做（改 `--role` 启动参数 + `role.info` api）；③embedcpu 无关对 cos 0.90+ vs llama.cpp 金标准 0.18-0.23 差异未解（Q8_0 地板假设已证伪）；④sec2 鉴权仅 token，OAuth/mTLS 未做。

## R355/R356 v0.19.0 FrontendApi chat 域接通 + DS 主力切换 (批 523 13/13, 提交 `3f90e3c`/`6a33404`)

- **用户指令**: ①"若当前你通过API使用LLM服务是GLM请改成DS, ds-flash4.1" ②"② KPI token 口径决策 ③ FrontendApi state.snapshot 真实状态填充"。
- **R355 FrontendApi chat 域**: 新建 FrontendApiChatRouter.cs（chat 域异步 handler 持 IAgent，直通 ProcessAsync）；FrontendApiServer handler 签名升级 `(api, payload)`；Program 加 `--frontend-api <port>` 第三运行形态（TCP 常驻）。两处 AOT/契约级修复：payload 透传缺失（server→router 传 "{}"）、AOT 反射禁用下匿名类型序列化崩溃 → 手写 Utf8JsonWriter。真机 E2E 全通；677/677，AOT 13.4MB。
- **R356 DS 主力切换（二分实证）**: 修前真相 = **首选实为 GLM**（打分 GLM/DS 同 8 分，GLM 价格 0 → fitness×2+推理×3+编码×3-价×2 恒胜；models.yaml "首选"标注仅注释、代码不消费）。修 A：models.yaml 加 `priority`（DS=1/GLM=2），ModelSelectionPolicy 每低一档 **-5 分**压过 0 价优势；性能不敏感分支（压缩/标注）同锁首选；未声明=旧行为不变；6 单测含"未声明时 GLM 仍胜"回归保护。修 B（正名）：**`deepseek-4.1-flash` API 名不存在（400）** → 官方支持名 = **`deepseek-flash`**（另一合法名 deepseek-v4-pro），直调 200 model echo 确认。终验：GLM 坏 key 下 chat.send **一次成功、零 401、零兜底、零 warn**。683/683。
- **R356-b embedcpu 数值审计（llama.cpp 源码对照）**: curl 拉 llama-model.cpp / llama-graph.cpp / src/models/bert.cpp / ggml.c 逐项对照 — 前向 8 项对齐 bert.cpp（gelu=tanh 变体、无 causal mask、scale、残差位置全 ✓）；**修正 pooling：mean→CLS**（BGE 官方 1_Pooling 实证 cls_token + pooling_type=2 是转换器默认值不可信）；WordPiece 去 ▁ 前缀（BERT 词表无 ▁，词="word"/子词="##sub"）→ **相关对 cos 0.8372 → 0.9634** ✓。683/683，推 `a8fe11f`。
- **llama.cpp 金标准对照（决定性实验）**: ghfast 镜像 clone llama.cpp 11s → 构建 llama-server（新版 embedding CLI 已移除，改走 `/v1/embeddings`）→ 同 `bge-q8.gguf` 加载：**mean pooling 无关对 0.17-0.19，CLS pooling 0.18-0.23 vs 我们 0.90+** → **Q8_0 噪声地板假设证伪，前向仍有差异（未解）**；同句前 16 维 cos 0.79。
- **R356-c**: KPI token 口径重锚（tokens_per_case 上界 1300，批 523 实测 1836 带外待定夺）+ state.snapshot 真实状态填充。
- **基线**: 683/683；批 523 = **13/13**，1836 tok/case，8.0s/case（DS 主力首测）。

## R353/R354 v0.20.5 模型通道精简 + bge 本地 CPU 最小推理 + LLamaSharp 全拆 (批520/521/522)

- **用户指令**: ①"去掉项目内本地加载本地llm与官方llm相关功能…仅保留api调用能力" ②"deepseek4.1flash首选 glm5.3flash次选 保留gpt6默认 其余model预留配置移除" ③"去掉llama后仅限cpu 不要onnx 少量代码或成熟库" ④"bge即便用最小实现也请本地cpu异步跑" ⑤"脚本互动若业界无先例则删" ⑥"跨平台vector实现"。
- **通道精简**: 删 LocalLlamaCaller/LocalInferenceAdapter/ILocalInference/OfficialModels/OfficialKeyStore/--official-key; ChannelScheduler 三通道→单 Remote; models.yaml 52→3 (deepseek-4.1-flash 首/glm-5.3-flash 次/gpt-6 默认配置); core.yaml model gpt-4→gpt-6; SkiaSharp 渲染器删 (仅 SVG)。
- **LLamaSharp 全拆** (vendored fork 445MB 目录+nuget 缓存+csproj 引用+native 复制段): BgeEmbedder/SharedEmbedderRegistry/BgeEmbeddingProvider 删; qwen/bge-small-en gguf 删 (bge-q8 保留 — embedcpu 引擎)。
- **embedcpu 新项目** (纯托管零原生依赖, ~470 行): GgufModel (GGUF v3 最小解析+Q8_0/F32 反量化+f16 手写位运算) / WordPieceTokenizer (21128 词表最长匹配+## 子词回退+中文按字) / BgeCpuEmbedder (4 层 BERT forward, TensorPrimitives SIMD, mean-pool+L2, 惰性双检锁, EmbedAsync=Task.Run 异步)。
- **真 bug (R353b 修)**: Q8_0 反量化 Data.ReadByte() 返回无符号 int → 负权重变正大数 → cos 恒 1.0 嵌入无区分度; 修 = (sbyte) 显式转换; 修后与 python 参照逐位一致。
- **R353c 跨平台向量化** (用户检查点): 剩余 4 处标量循环全 TensorPrimitives 化 (embedding 查表/attention 加权/SoftMax/LayerNorm 仿射) — 跨平台自动 SSE/AVX2/AVX512/NEON。
- **R354 eval 同步**: LOCAL_DISABLED 死开关退役 (本地通道本体已删, R107 泄漏源不存在); D4 gate 不再依赖 BGE_MODEL (--embed 走 llm-service), 自动探测 agenthost 路径注入 LLM_SERVICE_BIN。
- **真缺陷 (520/521 双 0/13 负样本如实)**: 清 bin/obj 后未重建 host 而 run_round 用 --no-build → CLI 不存在全 case 650ms 空回; 重建后 CLI 手验 glm-5.3-flash 正常回复。教训: 清 build 产物必须立刻重建 host (run_round --no-build 依赖磁盘二进制)。
- **脚本互动调研归档** (R352-d): 8 家主流 agent 均无"脚本执行中主动问 CLI"先例, 主导模式=单向事件流 → 本项目 ScriptPluginRunner 单向事件流判定保留 (script-interaction-research-R352.md)。
- **基线**: 677/677 绿; AOT 13.4MB 0 IL 警告; bge CPU 热嵌入 ~26-90ms; 验收批 522 (host 重建后)。

---

## R343 v0.20.0 LLM 服务独立进程 — llm-manager / worker 架构 (批516 quick-13 验证中)

- **用户指令**: "将llm服务写成单独进程, 以免新CLI重新加载LLM到显存内, 最好使用小而完善的框架完成"; 纠正 "仅是新增本机 llm host 而非全面修改当前框架llm使用流程"; 钦定策略 "一个是 llm-manager 进程, 一个是实际 llm-service-host; **卸载直接杀 llm-service-host 就好了**"。
- **现状代码事实**: BgeEmbedder (llamalocal) 惰性加载 bge-q8 26MB (加载后 RSS ~157MB 实测), 每 CLI 进程经 DI 新建 (ServiceCollectionExtensions L226); LLamaEmbedder.Dispose() 只释放 Context **不释放 _weights** (LLamaSharp L54-57 实测) → 手工卸载需穿透 SharedEmbedderRegistry (无卸载 API) + 引用计数, 复杂易漏; CLI 生命周期 = REPL while(true) (L296) 或 -q 单次, 多实例并存。
- **架构**: `llm-manager` (轻量常驻, 0 模型, 不随 CLI 生死) 对外 UDS 透明代理 → lazy spawn `llm-service-host` worker (真 bge); 卸载 = kill worker (OS 回收全部 native 内存, 绕开手工释放/引用计数)。ping 由 manager 直答 (探活不触发加载); 双启保护 .manager.pid/.worker.pid; 客户端 .startlock 原子抢占; SIGKILL 后孤儿 worker 由新 manager 清理。
- **卸载判定 (纯函数, 单测矩阵)**: `ShouldUnload = workerUp ∧ inflight==0 ∧ availMb>0 ∧ availMb<floor(512) ∧ cliCount==0` — **不按时间** (用户钦定: 内存充足常驻); **空闲长连接不阻止卸载** (实测缺陷修正: 原含 conns==0 导致 CLI 长连接永久阻止卸载); 读不到内存 (非 Linux) 保守不卸。
- **跨平台 (用户 OOB "/bin/sh 跨平台怎么办?")**: 产品代码零 shell — spawn 用 `Process.Start`+`ArgumentList`, 卸载用 `Process.Kill(entireProcessTree:true)`, 存活判断 `Process.GetProcessById`+`HasExited`; daemon 自写日志 (env LOG, 替代 sh 重定向); UDS 跨平台 (Win10+ AF_UNIX); /proc/meminfo 非 Linux 优雅降级 (Windows GlobalMemoryStatusEx 待办)。
- **验收**: 新增 LlmServiceTests(9)+LlmManagerTests(7) → **全量 661/661 绿**; AOT publish 13.6MB **0 IL 警告**; 真机 E2E: ①manager READY 0 模型 → ②首请求 lazy worker (RSS 157684KB, bge 512 维) → ③kill -9 worker → ④下请求自动重拉 (pid 2659546→2659594) + manager 存活 → ⑤阈值拉满+无 CLI 实例 → worker 被卸载无残留。
- **诚实边界**: ①RemoteEmbedder 尚无框架内调用点 (opt-in 集成 = v0.20.1 P4-a); ②worker 仅服务 bge embed, 本地 LLM 推理未 worker 化 (P4-b 评估); ③Windows 内存探测未实现。

## R338 v0.17.3 P10 锚词 Span 化收尾 (批288 quick-13 13/13)

- **立项**: improvements.md 下轮候选 — R333 (v0.16.4) 完成 P10 中文 2/3/4 字窗 long-key 零分配后遗留 **English 段未动** (function-map-R326 P10: 压缩热路径锚词提取)。可选性: c 收口/dormant 退役均需用户裁定 → 本轮唯一可执行候选。
- **现状代码事实** (src/agent/contextassembler/ContextAssembler.cs, ExtractAnchorWords L1006+): CJK 窗 R333 已零分配; English 段仍 `Regex.Matches(content, "[A-Za-z]{3,}")` + 每匹配 `m.Value.ToLowerInvariant()` = **每 English 词 2 次短串分配 + MatchCollection/Match 分配**; 压缩热路径每超限 snippet 触发一次 (代码/英文片段词数×2 分配)。
- **修法**: English 提取 → `Regex.EnumerateMatches(content.AsSpan())` (零 Match 对象) + **≤7 字符词 8bit/char long 键零分配计数** (ASCII 字母 `|0x20` 即小写; 8×7=56bit 键域无歧义; 字母编码无中间零字节 → decode 移位归零即末字节; 复用栈槽免 CA2014); >7 字符词 string 兜底 (长词稀有); 两路 distinct 首见登记 enOrder (枚举序=match 序=内容首见序), 计数毕按登记序解码 count≥2 候选入 words — 与原实现 (English match 序先、CJK len-major 后) **同插入序**, count 相同下稳定排序输出全等。
- **验收**: **624 单测绿** (+5 ExtractAnchorWordsEquivalence InlineData: R333 随机语料英文词全 ≤7 字符未覆盖 >7 兜底路径 — 补 >7 重复/短长混合首见序/7-8 边界同 count 保序/>7 大小写折叠/7 大写折叠×8 string 交替); AOT publish agenthost 13.5MB **0 IL 警告** (仅预存在 CS0649/CS0169/xUnit1030); 批288 (round 515) quick-13 **13/13** tok/case 1806 (KPI_BREACH 带外 — C19 重案 8023 tok 已知方差同 R337/R331 判型, 通过率主口径零回归; 改动为压缩路径纯函数不进 LLM 链)。
- 收益: English 主路径 (≤7 词, 绝大多数) 每匹配 2 短串+MatchCollection → **零分配**; >7 仅兜底; 与 R333 CJK 段合拢 P10 "单遍扫描 + Span/字典" 全部建议。
- 诚实边界: 片段级锚词缓存 (function-map P10 建议) 未做 (收益需跨 snippet 重复片段真实命中分布, 候选中); >7 词每 occ 仍 Substring+ToLower 与旧版同 (未回退)。
- 下轮候选: c 收口 (/schedule 持久化 + 外部 cron 挂钩 + 定时 skill — 需用户裁定) / 片段锚词缓存 (需命中分布) / RAGConfig 内联 hash 收敛 (需加 rag→vectormemory 引用) / dormant 退役 (需裁定)。

## R337 v0.17.2-b/c 脚本插件协议 + 条件定时 (批287 quick-13 13/13)

- **立项**: 用户钦定 (执行层自需脚本一律 py 编写 → CLI 验证 py 正确后交插件服务执行; 明确对接协议: 定期反馈/结束前返回/长执行心跳) + plan docs/plans/v0.17.2-activity-script-plan.md §2/§3 (b 脚本插件协议 + c 条件定时, 依赖 a 的 IsOtherAgentBusy 条件原语)。
- **协议层** (src/agent.skills/): ScriptPluginProtocol.cs — **JSON Lines 事件流** `{"type":progress|checkpoint|heartbeat|done|error,"ts","msg","data"}`; done/error=权威终态 (以事件为准, 进程退出码仅兜底); done 回填 summary + data.outputs(产物路径); 非 JSON/未知 type 行=调试噪声 (忽略计数); ts 容忍 epoch 秒/毫秒; ScriptEventStreamParser 状态机 (时钟注入): 事件驱动活性 → >2×heartbeat 无事件=疑似挂起判定。PythonScriptValidator.cs — **py_compile 验证门** (真实 `python3 -m py_compile`, 进程级 AOT 安全): 失败=拒绝执行 + 教训 `script-invalid:<name>` (ExecutorLessonMemory 频率加权)。
- **执行器**: ScriptPluginRunner.cs — 验证通过 → task-json 落盘 data/script-plugin/tasks/ (源生 STJ 序列化, 用后即删) → `python3 script --task-json <file> --heartbeat-secs N` (PYTHONUNBUFFERED 强制流式) → 事件流消费 → 活性监控 (疑似挂起打点一次不杀) → 总超时杀进程树返回失败 → 进度/心跳计数打点 + 结束回填。条件定时: ConditionalScriptScheduler.cs (v0.17.2-c) — "如果当前没有其他任务存在则 XX 后执行 Y": 延时到期 → 轮询其他 agent 忙 (接线方注入, 默认 ActivityService.IsOtherAgentBusy 自身排除) → 空闲即执行/忙重试至 give-up; 重试/放弃窗口全走配置委托, 延时/时钟可注入。
- **接线**: /schedule-run <延时秒> <py路径> [目标描述] 本地指令 (LocalCommandRouter + V2 特判臂 0ms 拦截, 坏 py 拒绝+教训落盘 ExecutorLessonMemory.Default; v1 延时上限 60s)。
- 验收: **619 单测绿** (+18 ScriptPluginTests: 解析终态/噪声容忍/秒容忍/挂起活性重置/真实 py_compile 好坏/真实 python3 子进程 done 回填+error 权威+协议违例+静默超时挂起观测+坏 py 真实教训 store 落盘/条件调度 空闲执行·忙拒绝·验证拒绝·取消 — 注 R336 文档 597 为其时计数口径, 含 Theory 行差异); AOT publish 0 IL 警告 (仅预存在 NU1510 包引用提示); **E2E 真机 AOT host 双场景**: /schedule-run 0 好脚本 → ✅ 完成 (200ms 事件3 心跳1, 产物回填 data/script-plugin/outputs/) / 坏 py → ⛔ 拒绝未执行 + `script-invalid:e2e_bad.py` 教训真实落盘; 批287 (round 514) quick-13 **13/13** tok/case 1641 (低于近4轮 1672-1811, KPI_BREACH 带外系 C19 重案 7680 tok + LLM 方差已知现象, 通过率主口径零回归 — 本改动为惰性本地指令+未触发库, 不进 LLM 链)。
- 诚实边界: /schedule-run 为轮内阻塞式 ≤60s v1 (长延时交互语义、跨重启持久化、Hermes cron 挂钩、定时任务 skill 面 = 下轮候选, 交互语义待用户裁定); 脚本产物默认写 data/script-plugin/outputs (改用户文件走 v0.17.1 staging 属接线方职责, 本期未接)。
- 下轮: c 收口 (/schedule 指令面持久化 + 外部 cron 挂钩 + 定时 skill) / P10 锚词 Span 化 / dormant 退役 (需用户裁定)。

## R336 v0.17.2-a 活动任务注册表 (批286 quick-13 13/13)

- **立项**: 用户钦定 (获得所有激活窗口活动任务/其他 CLI 状态/job_id 通知/"无其他任务则 X 后执行"原语) + plan docs/plans/v0.17.2-activity-script-plan.md (a 活动注册表 / b 脚本插件协议 / c 定时 skill 分期)。
- **ActivityService** (src/agent/activity/): 每活动 CLI 进程心跳文件 data/activity/<pid>.json (AtomicFileWriter; 退出 finally ClearActivity + 崩溃由 TTL 兜底); 条目含 pid/window(env AGENTFRAMEWORK_WINDOW)/job_id(env AGENTFRAMEWORK_JOB_ID)/agent/任务摘要/心跳; 查询扫目录; 过期 TTL **90s** (E2E 实证教训: 心跳为轮级非定时器, LLM 单轮 30-60s, 10s TTL 误清在跑实例); IsOtherAgentBusy(自身排除) = "无其他任务" 条件原语。
- **接线**: V2 OnProcessAsync 轮首 Heartbeat(message.Content); Program.cs finally ClearActivity (守护轮并行补); /activity 指令 (Known+switch 臂+V2 特判 0ms 渲染列全部激活 agent: pid/win/job/status/心跳龄/任务)。
- 验收: **597 单测绿** (+6 ActivityService: 注册查询/过期清理/自身排除/多实例无串扰/渲染含 job_id/损坏容忍); AOT 0 IL 警告; **E2E 双实例真机**: 实例 A (win-A/job-A-test/长任务) 运行中 → 实例 B /activity 看到 A: pid/win=win-A/job=job-A-test/任务摘要 ✓ (首版失败=TTL 10s 误清, 改 90s 复绿); 批286 (round 513) quick-13 13/13 tok/case 1811。
- 下轮: v0.17.2-b 脚本插件协议 (py 验证→插件服务执行, JSON Lines 事件流/heartbeat/done 约定) + c 条件定时 (IsOtherAgentBusy 已就绪)。

## R335 v0.17.1 离线变更 + 用户审批 (批285 quick-13 13/13)

- **立项**: 用户钦定 (Q1-Q7: CLI 产出需审批/VS Code 编辑保护/不能停/落盘不占真实地址/下次打开恢复/过期周期/前端取得/多批合并) + plan docs/plans/v0.17.1-staged-approval-plan.md (逐问题设计)。
- **存储**: src/agent/staging/ — StagedFileStore (批次 content 原样落 data/staged/<batch>/<n>.content **不占用真实文件地址**; index.json 原子写; 恢复=新实例读 index; 过期三阶段 TTL→expired(内容保留可取回)/TTL×2→reclaimable/显式 cleanup 物理删 — 不静默丢); ChangeBatch/StagedItem (基线 sha256 快照模型); StagingSha (IncrementalHash AOT)。
- **审批**: ApprovalController.Apply = LockedFileWriter.WriteIf **锁内基线比对** — 用户/编辑器在批次创建后改过目标 → 冲突拒绝绝不覆盖 (Q1 VS Code 场景机械保证); 多批 approve all 按创建序, 后批基线过期 → partial 报告人工; 冲突教训入 ExecutorLessonMemory (staging-conflict:<file> 频率加权)。
- **指令**: /staged [--json] /staged diff <id> /approve <id|all> /reject <id> /cleanup (Known+switch 臂+V2 特判渲染 0ms 本地拦截, /skills 族同款); --json 单行输出供前端 (Q5: 状态文件 data/staged/index.json 也可直读)。
- **验收**: **591 单测绿** (+10 StagedApproval: staging 落盘不占真实地址/恢复/apply 成功/用户编辑冲突拒绝/新建语义/多批顺序+冲突/reject/过期三阶段/--json/损坏容忍); AOT 0 IL 警告; **E2E 三场景真机** (AOT host): /staged+diff 查询 ✓ → 模拟 VS Code 编辑 → /approve ⚠冲突未覆盖 (文件保持 USER-EDITED-IN-VSCODE) ✓ → 恢复基线 → /approve ✓已应用 1 项 (AGENT-PRODUCED-CONTENT 落盘); 批285 (round 512) quick-13 13/13 tok/case 1765。
- 下轮: v0.17.2 窗口&任务感知 (OOB 钦定) + 脚本增强计划 (OOB 钦定)。

## R334 v0.17.0 执行层稳固化 T1-T4 (批284 quick-13 13/13)

- **立项**: 用户钦定 (2 agent 同时写 1 文件族问题 → 工业化 IO 防御) + plan docs/plans/v0.17.0-executor-hardening-plan.md。
- **T1 跨进程锁**: src/agent/execution/FileLocking.cs — FileLock (.lock 文件 FileShare.None=Unix flock LOCK_EX, 持有者崩溃内核自动放锁, 锁文件含 pid); AtomicFileWriter (tmp+Flush(true)+Move overwrite 原子); 删除竞态防护 (释放后校验锁文件仍属自己 pid 才删)。
- **T2 占用者检测**: OccupantDetector — 快路径读锁文件 pid; 主路径 /proc/locks (解析实证 Linux 6.8: "1: FLOCK ADVISORY WRITE <pid> <dev>:<inode> 0 EOF", pid 是含 inode 段前一项, 非固定 index); stale 判定 /proc/<pid> 不存在。
- **T3 教训临时记忆**: ExecutorLessonMemory — 失败→原因→临时记忆, **频率加权增长** (count1 摘要/count≥3 补方案/count≥8 补上下文), 24h 降级 7d 移除 (时钟注入), 手写 JSON 持久化原子写 (踩坑: JsonEncodedText.ToString 带引号致双引号 JSON → 手写 Esc; Save 拼接缺引号 → Esc 包引号)。
- **T4 接入**: TaskCharter.Save → WriteIf (同 Id 状态推进覆盖/异 Id 让位 — KeepExisting 会让 TaskCharterTests 失败: 自身 planning→done 被挡, 教训=自身生命周期推进 ≠ 异主冲突); GuardrailMemory.Save → 加锁 Overwrite; 冲突结构化 + Record 教训 + executor_write/executor_lesson 打点。LockedFileWriter.WriteIf (锁内条件覆盖, 无 TOCTOU)。
- **设计踩坑 (FileShare)**: FileShare.Read 实测同进程第二 Open ReadWrite 仍成功 (不互斥, 测试实证) → 必须 FileShare.None; FileOptions.DeleteOnClose Unix=打开即 unlink → 破坏锁文件可见性。
- 验收: **581 单测绿** (+11 ExecutorHardening: 双锁互斥/stale 接管/活锁不误删/占用者报告/原子写无残留/KeepExisting 让位/教训频率升级衰减/持久化往返/损坏容忍/8线程120行并发追加零丢失); AOT publish 0 IL 警告; 双进程 flock 竞争 smoke (60/60 全成功零交错 — smoke 判定假警报已诊: split 后段天然无分隔符); 批284 (round 511) quick-13 13/13 tok/case 1672。
- 下轮: v0.17.1 离线变更+用户审批 (OOB 钦定, plan 已建 docs/plans/v0.17.1-staged-approval-plan.md)。

## R333 v0.16.4 P10 锚词提取 long-key 零分配 (批283 quick-13 13/13)

- **现状**: ExtractAnchorWords (ContextAssembler.cs L1000) 中文 2/3/4 字全滑窗每位置 3 次 Substring 短串分配 — 压缩热路径 (每超限 snippet 一次, 大片段 ~65K CJK chars → ~200K 分配/片段)。
- **修法**: CJK 全在 BMP (UTF-16 单单元 ≤0xFFFF) → 窗口编码 long key (每 char 16bit 顺序拼, 低位=窗首; 起点必 CJK 使高 16bit 非零、每 len 独立字典 → 键域无歧义) 零分配计数; 仅 count≥2 候选解码 string (AddDecoded 固定 len 正向移位)。
- **语义等价证明**: ExtractAnchorWordsEquivalenceTests 10 测 — 反射调 private 新实现 vs 内联旧 Substring 算法: 6 已知样本 + **40 轮随机混合语料 (CJK/ASCII/标点/emoji/超长词) 全等**。中途设计漏洞自捕: while(k!=0) 解码无法定 len + 低位反序 → 改 3 独立字典分 len。
- 验收: **570 单测绿** (+10); AOT publish 0 错误 0 IL 警告; 批283 (round 510) quick-13 13/13 tok/case 1712 (vs R331 1875 / R332 1889 — 更低, C19 重案方差内; pass-rate 主判据干净)。

## R332 eval per-case isolation hardening (批282 quick-13 13/13)

- **根因**: run_round.py 清理只在轮级 (R81), case N 落盘会话记忆 (data/sessions/cli-*_memory.json, CLI 每进程读+追加写) + RAG index 泄入 case N+1 新子进程 → C14 isolated=None 两次 12/13 flake (rounds 506/506b; R331 A/B: 同 binary standalone 2/2 PASS + OLD 13/13 PASS, 失败仅现整批窗口 = cross-case leakage 时序累积)。
- **修法**: case 循环内每 case 前清 sessions + RAG 落盘 (setup 键仅 charter/guardrails 且 fixture 在 run_case_with_setup 内应用 → 清理先于 setup 安全; repl 型 case 内部多轮共享进程状态不受影响)。
- **教训 (执行层)**: execute_code 内 Popen 起批测会被 cell 300s timeout kill 连坐 (半批 16/16 PASS 无汇总即死) → 长批必须 terminal background=true + notify。
- 验收: 批282 (round 509) quick-13 **13/13** (tok/case 1889 vs R331 1875 同水平; C14 PASS); 508 半批 16/16 (被连坐前)。AOT 无需重发 (eval 层改动)。下轮候选: P10 锚词 Span 化 / RAGConfig 内联 hash 收敛 / dormant 退役 (需裁定)。

## R331 v0.16.3 RAG 落盘裁剪摊销 (P12, 轮507 13/13 验收)

- **背景**: function-map-R326 P12 — RAGConfig.PersistDocument (L231-262) 每 append 后无条件 `File.ReadAllLines` 判 512 行裁剪, 超限 `WriteAllLines(lines[^512..])` → 库过 512 后**每消息整读+整写** (~512 行恒定浪费 O(库大小) 文件 IO); 增长期 1→512 每 append O(n) 读 = O(n²) 累计。每用户消息热路径 (对话库逐轮涨)。
- **改动**: 常量抽取 `RagPersistMaxLines=512`/`RagPruneInterval=64`; `Interlocked` 计数 `_persistAppendsSincePrune`, 仅每 64 次追加整读一次判裁剪, 超限重建保留最新 512 (`lines[^512..]` 语义不变)。文件瞬时上限 512+63 行 (有界松弛), 每次裁剪终态与逐次裁剪内容集一致 (追加+保尾裁剪单调); 文件被外部删除/重建后计数器最多漂 64 次 append, 下次裁剪整读实测自愈。
- **验收**: **560 单测绿** (+3 RagPruneAmortizeTests: 700 文档 → 文件行数 ∈(512,575] 且保最新裁最老 / 新实例重载只恢复幸存者+追加继续正常 / 小库 50 行零裁剪); AOT publish 13.2MB **0 IL 警告** + CLI 冒烟; 批测轮 507 quick-13 **13/13 零回归** (tok/case 1875 超旧健康带 = C19 8523 级重案 + LLM 方差, R329/R330 同判型; 通过率主口径零回归)。
- **C14 整批 flake 调查 (非本改动引入, 留档)**: 轮 506/506b 均 C14 isolated=None FAIL (12/13, tokens≈1000=未 spawn 隔离链); 同代码单跑 C14 ×2 PASS (isolated=True score=2) + 轮 507 整批 C14 PASS + 旧代码 86a4f13 A/B 整批 (506old) 13/13 C14 PASS → 失败集中于 05:00-05:15 窗口, 与代码无关。归因: TopicRelevanceEvaluator 是确定性规则器 (R308), C14 方差来自**输入**: turn1 锚/goal 的 LLM 提取质量 + **跨用例 tendency/画像泄漏** (run_round R81 只轮级清 RAG+会话记忆, case 进程共享 tendency 文件 → 前序 C07/C13 输出随 LLM 方差变化, 泄漏进 C14 锚提取 → 弱锚/无锚路径不隔离; 失败回复实测引用前序用例 "Web API 项目/代码推送" 上下文坐实泄漏)。→ 下轮候选: eval 隔离按 case 清理 tendency/画像状态 (harness 硬化)。
- 收益: 库过 512 后每消息文件 IO 整读+整写 → 每 64 消息一次 (64× 摊还); 增长期读 O(n²)→O(n)。
- 下轮候选: P10 锚词 Span 化 / C14-in-batch 隔离硬化 (eval 按 case 清 tendency) / RAGConfig 内联 hash 收敛 (需加 rag→vectormemory 引用) / P4 二段-前缀否定 (需真实命中分布数据) / dormant 退役 (需用户裁定)。

## R330 v0.16.2 工作区召回流式化 + 整轮字节预算 (P4 首段, 批282 13/13)

- **背景**: function-map-R326 §4.1 P4 — ContextAssembler.RecallFromWorkspaceAsync 每文件 `ReadAllTextAsync` 整读 (≤200KB/文件 × ≤300 文件 → 单轮理论最多 ~60MB 文本读入 + `Split('\n')` 全行数组数千短 string 分配/文件), 无整轮读取预算; 文件/编码类意图每装配触发 (recall_workspace 打点监控), 中热。
- **V1 流式化**: 整读+Split → `StreamReader` 逐行 (`FindKeywordLineRankedStreamingAsync`), 峰值内存 = 单行。**语义与字符串版完全一致 — 无前缀截断, 文件尾部命中不丢** (35KB 深处命中单测锚, 前缀否定需真实命中分布数据, 未做, 候选); 单行命中计数抽 `CountKeywordHitsInLine` 双版共享防漂移 (FindKeywordLineRanked 字符串版保留, WorkspaceRelevanceTests 反射锚)。
- **V2 预算化**: 满分档 (5 hits) 命中即停读 (原整读后 break 无 IO 收益); 整轮字节预算 `WorkspaceRecallBytesBudget`=4MB (static 非 readonly — 单测反射注入小预算验证截断路径), 超预算停止扫描剩余文件 — 与 Take(300) 同哲学 (按修改时间降序, 丢最旧文件; R30 已声明"扫描窗口内召回质量"边界); 空文件跳过。
- **验收**: 557 单测绿 (+4 WorkspaceRecallBudgetTests: 文件尾部 ~35KB 关键词命中不丢 / 预算 2KB 截断只留最新文件 / >200KB 大文件跳过 / 多词最佳行 R118 相关分语义); AOT publish 13.2MB **0 IL 警告** + CLI 启动冒烟; 批测 505 quick-13 **13/13 零回归** (tok/case 2004 超旧健康带 = C19 8523/C14 4291/C13 2616 重案 + LLM 方差, 同 R329 判型 — 通过率主口径零回归, hash/bge 路径不受影响)。
- 收益: 工作区召回峰值内存 整文件→单行 (大文件数千行数组分配消除); 单轮读取上限 理论 ~60MB → 4MB 预算窗口。
- 下轮候选: P10 锚词 Span 化 / P12 RAG 裁剪 O(n)→摊还 / RAGConfig 内联 hash 收敛 (需加 rag→vectormemory 引用) / P4 二段-前缀否定 (需真实工作区命中分布数据) / dormant 退役 (需用户裁定)。

## R329 v0.16.1 HashEmbeddingProvider 双实现统一 (T-B4 遗留收口, 批281 13/13)

- **背景**: v0.15.3 计划 T-B4 遗留 — 三份 hash 语义并存: vectormemory 384 英文版 (EmbeddingProvider.cs) / llamalocal **256 硬编码版** (EmbeddingRouter.cs, bge 缺失兜底) / RAGConfig 内联 (RecallRateTests 锁定, 不动)。两 class 注释均自称 "R58 语义" 但实现矛盾 (256 vs 384 维度分裂、英文-only vs 中文标点、单桶覆盖 vs 3-seed 摊开)。
- **V1**: vectormemory.HashEmbeddingProvider 升级为统一唯一实现 — RAGConfig.Tokenize 同族分词 (lower + ASCII 标点全切 + ascii↔非ascii 边界切 R44 中英混写 + 中文 2-gram 滑窗 R6) + 3-seed 摊开桶分配, dim 可配默认 **384**; 不做预归一化 (全部调用方 CosineSimilarity 自归一, 与 RAGConfig 内联一致)。
- **V2**: llamalocal.HashEmbeddingProvider (256) **删除**; EmbeddingRouter fallback → vectormemory 统一版 (384)。grep 全仓无残留。
- **验收**: 553 单测绿 (+5: 维度 384/中文多桶/R44 混写召回/R6 无空格召回/EmbeddingRouter fallback 指向统一版); AOT publish 13.2MB **0 IL 警告** + 冒烟; 批测 504 quick-13 **13/13 零回归** (tok/case 1877 超旧健康带系 C19 重案 8877 + LLM 方差, 逐案对比 C03 -1076/C13 +1199/C19 +1563, hash 路径批测不参与, 非本改动引入; 批279 1687 亦在旧带外 R322 已知)。
- 收益: 降级/AOT 形态 RAG 与记忆整合向量空间统一 (384), 中文召回从整句 1 桶升级为 2-gram + 边界切 (R6/R44 语义覆盖)。
- 下轮候选: P4 工作区召回预算化 / P10 锚词 Span 化 / P12 RAG 裁剪 O(n)→摊还 / RAGConfig 内联 hash 收敛 (需加 rag→vectormemory 引用) / dormant 退役 (需用户裁定)。

## R328 v0.16.0 skills 引擎完整落地 (批280 37/37 验收)

- **CLI 外挂 skills** (用户钦定 v0.16.0-a): `--skills-dir <目录>`(可多次)/`--skills-blacklist <id或目录名>`(可多次)/`--skills-file <单SKILL.md>`(可多次) → env 钩子传 DI → ServiceCollectionExtensions 合并注册; 外挂同 SkillId 覆盖内置 (Register 字典后写胜); RemoveById 精确 id+包目录名双匹配。E2E: 外挂 my-ext-skill 进注册表 (7 个激活)。
- **运行时动态过滤** (v0.16.0-b): SkillRegistry.SetActiveWhitelist/Blacklist (volatile HashSet, All getter 应用, null=清除) — 循环任务内动态指定可匹配范围。
- **/skills 指令族** (v0.16.0-c): /skills 查询当前激活 (id/版本/类型/触发词)、/skills-only /skills-exclude 动态过滤 — Known+TryRoute switch 三臂+V2 特判渲染 (Dispatcher.Registry 只读暴露)。**根因教训: Known 集合加了但 switch 臂没加 → 落 _ => NotCommand 送 LLM (模型幻觉能力表); SkillsCommandRouteTests 测试先行逮住**。
- **skills 格式统一**: 6 包全部规范 frontmatter (name/description/version/type/keywords; image-gen 补缺失→knowledge_hint; normative 显式化)。
- **critic-rules 语言无关化 2.0.0**: R01-R08 按语义定义 (堆分配/串拼接/async void/阻塞/吞异常/判空/浮点比较/资源释放) + C#/Python/Go/Rust/Java 映射; config 同步去 domains:[csharp]。
- 验收: **548 单测绿** (+SkillsCommandRouteTests 2); 批280 全量 37/37 (mass 503, tok/case 2075 = 全量口径含 C19/C16 重案+诱饵族, 非回归); AOT publish 0 错误。撞号险情 1 次 (误取 502 与批279 冲突, R257 协议 30s 内 kill 换 503, 旧文件零损失)。
- 下轮候选: R-3 HashEmbeddingProvider 双实现统一 / P4 工作区召回预算化 / P10 锚词 Span 化 / P12 RAG 裁剪 O(n)→摊还 / dormant 退役决策 (需用户裁定)。

## v0.13.x (2026-09-08~09) — 底座能力与收敛环 (已落地, R205-R288)

### 主题 (用户钦定): 渐进式探索 / 思考链收敛 / 兜底粘性路由 / 格式修复收敛环 / 底座能力长期观察

### ✅ 完成记录 (真实执行)

**v0.14.0 输出侧经验闭环 + v0.15.1 任务路由 (R318-R322, 2026-09-09)**
- OutputCritic (R318): 8 条 C# 反模式静态规则, 14 测; plan 三版演进 (孤立设计→用户纠正"回顾既有牵引体系"→master-plan S/M/D 盘点+第四环定位)
- SelfCritic (R319, 用户钦定方向): LLM 自审=人类经验检索 (常见反模式分布内可靠); 三失效模式 (过度批评/幻觉批评/分布外) 对策=逐字子串锚+机制解释强制+Anchor 过滤; 单源自评绝不直接进生成上下文
- FixMemory (R319): 修法记忆 (反模式→修法), 来源秩 human_review > metric_delta > llm_self_confirmed; R0071 误信全仓清零 (用户纠正: 非本项目编号)
- CriticPipeline (T2c): 静态=确认态 / LLM 交叉=去重 / LLM 单源=观察态不入上下文
- T2d 接线: DataSourceType.FixMemory + ContextAssembler 分支 + K1 全隔离剔除 (R302 对齐); 装配接线 3 次插错教训=多块编辑用 git diff 不做行号算术
- TaskCharter (R322, v0.15.1-a): 章程 schema + 任务进行中新输入三态路由 (supplement→pending / pivot→归档 failed / isolate→既有链); E2E 三态实证 + 归档快照修正 (Archive 先 Save 终态再 Move)
- 数据: 批263-265 全绿 (12/12 quick-12); 538 单测

**v0.13.3 牵引收口与重构事故自捕 (R309-R313, 2026-09-09)**
- 缺陷 72 修复 (R309): executive 直达补 intent 打点 (C04/C06 intent=general 复现; llm_calls=0 保留=executive 本质无 LLM); init 键教训第 3 次 (R142/R151/R309) — topic_* 键加错 init dict, 批254 KeyError 杀批
- 牵引阈值 env 化 (R309): AGENTFRAMEWORK_TOPIC_STEER_THRESHOLD (默认 2)
- explore 执行方式修复 (R310): AOT apphost framework-dependent 无 DOTNET_ROOT 秒退假跑 → dotnet dll 对齐 run_round; 24 案真跑 A 0.167/B 0.722 (+56pt 历史最高); B 轮 3 viol 定性=must_not_contain 与引用来源的判定张力
- 否定围栏双向化 (R311): 前 40ch + 后 20ch (后置否定 "并非光合作用" 兜住); 3 形态离线验证; 批256 负样本零回归
- 无锚轮词面 verdict (R312): R308b 删词面退路致无锚会话牵引失效 → else 分支纯词面模式; 但**重构事故**: 有锚隔离执行链误删 → 批257 C14 首败 (isolated=None) 实锤 → R313 恢复
- 衔接副词精修 (R313): "再讲 X" 单字"再"误判指代 → 裸衔接词 + 无复合指代在场 + 词面偏离成立 → veto 不适用; 💡 提示链恢复 (SteerHint ×2)
- 欠账补齐 (用户点名): 批 188-217/218-247 两段归档 (R312), archive-first-then-retire 制度
- 数据: 批255 11/11 1228/case; 批256 11/11 1161/case; 批258 11/11 1003/case (C14 复绿)

**v0.13.3 合并判定与复查收口 (R307-R308, 2026-09-09)**
- L1 轻牵引 (R307): 连续偏题 ≥2 轮 → 回复尾追加衔接提示 (答案本体零改动); 追加位置必须在区段路由**之后** (ProcessAsync 会重写 Content — E2E 实证)
- TopicRelevanceEvaluator (R308): 隔离+牵引合并判定 API — 一份 verdict 三路消费 (Isolate→subagent / SteerHint→牵引 / Normal); 分级 veto (指代词绝对 / 短询问在实体非零重叠时)
- 复查三轮 (用户钦定): ①首查 4 缺口 (隔离点直调 Check / steering 独立打点 / verdict 双算 / 旧注释) ②二查 3 缺口 (run_round 零消费 topic_relevance / K1 双开关语义 / no-anchor 观测盲区) ③三查围栏双脚本同源 — explore_eval 窗口 20→40ch + 词表补 "不能" (TC-F06 离线双向 4/4) + suspect 降级语义统一
- **缺陷 72**: skill executive 直达路径 (L481 early-return) 绕过 LLM 后全部打点 — C04/C06 llm_calls=0 结构性根因 (批244 起即如此, 此前误标瞬态)
- 数据: 批250 11/11 1172/case; 批253 11/11 1061/case; 499 单测; 探索增益口径澄清 (R288 可达 11 案 +18pt / R289 全 24 案 +39pt, README 用后者)

**v0.13.3 宿主执行与真机 E2E (R272-R288, 2026-09-09)**
- 思考链宿主执行全线打通 (R286): HostExploreExecutor (URL GET digest/页内链接发现≤5/目录文件路径穿越防护) + V2 RunThinkChainAsync (播种→4s/4步→首败即停→回注); 真机 think_chain {seeded:1, steps:1, ms:46}
- **探索 KPI 正信号** (R288/R289): 可达 URL 24 案 A/B — hit **0.278→0.667 (+39pt) ↑7 ↓0 零回归**; wall B≤A (成本不可见); explore_eval 独立跑测程序 + 本地夹具 8 页 + A/B 开关 AGENTFRAMEWORK_EXPLORE
- LinkRegistry 激活链 (R276/R282): 三信号 (锚定/稀缺出链/路径递进) ≥3 激活+父链保护; 真机 link_activation {urls:5, activated:5}
- think-memory 持久化 (R283): Save/Load (STJ source-gen 流式零反射) — 新进程 recall hit top_sim 0.9701 (data/think-memory.json)
- 微步骤宿主链 B2 (R274): gate=IsolatedMicro → 微问询 → 回注 ≤200tok/条; E2E 2860ms failures=0
- 压缩失败防护 D1-D4 (R262-R265): 异常隔离/数字+URL 哨兵 (链接文档 URL 键全档 100%)/降级链/熔断器; 多轮 3 场景 (A=35/B=12/C=22 压缩事件 sentinel 全 0)
- 多轮 driver 场景参数化 (R278): MT_SCENARIO=A/B/C; 10 轮 repl × 压缩遥测 17-35 事件全健康
- 缺陷台账新增: 跑测程序回复区误报 (R273 修: 回复区提取+否定围栏) / build 单项目不刷 host bin 依赖 (R274 教训) / probe stdout 管道满冻结 agenthost

**v0.13.0**
- 渐进式探索: ExplorationConfig (每上下文区/文本/URL/目录最大探索步 + 全局预算 + URL 深度) + ExplorationPlanner (优先级队列; 用户例: 上下文内 URL > 上下文外目录) — 7 单测
- 思考链 T3: ComplexityGate + EvidenceScorer (多源对比, 单源封顶 medium) + ThinkMemory RAG 联想 (相似问题优先历史高置信链接, 引用后 +0.05 置信, 负样本降权, 30 天衰减) + ThinkChainSession — 12 单测
- RAG 数据文件用户指定: CLI `-rag <path>` / 任务内 `/rag` / env 三入口 (真机三态验证)
- Baseline 换血 (用户钦定): L0-L5 分层; XL 大上下文族真机验证 (XL-01 实测 7010 tok, 回复含全部 ground truth; XL-04 10750 tok); ContextBudgetGate (WARN 6000/HARD 9000, 防抖首次跨越放行修复 — python 复现抓 bug) — 6 单测

**v0.13.1**
- 兜底粘性路由: FallbackConfig (config 开关 + cost_quality 性价比序 + 逐个兜底 + 回复校验, MinReplyChars=2 由 Router 测试实证) + Router 逐个兜底链 (fallback_attempt/fallback_verify_fail 打点) + StickyRouteMemory (三门判定: 相似+意图+实体指纹; 最近成功优先 0.01 容差; TTL 72h) — 11 单测

**v0.13.2**
- 格式修复收敛环: IFormatRepairPlugin + JsonRepairPlugin (栈感知括号修复; 用户破损 JSON 实例回放通过) + FormatRepairLoop (①块内检测→②查找→③校验→④本地修复→⑤LLM 循环; max_llm_rounds 可计数; 技能-校验矩阵硬规则) — 13 单测

**v0.13.3**
- 底座能力长期观察 (用户钦定, 入 master-plan §0-2): 压缩 audit (`--compression-audit`, 104 篇多样态 ground-truth × 4 档 × 3 级别)
- A3 关键句保护修复: TakeSentences 评分保留因果/指令句 — SummarySentences 因果/指令保留 0-20% → 单样式 100% / 多样态 99% (keys) / 85% (指令, 无标点样式待修)
- 429 感知调度: 限流跳过同模型重试直切备 (省 ~1000 tok/次重发)
- token-breakdown 每批观测行 (prompt/history/completion)
- 微步骤隔离设计 A6 (阈值门控, 更正2: 未达阈值走常规; 触发率基线 0%)

**缺陷修复 (本段)**: 真缺陷 65 (重试/切备成功路径 llm_call 打点缺失→429 后 token 全丢, 批187 假性 KPI_BREACH) / 66 (文本请求备选落视觉模型成本倒挂) / 67 (Text 能力硬过滤, cogview 误入文本备选) / 68 (C17 断言脆性 → neg_context_markers 推测围栏, 双向回放验证)

### 📊 基线
- 测试: **468/468 全绿** (404 → 468, 含探索 7/思考链 12/兜底粘性 11/格式修复 13/预算门 6/视觉族 3)
- AOT: publish 0 IL 警 (多次重发布); 批测: 批 174-217 带内 (600-1250 tok/case), full-23 23/23
- 文档: CLI 指令说明三表重构 (会话指令/本地命令/启动参数); docs/ 全量审计 (6 文档归档, 断链 0)

---

## v0.12.0 (2026-09-08) — 视觉理解 / 渲染插件 / 收敛环 (已验收)

### ✅ 完成记录 (真实执行)
- **视觉理解链**: CLI `-img` → Message.ImageAttachments → data URL base64 → glm-5.3-flash v4 端点; text-only 模型自动重路由 + coding 端点改写 (真缺陷 63/64); OpenAIMultimodalMessage 双形态 DTO (string|parts[], AOT-safe 手写 converter)
- **图像渲染插件体系** (用户钦定收敛环服务化): IImageRenderPlugin 契约 + SkiaSharpRenderPlugin (默认 PNG, 边缘选项 `-p:DisableSkiaRenderer=true` 停编) + SvgTextRenderPlugin (零依赖兜底) + ImageRenderPluginRegistry (HasRenderer=false → 跳过后续环节); LocalSvgRenderer DSL (rect/circle/line/text, XML 转义, 栈感知)
- **收敛环 E2E**: LLM 生成 DSL → 渲染 → 5.3-flash 视觉校验 → FAIL 重生成 → PASS (真机一轮 PASS: DSL 1039ch → SVG 843ch → 校验 6/6, 6.4s)
- **能力矩阵**: models.yaml 25/25 模型 capabilities 回填; CogViewClient 保留 (生成路径按用户钦定 R210 弃用)
- **验收**: T-V01~04 视觉用例族 full-23 23/23 (含负样本诱饵识破: 模型拒绝"右下角苹果"假预设); 四问真机复证; 基线 docs/archive/reports-archived/v012-acceptance-baseline.md

### 📊 基线
- 测试: 415+ 绿 (视觉 DTO 5 + 渲染器 3 + 插件 4); AOT 0 IL 警

---

## v0.11.0 (2026-09-06) — 统一命令协议 + 三传输 + Skill 脚本执行

### ✅ 已完成 (真实执行)
- **agent.io 统一命令协议**: `AgentCommand` 信封 (@cmd name key=value 行协议, 百分号转义手写编解码 — 零依赖 AOT 安全) + `AgentCommandWriter/Reader`; AgentReportReaderBase 加 Command 事件分类
- **三种传输**: Console.IO / 共享内存 (文件-backed mmap 环形区, 背压可见) / TCP Socket (跨机)
- **LogRouter 双通道**: thinking/输出指令同时镜像 IChatboxSink + @cmd
- **SkillScriptRunner**: SKILL.md 包 scripts/ 真进程调度 (python/bash/node PATH 探测; cwd=包目录沙箱; 环境变量白名单; 超时杀进程树; 脚本 @cmd → AgentCommandWriter 转发)
- **SkillDispatcher 接线**: executive 无显式 entry → 包脚本自动执行
- **性能修复 (sync-over-async 清剿)**: ModelQueueRouter.OnTransientFailure → async 链; TriggerMatcher.MatchAsync; ContextGradientCompressor.CompressCoreAsync
- **模型目录 6 → 18**: +Anthropic/Google/xAI/Moonshot/Qwen/DeepSeek v3.2/OpenAI/GLM-4.5 — 全部公开牌价, /model verify 可校验

### 📊 基线
- 测试: **351/351 全绿** (+10: 命令协议 6 + 脚本执行 4)
- AOT: publish 0 IL 警; /model list 18 模型真机确认

---

## v0.10.0 (2026-09-06) — Yamlify 换库 + Token 统计/余额联动 + Skill 语义

### ✅ 完成记录 (全部真实执行)
1. **YAML 解析换 Yamlify 1.8.0** (MiniYaml 重写为门面): AOT 零 IL 警; `TryGetTopLevel` 修复顶层列表键真 bug; API 签名不变 → 5 消费者零改动
2. **Token 使用统计 + 余额联动** (TokenUsageService): 真实 API 同步 → 本地累计 → 阈值再同步; 余额不足切模 + flags 提示; `/token stats` 全 JSON
3. **Skill P3 语义匹配接 bge** (TriggerMatcher): 词面全未命中 → bge 余弦 ≥0.45 疑似判定; 失败静默回退词面
4. **官方端点可配置代理** + **统一输出收口** (host 8 处 Console → IOutputSink; 库内零 Console 直写) + **/forecast 指令** + **/model list 序号选择** + **LocalLlamaCaller DI 修复** + **版本号统一 15 csproj → 0.10.0**

### 📊 基线
- 测试: **341/341 全绿**; NativeAOT publish 0 IL 警 (agenthost 12MB ELF); AOT 冒烟 4 项通过; GitHub 推送 387bfb1

---

## 历史遗留 (v7.x — v0.x 前身版本号体系)

> 以下为 v0.x 统一编号前的历史记录, 原文保留; 详情见 git log 与 docs/changelogs/CHANGELOG-v7.14.md。

### v7.15 (2026-09-05) — 十节点全落地
十节点: ①Skill 调度 P1 ②模型队列与意图选模 ③日志四通道 ④上下文梯度压缩 ⑤影子计划 ⑥问询打通 ⑦会话恢复 ⑧公开配置读写 ⑨agent.io 协议库 ⑩能力插件接口。需求四项: ①官方通道混合调度 ②agent.io ③会话中断恢复 ④公开配置读写。基线: 276→325 测试全绿 / AOT 0 IL 警 / 双冒烟通过。

### v7.14 (2026-09-05)
EvidenceGate→ClarificationBatch 接入 V2 主链 / vulkan setenv 双写 / SessionMemory 滚动 / AgentProfile 动态学习 / CapabilityScanner 重构 / 目标锚免压缩 / 面板全 JSON。基线 218/218。
