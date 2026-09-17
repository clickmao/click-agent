# R411-V · 登记表「可执行性」纠偏 + 退役能力降级收口

日期: 2026-09-14 · 轮次: **R411-V**（验证线；同日另有并发 session 在做 **R411 = K2b 长驻本地生成端口**，故本线用 `-V` 后缀避免轮号撞名）
入口: `docs/verification-registry.json`（45 行）+ `src/agent.tests/VerificationFormTests.cs`
触发: 推进计划表**最前未完成项 R402** 时发现其前提随 R408 消失 ⇒ 顺链查出登记表 9 行「宣称≠实现」。

## 1. 因果链

```
推进 R402 步 2（compute-direct 微基准 1 vs 2 线程）
  └─ 复核前提: R408(同日 08:17, 提交 b00917c) 把本地 GGUF 引擎整线退役
       ⇒ agent.rover/{infer,cli,runtime,token,...} 已删 ⇒ 原定的"被测对象"不存在
       └─ 查登记表: rover.io.attribution 行仍挂 L3, evidence_cmd 仍调用
            已删二进制 + 已删测试过滤器(RoverProcIo) + 已删源文件 covers
            ⇒ 但机检**全绿**（只验 evidence_path 存在）
            └─ 机检缺口: R2 只问"命令写着没有", 不问"命令还能不能跑"
                 ⇒ 一次审计抓出 9 行同类（3 行退役残留 + 4 行 covers 路径错 + 1 行归档名不符 + 1 行反证命令未声明）
                    └─ 纠偏 + 给机检补 R2b/R2c/R2d（含负向控制）⇒ 同类缺陷今后**编译期前哨**
```

关键认识：**「有登记行」不等于「证据可执行」**。R370 立的登记表机检验的是「路径存在」，于是
「命令里调用的二进制/测试/源文件全被删掉」这一整类缺陷**穿透了闸门** —— 与 skill 里
「只校验文件存在的机检等于没检」同源。

## 2. 产出表

| # | 文件 | 改动 | 性质 |
|---|---|---|---|
| 1 | `src/agent.tests/VerificationFormTests.cs` | 新增 **R2b**（`evidence_cmd` 里仓库路径必须存在；反证类须声明 `cmd_expect_absent[]`，声明与事实矛盾也报红）、**R2c**（`covers[]` 路径必须存在）、**R2d**（`--filter FullyQualifiedName~X` 必须能解析到真实测试类/方法）；`bin/`、`obj/` 构建产物不机检（干净检出下本就不存在，上游由 covers 钉住） | 机检加固 |
| 2 | 同上 | 负向控制扩到 **7 类注入坏行** + **2 条正向/反向控制**（声明豁免必须放行；声明与事实矛盾必须报红）；测试名扫描为空时**自曝失效**（fail-loud，不静默放行） | 负控加固 |
| 3 | `docs/verification-registry.json` | **9 行纠偏**（见 §3.2）；`updated_round` R408 → **R411-V**；45 行不变 | 事实纠偏 |
| 4 | `docs/验证形式规范.md` | R2 下增设 R2b/R2c/R2d；新增「**退役能力的登记形态**」定式（L0 + 可执行的退役账断言 + `cmd_expect_absent` + `gap_note`）并记入史实 | 规范 |
| 5 | `docs/reports/r402/io-attribution.md` | 新增 **§8 收口**；§7 加「前提作废」补注（原候选清单保留，标注对象已删） | R402 收口 |
| 6 | `eval/rover/r402/README.md` | **补登记孤儿归档** `compute-bench.json`（步 2 微基准，此前 3 行表里没有它）+ 裁定与边界 | 证据补登记 |
| 7 | `eval/rover/r408/r408-evidence.md` | §B 补「归档口径」：入库的是 **AOT 臂**产物 `aot-generate.json`；旧登记行引用的 `e2e-generate.json` **从未入库** | 诚实纠偏 |
| 8 | `docs/plans/v0.22.0-longterm-backlog.md` | R402 → **已收口(R411-V)**；R403 → **前提复核（待判）**；轮次看板加 R411-V 行 | 计划同步 |

## 3. 机检证据（两侧对照）

### 3.1 检查器**先证明会红**（负向控制）

`Validator_CatchesInjectedDefects` 合成坏表必须全红，含 **7 类**：
删除登记行 / L≥2 缺负向控制 / 静态命令越级申报 / 未登记插件 / **cmd 引用不存在路径** /
**covers 引用不存在路径** / **测试过滤器解析不到测试**；
另有两条方向相反的控制：`cmd_expect_absent` 声明的路径**确不存在 ⇒ 必须放行**（不误杀），
**声明不存在却存在 ⇒ 必须报红**（声明不可成为免检后门）。

### 3.2 检查器**在真数据上抓到的 9 行**（加固后一次性抓全）

| 行 | 缺陷 | 处置 |
|---|---|---|
| `rover.io.attribution` (R402) | `evidence_cmd` 调已删二进制 + 过滤器 `~RoverProcIo` 指向已删测试；covers 5 条指向已删源；L3 宣称运行级 | **L3 → L0**；命令改为**可执行**退役账断言；covers 收敛到 4 个归档件 |
| `rover.generation.chain` (R400) | covers 10 条指向已删源；L4 宣称；cmd 调已删 CLI | **L4 → L0**；同上（夹具 + 报告留档） |
| `gpu.spirv.structural-validation` (R389) | cmd 调已删 CLI；covers 含已删 `cli/VulkanCli.cs`；L4 宣称 | **L4 → L1**（库形态留存，驱动退役 ⇒ 5 组负控**当前无入口可复现**） |
| `llamacpp.process.boundary` (R408) | cmd 引用 `eval/rover/r408/e2e-generate.json` —— **该文件从未入库**（入库的是 AOT 臂 `aot-generate.json`） | cmd + covers 改指实际归档件；文档补归档口径 |
| `segment.plugin.router` | covers 指 `src/agent/registry/CodeReviewPlugin.cs` —— 该文件不存在（类声明在 `UiCapturePlugin.cs` 内） | covers 改指真实声明处 |
| `plan.route.ablation` | covers 含 `src/agent/tests/...`（目录名错，真实为 `src/agent.tests/`） | 修正目录名，去重复项 |
| `python.interpreter.pinned_tool` | 同上（同类笔误） | 同上 |
| `plan.resume.checkpoint` | covers 指 `src/agent/recovery/...`（真实为 `src/agent.recovery/`） | 修正 |
| `engine.retired.no_local_gguf` | 反证命令（`test ! -d ...`）未声明「必须不存在」的路径 | 补 `cmd_expect_absent[]`（4 条） |

**加固前（Python 等价复现规则）**: 9 行违规 → **加固后: 0 行**；C# 侧同一规则由 `VerificationFormTests` 执行，
过滤器口径（`VerificationForm|SkillGeneralization|DevPlanDocRef`）的实际运行结果见 §3.3。

### 3.3 形式校验运行（隔离副本，原因见 §6）

```bash
# 证据树 = HEAD + 本轮 7 个改动文件（不含并发 session 的未提交 WIP），哈希已与工作树逐字节比对一致
cd /tmp/r411v && dotnet test src/agent.tests/agentframework.tests.csproj \
  --filter "FullyQualifiedName~VerificationForm|FullyQualifiedName~SkillGeneralization|FullyQualifiedName~DevPlanDocRef" \
  --nologo -v q > run-filtered.log 2>&1 ; echo "TEST_EXIT=$?"
```

> 结果见 §7「运行记录」（本轮在报告定稿后回填，**不预填结论**）。

## 4. R402 收口裁定（本轮最前计划项的结论）

**步 2 的读数早已存在，但从未登记** —— `eval/rover/r402/compute-bench.json`（R407 提交 `cd8feeb` 入库）：

| 张量 | 1 线程 | 2 线程 | 加速比 | `y_hash` |
|---|---|---|---|---|
| `token_embd.weight` Q4_K | 464.5 ms / 0.5079 GB/s | 442.7 ms / 0.5329 GB/s | **1.049** | 相等 |
| `blk.0.ffn_down.weight` Q6_K | 92.5 ms / 0.3999 GB/s | 89.5 ms / 0.4134 GB/s | **1.034** | 相等 |

- **裁定**：对照 R402 报告 §7.1 **预注册**判据「2 线程加速比 <1.3× ⇒ 加线程升不了级」⇒ 实测 **1.034–1.049 ⇒ 不升级**。
- **机制**（与读数同向、非事后编解释）：本机 **2 vCPU = 1 物理核 + SMT**（R408 证据抬头）⇒ 无第二物理核可并行。
- **机制启用断言**：`disk_read_bytes=0` / `majflt=0` ⇒ 确认是**权重常驻内存的纯计算**（不是被盘读污染）；
  `y_hash` 两档相等 ⇒ 线程数**不改变数值结果**（等价性证据，替代"看起来更快"）。
- **不可核验**：`estimates[].est_ms_per_token`（8866→8488）是原产物自述，外推公式随生产者 CLI 被删 ⇒ 不可复核；
  它与 §3.5「计算 9.2–17.0 s/pass」量级相近但口径不同 ⇒ **只算同量级一致性（指示性），不构成互证**。
- **收口**：步 3（批量 prefill A/B）对象已删；R402 无可续做步骤。问题本身由 R408 **形态替换**解决
  （`llama-server` 17.891 t/s vs 本引擎 AOT 0.2017 t/s = **89×**）——**这是换实现，不是本线优化成果**。

## 5. 基线

| 指标 | 值 |
|---|---|
| 登记表行数 | 45（不变） |
| `updated_round` | R408 → **R411-V** |
| 等级分布变化 | L4 **−2**（12→10）、L3 **−1**（17→16）、L1 **+1**（2→3）、L0 **+2**（0→2）；L2 不变（14）—— 3 行退役/驱动退役的能力不再挂运行级 |
| 本轮违规（加固后） | **0**（加固前 9） |
| 负向控制 | 7 类注入坏行 + 2 条方向控制（声明豁免放行 / 声明矛盾报红） |
| R402 步 2 裁定 | 2 线程加速比 **1.034–1.049 < 1.3×** ⇒ 不升级 |
| 分号拼接/JSON 破坏事故 | 0（改写前后逐字节断言 + 读回校验 + 幂等） |

## 6. 诚实边界

1. **门禁在隔离副本上跑，不在共享工作树**：并发 session（R411 = K2b 长驻端口线）正在同一工作树里
   编辑 `src/agent.{host,llamacpp,modelqueue}`（未提交）。按「build/批测/单测互斥」纪律，我**不在其构建窗口内**
   跑构建；证据树取 `HEAD + 本轮 7 文件`（哈希与工作树一致）⇒ 结论对**本轮改动**成立，
   对「并发 WIP 一起编译后是否仍绿」未证（那属另一 session 的提交面）。
2. **R2b 不覆盖构建产物路径**（`bin/`/`obj/`）：干净检出下本就不存在，若强行机检会在其它机器上假红。
   代价：**「命令调用的二进制名是否还存在」不进机检**（如裸 `agent.rover tokenize`）；本轮该形态由 `covers[]` 规则
   间接抓到（covers 里同源源文件已删）——但这是**间接**，属已知缺口。
3. **`covers[]` 规则治不了「文件还在但语义已变」**：路径存活 ≠ 覆盖有效；语义级漂移仍需人读。
4. **R403 只做「前提复核（待判）」**：判据引用 R408 §Q5 与 R409 §2.1，但「工具调用模板是否改口径」
   需独立判定，本轮**不改其状态**（避免把两件事并成一步）。
5. **退役行降级为 L0 不等于归档数据被推翻**：归档读数（盘读比、双计负控 2.00×）仍有效，
   只是**不可再产出**；等级下降是「可复现性」的诚实记账。
6. 本轮**未**碰 R402 以外的产品代码；除 §2 表格外的文件零改动。

## 7. 运行记录（回填 · 真实执行）

| 项 | 值 |
|---|---|
| 证据树 | `/tmp/r411v` = `git archive HEAD` + 本轮 7 个改动文件（`docs/verification-registry.json` 与 `VerificationFormTests.cs` 的 md5 已与工作树逐一比对一致：`5b04eb7a…` / `9fd9e2bc…`） |
| 命令 | `dotnet test src/agent.tests/agentframework.tests.csproj --filter "FullyQualifiedName~VerificationForm\|FullyQualifiedName~SkillGeneralization\|FullyQualifiedName~DevPlanDocRef" --nologo -v q`（`DOTNET_ROOT=$HOME/.dotnet`） |
| **第 1 跑（红）** | `Failed: 1, Passed: 12, Total: 13` · **`TEST_EXIT=1`** —— 失败项 = `VerificationFormTests.Validator_CatchesInjectedDefects`（**本轮新写的负控表自己**） |
| 红因（如实） | 注入坏行 `e.dead_cmd_path` 的 `evidence_cmd` 误用了**真实存在**的 csproj ⇒ 该行**不产生任何违规** ⇒ R2b 断言失败。这恰是负控闭环要的形态：**「注入的坏行没坏」必须让测试变红**，否则负控就是空心的（若把断言放宽成 `>=1` 就永远绿） |
| 修法 | 该行 `evidence_cmd` 改为引用不存在的 `src/agent.tests/deleted-suite.tests.csproj`（保留一个可解析的 `--filter` 以隔离 R2b 与 R2d 两条判据） |
| **第 2 跑（绿）** | `Passed! - Failed: 0, Passed: 13, Skipped: 0, Total: 13, Duration: 505 ms` · **`TEST_EXIT=0`** |
| **第 3 跑（最终树复核）** | `Passed: 13, Failed: 0, Duration 1 s` · **`TEST_EXIT=0`** —— 在 R403 状态措辞定稿（「待定」）与 kpi 行补写之后重跑，证据树与该提交内容一致；归档 `eval/verification/r411v/run3-FINAL.txt` |
| 日志归档 | `eval/verification/r411v/run1-RED.txt`（22,450 B）、`eval/verification/r411v/run2-GREEN.txt`（21,342 B）；两者末行均由脚本显式写入 `TEST_EXIT=<码>`（**批结论取自该标记，不取管道末条命令的退出码**） |
| 耗时 | 测试执行 505 ms；构建耗时**未单独计时**（两跑均在 ≤180 s 的等待窗口内完成，属区间描述，非读数） |

**这说明什么**：机检在**真数据**上从 9 行违规 → 0 行，且检查器**自己被证明会红**（第 1 跑红、第 2 跑绿，两次运行只有注入表那一行不同）。
注意第 1 跑的红**不是**「本轮改动把登记表弄坏了」—— 登记表那 9 行修正在第 1 跑时已就位（同一 md5）；红的是负控表自身。

## 8. 下轮候选

1. **R403 正式判定**：按 R408 §Q5 / R409 §2.1 裁定「关闭」或「改口径为验证 llama.cpp tool 模板行为」。
2. **R2b 覆盖构建产物路径**（若采纳）：改为「项目产出关系」校验（路径 → 生成它的 csproj 必须存在且 OutputType 相符），
   以闭掉 §6.2 的缺口（裸二进制名仍是空白）。
3. **covers 语义级校验**：为 covers 条目增加可选 `symbol` 字段（如 `UiCapturePlugin.cs(CodeReviewPlugin)` 的括号内容
   必须在文件内出现为符号），把「路径存活」升级为「符号存活」。
4. **并发工作树的构建互斥**：同一 worktree 双 session 已两次导致「我的构建撞别人的半成品」，候选 = 每 session 独立
   `git worktree` 或「构建前探测 VBCSCompiler/dotnet 进程 + 文件 mtime 窗口」的启动闸。
5. R402 相关：若将来重建引擎（无计划），§7 原候选清单可直接复用。

## 9. 收工探针读数 + 两处「机器接口」级发现

- 探针（`python3 scripts/capability_cycle.py status`，本轮收工后）：`mode=tasks`、`open_count=3`、
  `open_items=[R403(待定), R371, R370]`、`kpi_lines=6`、`skills_count=10`、`backlog` 诊断 `closed=4 / unmarked=1`。
- **发现 1（状态措辞是机器接口）**：R403 最初被我写成「前提复核（**待判**）」——探针的开放标记表是
  `(进行中/未开始/待定/部分/计划中)`，零命中 ⇒ 该行被归入 `unmarked`（诊断里可见，但**不进 `open_items`**），
  循环的下一靶点会**跳过 R403 落到 R371**（另一条线）。改用标记表内的「**待定**」后，`open_items` 最前 = R403。
  ⇒ 教训：**改状态文本前先查判定器的标记表**；否则「我记下了」与「循环能读到」是两件事，
  且这类漏读**不报错**（表现为靶点悄悄换了一条线）。
- **发现 2（指令自身路径漂移）**：本循环指令要求读 `docs/plans/iteration-master-plan.md`，该路径**不存在**；
  实际文件在 `docs/reports/iteration-master-plan.md`（本轮按实际路径执行）。建议修正指令文本，
  否则每轮都会白读一次、并由「缺失」而非「无未完成事项」决定分支。
