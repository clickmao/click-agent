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

