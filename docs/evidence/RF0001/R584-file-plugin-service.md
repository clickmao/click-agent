# R584 — 文件处理插件服务 `agent.files`（修改前必备份 · 竞争判定 · 三方合并）

口径（用户令逐字）：「**文件处理也要做成一个插件服务，因为涉及到 agent 会独立处理文件。比如修改前必须备份，文件修改竞争(用户再改，agent 也在改，diff 合并等)**」

## 1 交付物（本轮全部新增，`src/agent.files/` 19 文件 1,244 行 + 测试）

| 文件 | 行 | 职责 |
|---|---|---|
| `IFileService.cs` | 29 | 服务契约：快照/读/写/列备份/还原 |
| `LocalFileService.cs` | 331 | 实现：乐观并发判定 + 写前二次核对 + 原子替换 + 进程内互斥 + 沙盒 |
| `FileBackupStore.cs` | 306 | 备份库：内容寻址 blob + append-only 索引 + 保留淘汰 + 还原 |
| `ThreeWayLineMerge.cs` | 228 | 行级三方合并（LCS 锚点 ⇒ 双侧 hunk ⇒ 按 base 坐标归并） |
| `IFileServicePlugin.cs` / `NativeFileServicePlugin.cs` / `FileServicePluginRegistry.cs` | 17/13/46 | 插件面（与 `IImageRenderPlugin` 同构）；无可用插件即诚实不可用 |
| `FileSnapshot/FileEditRequest/FileEditResult/FileEditOutcome/FileConflict/MergeOutcome/MergeHunk/MergeSide/FileBackupRecord/FileServiceOptions/ContentHash/TextCodec/FileServiceJsonContext` | 余量 | 数据面（单类型单文件；JSON 走源生成，零反射） |
| `src/agent.tests/FileServiceTests.cs` + `UnavailableFileServicePlugin.cs` | 400+15 | 16 条判据（含 3 条负控） |

## 2 判据（机检 16/16 绿；负控先证明器具有牙）

| # | 判据 | 断言 |
|---|---|---|
| T1 | 修改前必备份 | Applied 后备份链 1 条且 `Sha256` = 前态、blob 内容 = 前态逐字节 |
| T2 | **备份失败即拒写（fail-closed，负控）** | 备份根不可建 ⇒ `Rejected` 且现盘字节逐位未变 |
| T3 | 重叠竞争不写盘 | `Conflict` + 冲突块（base 坐标 + 两侧文本）+ 现盘 sha 未变 |
| T4 | 非重叠竞争自动合并 | `MergedAuto`，两侧改动同时在盘上，备份 = 合并前现盘 |
| T5 | 缺基线不猜 | 现盘变更且无 `BaseText`/无该版本备份 ⇒ `StaleBase`，不写 |
| T6 | 文件被删不复活 | 期望 sha 非空但文件已不在 ⇒ `StaleBase`，不写 |
| T7 | 关合并即拒（负控） | `AllowMerge=false` ⇒ 现盘变更一律 `StaleBase` |
| T8 | 非文本拒改 | 非法 UTF-8 字节 ⇒ `Rejected`，现盘未变 |
| T9 | 沙盒（负控） | `../escape.txt` ⇒ `Rejected`「路径越界」 |
| T10 | 超合并上限拒自动合并 | 任一侧行数 > `MaxMergeLines` ⇒ `Rejected` |
| T11 | 保留策略 + 内容寻址 | 超 `KeepPerFile` 淘汰最旧；同内容多文件共用同一 blob |
| T12 | 还原可逆 | 还原 = 备份内容逐字节；还原本身先备份现盘（链 +1） |
| T13 | 并发不丢写 | 同 `ExpectedSha` 两次 Apply ⇒ 恰 1 次 `Applied` + 1 次 `MergedAuto`，两侧改动都在 |
| T14 | 合并器结构断言 | 重叠 ⇒ 冲突块带 base 行号/两侧文本；非重叠 ⇒ `Clean` |

## 3 真机 E2E（真实文件系统 + 走插件注册表取服务）

`eval/rover/r584/r584_e2e_file_service.txt`（sha256 `bafa3dc6a8ba3858f1eba980…`；源码 `eval/rover/r584/rf0003demo/`）

```
[0] 插件: native-local-file-service available=True
[2] agent 读: sha=ea7b8c2813027b53 bytes=23
[3] 用户改第2行: sha=53df65b517eb00a8
[4] agent 提交(重叠): outcome=Conflict 冲突=1 盘上 sha 未变=True 备份=<无>
    冲突块 base[1..2) ours="2 USER" theirs="2 AGENT"
[5] agent 提交(非重叠): outcome=MergedAuto 盘上="1 USERX\n2 USER\n3 AGENT\n4 appended\n"
[7] 还原最早备份: outcome=Applied 逐位等于备份内容=True 还原后备份链=2 条
[8] 负控 越界路径: outcome=Rejected note=路径越界（超出工作区根），拒绝访问
```

## 4 闸

build agents.Files `0 error / 0 warning` · 定向 `FileServiceTests` **16/16** · 全量 **1936/1936**（前态 1920 + 本轮 16，rc=0，37 s）· 形式门禁 **14/14** · API 基线 **+115/−0（115 行全部属 `agent.Files`，既有面零改动）** · sln 已挂 `src/agent.files/agent.files.csproj` · 读数档 `eval/rover/r584/r584_full_test.txt`。

## 4.1 本轮器具自捕（`roundcheck` P5 假 WARN）

起手 `preflight` 报「在飞执行体 `agenthost×1, llama-server×1`」⇒ 复核实为**自匹配**：旧实现 `pgrep -c -f <pat>` 把调用者自己的命令行（含 `agenthost` 字面量）算成了在飞执行体。改为扫 `/proc` 按 **argv[0]**（解释器进程再看 argv[1]）匹配 ⇒ 复跑 `P5_no_sibling_load` **PASS「无在飞执行体」**；`--selftest` 增「假红控制2」（P5 不得自匹配）⇒ **SELFTEST PASS（负控 3/3 有牙 + 正控 1/1 + 假红控制 2/2）**。

## 5 诚实边界（未被本轮证明的部分）

1. **只做进程内互斥**：跨进程无文件锁，靠「写前二次核对 + 原子替换」；跨进程竞争会落到合并/冲突路径，不会静默覆盖，但也没有跨进程排队。
2. **TOCTOU 窗口未被注入式测试打到**：代码里有写前二次核对（不一致 ⇒ `StaleBase`），但没有在两次读之间插入写者的测试手段。
3. **合并上限 2000 行**（DP 表 ≈16 MB/次）；超限拒自动合并，不降级为覆盖。
4. **边界邻接改动**按 base 坐标序无损拼接；**插入点严格落在改动区内部** ⇒ 判冲突（保守，宁可问人不静默丢改）。
5. 非 UTF-8 文本一律拒改；不处理二进制/大文件。
6. **尚未接产品路径**（`Workspace`/`Orchestrate` 的写盘点未改为走本服务）⇒ 本轮是「服务 + 插件 + 判据」到位，产品接线留待下一轮（会改产品行为，需先说明改哪一格读数）。

## 6 下一轮候选

①接 `Workspace.WriteFileAsync` / 编排面写盘点 ⇒ 让 agent 真实写文件必经备份链；②TOCTOU 注入测试；③冲突块回执进章程 `pending_inputs`（停链问人）；④AOT publish 出零反射证据。
