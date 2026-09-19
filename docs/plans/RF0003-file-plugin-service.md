# RF0003 — 文件处理插件服务（修改前必备份 · 竞争判定 · 合并）

口径（用户令逐字）：「**文件处理也要做成一个插件服务，因为涉及到 agent 会独立处理文件。比如修改前必须备份，文件修改竞争(用户再改，agent 也在改，diff 合并等)**」

## 1 问题拆解（先定「问题是什么」，再给决策）

| # | 问题 | 决策 | 边界（诚实） |
|---|---|---|---|
| Q1 | 何时备份 | **任何写盘之前**，先落备份再写；备份成功才允许写 | 备份失败 ⇒ `Rejected`，盘上零字节变化（fail-closed） |
| Q2 | 备份存哪 | 工作区下 `.filedb/backups/`，**内容寻址**（`<sha256[..16]>` 一个 blob 一份）+ append-only 索引 `.filedb/backup-index.jsonl`（原路径/时间/字节/来源可追） | 相同内容只存一份；索引行含 `Source`（谁改的） |
| Q3 | 保留多久 | 每个原文件保留最近 `KeepPerFile`（默认 20）条，超出按 `TakenUtcTicks` 淘汰；仅当无其他路径引用该 blob 才删 blob | 不做时间过期（时间策略留 v2） |
| Q4 | 竞争怎么判 | **乐观并发**：agent 读时拿 `FileSnapshot.Sha256`，写时提交 `ExpectedSha256`；现盘 sha == 期望 ⇒ 快路径；不等 ⇒ 进竞争分支 | 语义冲突检测不做（只看字节） |
| Q5 | 冲突怎么办 | **重叠且两侧文本不同 ⇒ 不写盘**，返回 `FileConflict[]`（base 行坐标 + 两侧文本）⇒ 交用户裁定 | 绝不静默取一侧（禁「差不多就行」） |
| Q6 | 合并粒度/上限 | 行级三方合并（稳定区算法：两侧都未动的 base 行直通 / 单侧改动取该侧 / 两侧同改且相同取一份 / 不同即冲突） | 字符级合并不做；任一侧行数 > `MaxMergeLines`（默认 2000）⇒ 拒绝自动合并交人工 |
| Q7 | 原子性 | 写 = 同目录 `.<name>.<guid>.tmp` + `File.Move(overwrite:true)`（rename 原子）；写前**二次读盘核对** sha（TOCTOU 闸） | 跨进程文件锁不自建（靠 rename 原子 + 二次核对 + 备份可回滚） |
| Q8 | 失败怎么回退 | 任意失败路径：盘上原文件不动 + 备份已在 ⇒ 可 `Restore` 逐位还原 | 备份库自身损坏不可恢复（另议） |
| Q9 | 插件形态 | `IFileServicePlugin` + `FileServicePluginRegistry`（与既有 `IImageRenderPlugin`/`ImageRenderPluginRegistry` **同构**：`GetDefault()` 取首个 `IsAvailable`）；默认实现 `NativeFileServicePlugin` | 不把文件处理写死进 agent 循环；无可用插件 ⇒ 诚实不可用，不降级硬跑 |
| Q10 | 判据 | 机检 T1–T12 + 负控（关备份 ⇒ 拒写 / 制造竞争 ⇒ 原盘逐位不变） | 判据**非替对侧声明**：只看本服务自己的落盘与返回 |

## 2 契约

```
IFileService
  string Root
  Task<FileSnapshot> SnapshotAsync(path)
  Task<string?> ReadTextAsync(path)
  Task<FileEditResult> ApplyAsync(FileEditRequest)
  IReadOnlyList<FileBackupRecord> ListBackups(path)
  FileEditResult Restore(record)

FileEditRequest { Path, ExpectedSha256, NewText, BaseText?, Source }
FileEditResult  { Outcome, Path, Snapshot?, BackupPath?, BackupSha256?, MergedText?, Conflicts[], Note }
FileEditOutcome = Applied | MergedAuto | Conflict | StaleBase | Rejected
FileBackupRecord{ Sha256, Bytes, OriginalPath, TakenUtcTicks, BlobPath, Source }
```

`Wrote = Outcome ∈ {Applied, MergedAuto}` —— 其余三类**保证盘上零改动**。

## 3 判定顺序（ApplyAsync 单路径）

1. 进程内 per-path 互斥（同进程并发写串行化）。
2. 读现盘快照 `current`；非文本（UTF-8 严格解码失败）⇒ `Rejected`。
3. `current.Sha256 == ExpectedSha256` ⇒ 快路径 → 步骤 6（`Applied`）。
4. 现盘已变：`AllowMerge=false` ⇒ `StaleBase`；基线（`BaseText` 或备份库中 `ExpectedSha256` 那一版）取不到 ⇒ `StaleBase`。
5. 三方合并（base/ours=现盘/theirs=NewText）：
   - 有冲突 ⇒ `Conflict`（**不写**）；
   - 超上限 ⇒ `Rejected`（**不写**）；
   - 干净 ⇒ `MergedAuto` → 步骤 6。
6. 写前二次核对 `current` 与写盘时现盘一致（否则 `StaleBase`）⇒ 备份现盘字节（失败且 `RequireBackup` ⇒ `Rejected`）⇒ 原子 rename 落盘。

## 4 落点

`src/agent.files/`（新项目，`agent.Files`）：`IFileService` / `LocalFileService` / `FileServiceOptions` / `FileSnapshot` / `FileEditRequest` / `FileEditResult` / `FileEditOutcome` / `FileConflict` / `FileBackupRecord` / `FileBackupStore` / `ThreeWayLineMerge` / `MergeOutcome` / `ContentHash` / `FileServiceJsonContext` / `IFileServicePlugin` / `NativeFileServicePlugin` / `FileServicePluginRegistry`。
测试 `src/agent.tests/FileServiceTests.cs`（T1–T12 + 负控 2 条）。

## 5 本轮不做（登记为候选，不假装做了）

① 接进 `Workspace.WriteFileAsync`/`OrchestrateCommand` 产品路径（会改既有行为，须单独一轮 + 让行检查）；
② 跨进程锁 / 文件监视（`FileSystemWatcher`）；
③ 字符级或 AST 级合并；④ 二进制文件的差异与合并（本轮只做「拒写 + 备份」）；
⑤ 时间维度过期策略；⑥ 与远端 LLM 的冲突裁定回路（先有冲突块，再谈谁裁）。
