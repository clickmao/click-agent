# R480 验收台账: agent.recall 测试面 (13 项)

状态: 未通过 (11 FAIL / 2 PASS) — 2026-09-16, `dotnet test src/agent.recall.tests`
本文件是缺陷清单的权威落盘处 (对话会被压缩, 此文件不丢)。

## 已修 (本轮真机验证)
- 库编译 rc=0 / 0 Warning / 0 Error (修 6 处: FindTerm 键编码经 RecallKeys.PathKey、DeleteByKey 契约、
  RecallConstants.FpMagic、RecallSegmentSearcher totalDocCount 命名实参、MemoryReport().TotalBytes ×4)。
- **OOM 根因 (16 项失败的主因)**: `RecallIndexMeta.Read` 用定长 i64 读 ngram/minTok/maxTok/maxTokens/
  rangeCount/segCount/docs/tomb, 而 `Write` 侧写的是 varint ⇒ p 错位 ⇒ rangeCount 取到垃圾 ⇒
  `ranges.Add` 无限增长 (RecallFormat.cs:211)。已改 varint + fail-closed 验界 (TryVar/计数上限/长度上限)。
  修后测试总时长 2m12s → 697ms, OOM 归零。
- `RecallFingerprint` 写 `fingerprints.bin.tmp` 前未建目录 ⇒ DirectoryNotFoundException。已补 CreateDirectory。

## 未修 (按根因分组, 这就是剩余工作量)
| # | 失败项 | 报错 | 推定根因 |
|---|---|---|---|
| D1 | ResidentBytes_DoNotScaleWithDocCount | `truncated term tops in seg.meta` | **段级 meta 同类错位**: RecallSegmentMeta 读写不一致 (写 varint / 读定长) |
| D2 | BlockChainBeyondFirstBlock (期望 400) / BlockSkip (期望 10) / WandTopK (期望 10) | 值不等 | 与 D1 同源 (term tops 截断 ⇒ 块链/WAND 结果少) |
| D3 | FindsDocumentByPhrase | Collection was empty | 检索零命中; 需先排除 D1 后复测 |
| D4 | CorruptSegmentHeader_FailsClosed | 未抛 RecallFormatException | 段头损坏未 fail-closed (缺 magic/长度校验) |
| D5 | Update_AddsModifiesDeletes_AndPrunesUnchangedDirs | `index.meta not found: <dir>/index` | updater 打开的索引目录未被 Build/Create 写出 index.meta |
| D6 | Links_In_Content_Are_Extracted_Stored_And_Returned | IndexOutOfRangeException | `RecallLinksFile.Read` 越界 (与 Write 的 count+1 偏移表索引不一致) |
| D7 | TaskState_Is_Durable_And_Feeds_Recall | IndexOutOfRangeException | 同 D6 (ReadLinks 路径) |
| D8 | TokenizesIdenticallyRegardlessOfFileLikeSuffix | ["alpha","cs"] vs ["alpha.cs"] | 点号是否算词字符: 由 `RecallTokenizerOptions.IsWordSymbol` 决定 — **口径待定, 禁改全局默认凑绿** |

## 纪律
- 禁止改测试断言凑绿: D8 必须先定口径 (点号不作为词字符, 因为路径/文件名后缀不是语义) 再动实现或测试。
- 每项修完必须重跑全量 13 项, 断言执行数 > 0 (R454 形式门禁假绿铁律)。

## R481-B: 点号口径 —— 已按统计判定结案 (用户令「需要我裁定的全按统计学规律则优」)
器具 `eval/recall/period_policy_probe.py`(2500 真实文件 / 300 真实查询: stem/全名/相对路径 各 1/3):
| 臂 | hit@5 | hit@10 | MRR@10 | 查询词数 | postings | 词表 |
|---|---|---|---|---|---|---|
| A 点号算词字符 | 0.2800 | 0.3133 | 0.2045 | 4.61 | 841,137 | 76,507 |
| B 点号是分隔符 | **0.2867** | 0.3133 | **0.2092** | **3.87** | **839,003** | 76,506 |
判定: hit@5 差 +0.67pt ⇒ z=0.182 / **p=0.856 不显著**; 而 B 查询词数 **-16.05%**、postings **-0.254%**。
规则(预先可陈述): **质量无统计显著差异时取成本更低者** ⇒ 取 B。已落 `RecallTokenizerOptions.WordSymbols = "_-/+#"`(去掉 '.')。
注意: D8 测试项在改默认值后**仍未通过** ⇒ 测试侧疑似显式传了 WordSymbols 或走另一条判定分支, 下一轮一行即确认(禁改断言凑绿)。

## R481-D: D9 交替核验（测试面 12/13 → 14/14，2026-09-16）

状态: **通过**。`dotnet test src/agent.recall.tests/agent.recall.tests.csproj -c Release` ⇒ **Failed 0 / Passed 14 / Total 14**（rc=0，949 ms，`Skipped 0`；trx 结果行 14）。

| 项 | 修前（本轮实测） | 修后（本轮实测） |
|---|---|---|
| 用例 `Update_AddsModifiesDeletes_AndPrunesUnchangedDirs` | **FAIL**（改写态 `second.Modified == 0`，期望 1） | PASS |
| 套件 | Failed 1 / Passed 12 / Total 13 | **Failed 0 / Passed 14 / Total 14** |
| 断言执行面 | —（1 用例红，不构成假绿） | trx 结果行 **14**、`Skipped 0`（0 行 ⇒ 假绿判红，见器具 C2） |
| 库编译 `dotnet build src/agent.recall -c Release` | 0 warning / 0 error | 0 warning / 0 error |

根因（承 R481-C 定位，本轮实修）: 目录剪枝条件 `Directory.GetLastWriteTimeUtc(dir).Ticks <= currentStamp` 对**纯内容改写**不可见 —— 改写文件内容**不更新父目录 mtime** ⇒ 整目录被剪 ⇒ 文件级 `(size, mtime)` 比对根本没发生。

改动（3 处，全在 `src/agent.recall/`）:
1. `RecallFingerprint.cs` 指纹头 stamp 编码改为 `((ulong)stampBase << 1) | (DirsPruned > 0 ? 1UL : 0UL)`；读侧 `lastScanTicks = (long)(ticks >> 1)` 与 `prevScanPruned = (ticks & 1UL) != 0UL`；头解析 fail-closed（`RecallFormatException("truncated fingerprint header")`）。`BackfillHeader` 形参 `long → ulong`（回填处不得再截断）。
2. `RecallFingerprint.cs` 剪枝开关 `bool pruneEnabled = options.PruneUnchangedDirs && store is not null && !prevScanPruned;` ⇒ **上轮剪过 ⇒ 本轮强制全量核验**（readdir + stat，不读内容）；idle 轮仍剪枝（保 `DirsPruned >= 1`）。
3. `RecallUpdater.cs` 报告新增 `VerifiedAllDirs` / `PrevScanPruned`（核验轮 `DirsPruned == 0` 且 `VerifiedAllDirs == true` **单列**，不冒充「无变化」）。

新增回归用例 `Update_AlternatingVerify_CatchesSameSizeContentRewrite`（刻意**等字节长度**改写: `钾`→`铷`，size 不变 ⇒ 只有文件 mtime 变）锁三条: ① 核验轮 `DirsPruned == 0` ∧ `VerifiedAllDirs == true` ∧ `Modified == 1`；② 下一轮**恢复剪枝**（`DirsPruned >= 1`，交替成立）；③ 单字查询 `铷` 命中 / `钾` 落空（证明索引内容真的换了，而非只翻计数）。

器具: `python3 eval/recall/r481/check_r481d9.py` ⇒ `verdict=PASS`（C1 源码派生读写契约成对 / C2 真跑 trx 读数 14 行 / C3 核验轮语义锁存 / 变异负控 **3/3**: NC1 反转剪枝门、NC2 删 stamp 左移、NC3 删标志位解码 ⇒ 全部翻红）；产物 `eval/recall/r481/verdict-r481d9.json`。

真值边界（不冒充）: ① D9 只保证**最多滞后 1 轮**被捕获，**不保证**任意改写当轮可见 ⇒ `VerifyMode.Hash` / 周期全量核验**未实现**；② 旧格式（未左移 stamp）store 的实读行为**只推理未实测**（推理: ticks 量级下 LEB128 恒 9 B ⇒ 左移前后字节数不变 ⇒ 旧值被读成更早 stamp ⇒ 只多核验不误剪）；③ 「核验轮 `DirsPruned == 0`」属**语义变化**，已单列字段；④ 本面**未入链** ⇒ 对主线「用户一轮 tasks tokens −30%」**无贡献**。

## R481-A: 【探索】跨文件/跨URL 精准度基线 (已跑, 见 prereg_r481a.json)
6647 文件 / 20155 条自带地址: 解析率 0.8508(G1 FAIL) / 悬空 0.1492 / **相对引用落地 0.2718(G3 FAIL)** /
**76.11% 文件零地址, per-file p50=0(G4 FAIL)** / 跨 URL 2720 条 unreported / 仓根相对落地 16965。

## R481-C: 测试面工程收口 (2/13 → 12/13, 2026-09-16)
状态: **未通过 (1 FAIL / 12 PASS) — 不认通过**。修复 7 处根因 (均为读写契约不一致 / 越界 / 未 fail-closed, 无一处改断言凑绿):

| # | 位置 | 根因 (写侧形态 vs 读侧形态) | 证据 |
|---|---|---|---|
| F1 | `RecallFormat.RecallIndexMeta.Read` | 写 varint 读定长 i64 ⇒ 游标错位 ⇒ `rangeCount` 垃圾 ⇒ `ranges.Add` 无界 | OOM 16 → 0; 2m12s → 0.4s |
| F2 | `RecallFormat.RecallSegmentMeta.Read` | 同类错位 (8 字段) ⇒ `topCount` 垃圾 | `truncated term tops` 消失; `empty postings region` 连带 |
| F3 | `RecallPostings.Flush` | 词表记 **词表内偏移** 而非 **postings 偏移** | `PostingsOffset` 指向词表 ⇒ 读越界 |
| F4 | `RecallLinks.Read` | 读完 count varint **未推进游标** ⇒ 首条链接长度=count | `links record truncated at doc 0/1` |
| F5 | `RecallUpdater` | 首次更新对不存在的索引直接 `Open` ⇒ 必须能 `Create` | `index.meta not found` |
| F6 | `RecallTokenizer` | 长度 < ngram 的 CJK 段 (如孤立「钾」) 不产出任何 token ⇒ 单字查询零命中 | `Search("钾")` 空; 已加 `FlushShortRun` |
| F7 | `RecallFormat.DocLength` | lens 表头 12 B (magic8+count4), 读侧按 4 B 偏移 ⇒ **整体错位 2 项** | BM25 分数漂移 3.4675 vs 4.0058 → 修后逐位一致 |

契约保证: F1/F2/F7 修后**文档长度/词表/段元数据三者与写入端逐位一致**; F3/F4 走 fail-closed 抛 `RecallFormatException`/`RecallCorruptionException`。

**剩余 1 项 (D9): `Update_AddsModifiesDeletes_AndPrunesUnchangedDirs` 第 379 行 `second.Modified==1` 实际 0。**
因果链 (已定位到机制, 非猜测): 扫描的目录剪枝条件 = `dir.mtime <= 上次快照 stamp`; **改写文件内容不改变父目录 mtime** ⇒ 第三次更新把该目录整目录剪掉 ⇒ 文件级 (size, mtime) 比对根本没发生。证据: 第二次 (idle) `DirsPruned >= 1` 且 `Dirty == false` (剪枝生效); 改写后文件尺寸 +12 B 仍报 Modified=0 ⇒ 唯一可能是目录被剪。
修法设计 (下轮实施): 指纹头 stamp 低位记为「上轮曾剪枝」; 上轮剪过 ⇒ 本轮该目录**强制核验** (列表+stat, 不读内容) ⇒ 内容改写最多 1 轮后被捕获; 交替策略下 idle 轮仍剪枝 (保 `DirsPruned>=1`), 删除类变更因目录 mtime 变化天然可见。真值边界: 纯内容改写对目录 mtime 不可见 ⇒ 任何「仅按目录 mtime 剪枝」的实现都存在该盲区, 需 `VerifyMode.Hash` 或周期性全量核验兜底 (**当前未实现**)。

## R481-E: 器具归档物可复现化 + 台账卫生（2026-09-16）

1) **归档物确定性**：`check_r481d9.py` 原先把 `dotnet test` 的 stdout 尾部原样写进 verdict（`tail`，内含**绝对路径**与 `Duration: N ms`），且 trx 落**仓内** `eval/recall/r481/results/` ⇒ 每重跑一次就改字节 ⇒ 与 registry 的 `frozen` pin（`artifact_sha12` 取 **HEAD blob** 的 sha12）天然不符：工作区重跑一次即失配（本轮实测 pin `aacb931b8029` ≠ 工作区 `dd80fad72cb0`）。
   修法：掐掉路径前缀 + `Duration: <ms>` 归一；trx 改落**仓外**临时目录（`$TMPDIR/r481d9-results`，运行前清目录）。
   读数：连跑两次 ⇒ verdict `sha256[:16] = 38d71089389acc10`，**两次逐字节一致**（DETERMINISM=OK），且 `verdict=PASS`（C2: rc=0 / result_rows=14 / failed=0 / passed=14 / D9 用例 Passed）。
   出库：删除 `eval/recall/r481/results/r481d9.trx` —— (bytes, sha256) = (19889, `0506ba3c77a571acc19aa3b966d5bc11ec4dbf1feff71fc14ec3123d637df4e0`)。无信息损失：解析出的计数与 D9 用例名已固化进 verdict 归档物，trx 可由器具重跑复现。
2) **台账卫生（bind_evidence 归属漂移）**：`bind_evidence.py --apply --round R481` 会把**全部**已覆盖行的 `audited_by_round` 刷成 R481（其最小 diff 判据把该字段也算进「派生内容」）⇒ 实测 147+/122- 行级 churn，其中 **96 行除 `audited_by_round` 外逐字段相同 = 纯归属漂移**（把 R478/R479 的审计戳改成 R481）。
   处置：`eval/recall/r481/repair_registry_attribution.py` 逐行回退这 96 行到 HEAD 值（写前 `SER_ASSERT` 逐字节复现 + 写后逐行核 scope 一致 + 读回；幂等，二次运行 `IDEMPOTENT=OK`）。**保留 6 行真重派生**（R478×3 / R479×3：`live/worktree-only` → `frozen/archived-per-round` + 真 pin，因其证据已入库且工作区未改）。churn 由 147+/122- 收敛到 **51+/26-**（= 新增行 + 6 行重派生 + `updated_round` + 尾换行）。
   未修：工具本身「换轮号必刷全部行」的判据缺陷 ⇒ 下轮候选。
3) **registry**：149 → **150 行**（新增 `r481.recall-d9-alternating-verify`；`updated_round` R479 → R481）。尾部**换行 1 B 修复**：原文件缺尾换行 ⇒ `bind_evidence` 的序列化器自检 `SER_ASSERT` 会 fail-closed 拒写（本轮实测 rc=3）；按其自身契约补 1 B，语义零变化。

## R481-E（本侧独立复核 + G2 相对地址解析，2026-09-16）

**角色切分**：D9（交替核验）由 cron 兄弟会话 `cron:9a97763d5fcd`（07:42–07:45）实施；本侧 `R481-E` 不采信其对侧自述，逐项自跑复核后，再实施 G2（相对地址解析）。

### E1 独立复核（全为本侧自跑读数）
| 项 | 命令 | 读数 |
|---|---|---|
| 测试面 | `dotnet test src/agent.recall.tests/agent.recall.tests.csproj -c Release` | rc=0 / **Failed 0 / Passed 14 / Total 14** / 576 ms |
| 库编译 | `dotnet build src/agent.recall/agent.recall.csproj -c Release` | rc=0 / 0 warning / 0 error |
| D9 器具 | `python3 eval/recall/r481/check_r481d9.py` | rc=0 / verdict=PASS（NC1–NC3 突变体全部被抓） |
| 断言未放宽 | `RecallModuleTests.cs:379` `Assert.Equal(1, second.Modified)` | **原文保留**，未改断言凑绿 |

### E2 G2 实施：显式相对引用按「引用方目录」解析（产品面）
- 面：`src/agent.recall/RecallLinks.cs` — 新增 `ResolveReferrerRelative(candidate, referrerPath)`（纯字符串代数，不触磁盘）与 `Extract(..., string? referrerPath = null)`；**只改 `./` 与 `../` 开头的显式相对引用**。
- 接线：`src/agent.recall/RecallIndexWriter.cs:70` 传入 `doc.Path`（文档自己的根相对路径）。
- **不改写面（防回归）**：根相对（`src/agent.recall/RecallIndex.cs`）与绝对 URL **保持原样** —— 根相对是 R481-A 实测的主力成功通路（root-fallback 16,965/20,155），改写即回归。
- **fail-closed**：`../` 层数多于引用方目录深度（越根）⇒ **原值返回**，不猜目标。
- 测试：新增 `Relative_References_Resolve_Against_Referrer_Directory`（含越根负例）⇒ `agent.recall.tests` **15/15 / rc=0 / 455 ms**（14 项旧用例零回归）。

### E3 诚实边界
- **G3 的 0.2718 属语料侧读数**（Python 代理面），产品面这一改动**尚未**在语料上重测 ⇒ **不得**宣称 G3/G1 已达标；下轮须以产品侧器具（`agent.recall.bench` 增度量模式）或同语义双实现交叉核对后再上报。
- 未提交、未 push（`PUSH_PAUSED`）；`src/agent.recall*` 仍为 untracked。

## R481-F: 语料侧重测 —— 源码派生的规则端口（2026-09-16，承计划 §7「G3 口径须重跑取得」）

**起因**：R481-E 实施了显式相对引用的解析基准改写（`ResolveReferrerRelative`），而 R481-A 的旧端口 `eval/recall/links_probe.py` 是**手写规则**：① 候选受**后缀白名单**约束（语言相关）；② 把**无 `/` 的裸名计入相对档**；③ 根兜底用 `lstrip("./")`（`../x` 会被剥成 `x`）。产品规则与之已**静默漂移** ⇒ 旧读数不能拿来给新基准下的 G3 定值。

**器具**：`eval/recall/links_port_r482.py`
- **规则源码派生**：7 组常量由 `src/agent.recall/RecallLinks.cs` 正则派生（开关 / `MaxLinkChars=512` / `MaxLinksPerDoc=64` / schemes / `IsAddressChar` 字面量集 / 尾部标点集 / 最短长度 3 / 相对前缀 / 越根 fail-closed 分支），任一派生失败 ⇒ **rc=3 弃权**（不入红绿）；并带**形状机检**（字面量必须单字符、必须含 `/` 与 `.`、相对前缀必须恰为 `./`+`../`）——本条由本轮实测逼出：首版抓错 span 得到**空字面量集**，端口把 `src/x.cs` 拆成无 `/` 的碎片，静默少报 2/4 条。
- **期望值取产品自身断言**：从 `RecallModuleTests.cs::Relative_References_Resolve_Against_Referrer_Directory` 派生（输入 / 引用方 / 期望计数 / 期望值），端口必须逐条一致（2/2）。
- **判别力自证**：6 条规则变异（禁改写 / 越根不 fail-closed / 最短长度 3→2 / 去掉 `/` 要求 / 不裁尾标点 / 不去重）**6/6 各被探针抓到**。
- **唯一变量**：语料收集口径沿用 R481-A（同 SKIP / 1 MB 上限 / 文本探测）⇒ 与旧端口的差只来自**抽取规则**。

**预注册**：`eval/recall/prereg_r481b.json` 先于首跑落盘；`supersedes` **只覆盖** G3 口径与 refs 定义，`prereg_r481a.json` 的判据与读数**不翻案**（旧口径同批并列作对照臂）。

**真读数**（`eval/recall/r481b/port-corpus.json`；语料 6,658 文件 / `files_sha16 1000893f7926c08c`；同时段旧端口读数见末行）：

| 项 | 新口径（产品派生规则） | 旧口径（R481-A 端口） |
|---|---|---|
| 候选地址 | **76,404**（跨 URL 1,524 = `unreported`） | 20,280 |
| 解析率 G1（≥0.90） | **0.1450 ❌** | 0.8504 |
| 悬空率 G2（≤0.10） | **0.8550 ❌** | 0.1496 |
| 显式相对引用 `./`·`../` | **660**（旧档把裸名也算进 = 1,163） | — |
| 相对引用落地 G3（≥0.85） | **0.1091 ❌**（72/660） | 0.2650 |
| 地址覆盖 G4（p50≥1） | **p50 = 5 ✅**（零地址文件 30.43%） | p50 = 0 / 76.11% |
| 越根 fail-closed 原值保留 | **2** 条（单列） | 未单列 |
| 绝对路径形态（仓根外） | 7,462 条（单列，不混入「越根」） | 混入 dangling |
| 按引用方目录兜底可解析（诊断） | 53 条 | 未测 |

**按来源通路分解**（新口径，本轮新增字段）：markdown 目标 **96**（落地 65/80 = **81.25%**）／裸 URL **1,508**（全 `unreported`）／相对地址串 **74,800**（落地 10,796 = **14.43%**，悬空 64,004）⇒ **悬空的 99.98% 来自「相对地址串」通路**。

**结论（口径层，非产品缺陷）**：产品的接受规则是**结构性宽判据**（`含 '/' ∧ 无空白 ∧ 3–512 字符`），代码/配置/模板里的 slash token（`bin/`、`obj/`、`.gitignore` 条目）与绝对路径全部进候选 ⇒ G1/G2 在「全候选档」上**结构不可达**；「内容自带链接」的真读数在 markdown 档（81.25%）。
**天花板算式**：相对引用改写的可达面 = **660 / 74,880 = 0.88%**；即使该档 100% 落地，解析率也只 **+0.88 pt**（0.1450 → 0.1538），距 ≥0.90 的 **75.5 pt** 缺口不是这个机制的杠杆（`可省 ≤ 该类占比 × 该类可消除比例`）。

**诚实边界**：
1. 旧端口**未逐位复现** R481-A 登记值（6,662 文件 / 20,293 候选 / 0.8502 vs 登记 6,647 / 20,155 / 0.8508）⇒ 语料已增文件（+14），且旧端口无排除规则会把器具产出目录一并计入 ⇒ 跨轮对比标 **`不可比（语料漂移）`**，不当回归。
2. 端口自检（派生 + 差分 + 变异）是**自我认证**，只作必要条件；产品侧真机度量（`agent.recall` 度量模式）仍未做。
3. Unicode 近似：`str.isalnum`/`str.isspace`/`lower()` 分别近似 `char.IsLetterOrDigit`/`char.IsWhiteSpace`/`OrdinalIgnoreCase`。
4. 候选面**无法从文本层区分「链接语境」与「代码 token 语境」** ⇒ 本读数测的是**接受规则的精度**，不是「内容自带链接的召回」。
5. 误差面：首跑（`port-corpus-firstpass.json`）未排除器具自身源码、且把绝对路径与越根混算 ⇒ 已修并重跑，首跑归档保留（不覆盖）。

**口径冲突登记（文档内部，承 R435「口径冲突要显式作废」）**：计划 §1 G2 写「悬空 ≤0.10」，而 `prereg_r481a.json` 的 G2 阈值写「dangling_rate ≤ 0.35」——**两处不一致**。处置：预注册**不得事后修改**，故旧阈值只在其自身口径下有效；本轮判据采用 `prereg_r481b.json` 的 **≤0.10（与计划一致）**。在新口径下两档都越线（0.8550），故该冲突**不影响本轮判定**，但须登记在案以免后续会话按 ≤0.35 误读 R481-A。

**下轮候选（一步）**：① **分档口径预注册**（把候选按形态分档：markdown 目标 / 显式相对 / 根相对路径 / 其余 slash token，各档单列目标——数据已在 `by_origin` 与 `readings`，本轮的 81.25% vs 14.43% 是分档依据）② 产品侧器具（`agent.recall` 度量模式）与端口交叉核对 ③ 1e5 规模臂 ④ R479 遗留（路由器接线 / 入链 prompt 正文槽位化）。**不建议**继续投入「相对引用改写」（可达面 0.88%，天花板 ≤ +0.88 pt）。


## R481-G（本侧独立复核 + 语料钉 + 分档口径预注册）

### G1 独立复核（不采信对侧自述）
- `python3 eval/recall/links_port_r482.py --selftest` ⇒ **rc=0**；`N3_mutations_caught=true`（6/6 变异被抓）。
- `python3 eval/recall/links_port_r482.py --out /tmp/port_g.json` ⇒ **rc=0**；本侧读数与 R481-F 报告**同向同量级**：`G1=0.1449`（报 0.1450）/ `G2=0.8551`（0.8550）/ `G3=0.1086`（0.1091）/ `G4 p50=5` **达标** / `by_origin`：markdown `0.8125`、rel `0.1442`、url `1518 = unreported`。
- `old_arm.vs_registered_r481a.match = false`（files 6,687 vs 6,647；refs 20,348 vs 20,155）⇒ 器具已自标**不可比（语料漂移）**，与报告一致 ✔。
- 形式门禁本侧自跑 ⇒ **rc=0 / Failed 0 / Passed 10 / Total 10**（执行数 > 0，非假绿）。

### G2 发现：语料钉缺失 ⇒ 跨读数可比性无机制保障（本轮新）
`check_corpus_pin.py` 对 4 个 port 读数 ⇒ **rc=1 / PIN_VERDICT=DRIFT**（`distinct_corpus_pins=3`、`distinct_rule_pins=1`）：

| 读数 | files | corpus.files_sha16 |
|---|---|---|
| `r481b/port-corpus-firstpass.json`(08:03) | 6,659 | `251b1c166eca7dbe` |
| `r481b/port-corpus.json`(08:04) | 6,658 | `1000893f7926c08c` |
| `r481b/port-corpus-pass2.json`(08:04) | 6,658 | `1000893f7926c08c` |
| 本侧复跑 (08:2x) | 6,683 | `737b2cca752d55bc` |

- 规则侧**恒定**（`rule_sha16=9e9104ca601f8849` 四个读数全同）⇒ 漂移源是**语料**（`head=ccb132b`、`worktree_dirty_files=37`），不是端口。
- 结论：R481-F 的「两次独立运行核心字段逐字节相同」**只在同一语料成立**；其首跑与第二跑之间语料已 6,659 → 6,658（即已漂移）。**漂移不报警**是机制缺口 ⇒ 本侧补 `check_corpus_pin.py`。
- 归因缺口（诚实边界）：器具只出 `files_sha16`、不出参与文件清单 ⇒ 漂移**可判不可归因**；清单导出列为下轮候选。

### G3 器具与判别力自证
- `eval/recall/r481/check_corpus_pin.py`（语言无关，只读固定字段；三态 fail-closed）：**UNIFORM rc=0 / DRIFT rc=1 / MISSING rc=3**。
- 负控真跑：N1 删 `corpus.files_sha16` ⇒ **rc=3 / PIN_MISSING**；N2 篡改一读数 sha16 ⇒ **rc=1 / DRIFT**；N3 单读数自比 ⇒ **rc=0 / UNIFORM**。

### G4 预注册（先于分档首跑）
- `eval/recall/prereg_r481g.json`：① 语料钉三元组 + 可比性规则（仅当 `(files_sha16, rule_source_sha16)` 全等才可同批对照）；② 分档口径（markdown / url / rel，rel 待细分为 explicit_rel / root_rel / slash_token）+ 各档目标；③ 判据收窄：全局 `resolved_rate>=0.90` 与 `dangling_rate<=0.10` 在含 slash token 的候选面上**结构不可达**（实测 0.1449 / 0.8551）⇒ 只保留 `markdown` 与 `root_rel` 设门槛、`explicit_rel` 沿用 ≥0.85、`slash_token` 不设门槛；④ 负控 N1–N3。
- 预注册**晚于**钉观测落盘 ⇒ 该漂移读数按 R453 单列 `posthoc_observation`，只对其后的比较生效。

### G5 诚实边界
- 分档读数**尚未取得**（器具需加 `by_subband` 输出）⇒ 本文件不宣称任何档达标，也不改 R481-A/B/F 读数。
- 全程 Python 代理面，不测产品面（`agent.recall`）延迟/实现；跨 URL 一律 `unreported` 不冒充 0。
- `src/agent.recall*` 仍 untracked；未 push（`PUSH_PAUSED`）。

## R483 · 分档读数器具（复用端口 + 双重自污染修正）
- 新增 `eval/recall/r483/bands_probe.py`：导入 `eval/recall/links_port_r482.py` 复用源码派生规则（rule pin `9e9104ca601f8849` 两侧一致）。
- 三态：rc=0 读数完成 / rc=2 内不变量失败（守恒）/ rc=3 缺输入或端口派生失败；负控 `--nc-conservation` ⇒ rc=2 ✔。
- 读数：markdown **0.8125**（✘≥0.90）/ root_rel **0.1608**（✘）/ explicit_rel **0.0923**（✘≥0.85）/ slash_token 7,508 全越根（无门槛）；
  refs_total 77,037、url unreported 1,541；pin `5ef643596c8b2690` / 6,710 文件 / NC3 两次逐字节相同。
- 语料钉对照 R481-F：**DRIFT rc=1** ⇒ 不可比（语料漂移，规则未漂移）。
- 归档：`bands-firstpass.json`（首跑含 external 污染 + 自身产物入语料，**不覆盖**）。
