# R539 (2026-09-18) — 主线对照补**外侧臂**（codex 断链修复 + 首跑 · 3 独立窗）+ R537 五候选同轮闭合

轮志 / 证据：`eval/rover/r539/`（`prereg-r539.json` · `taskset-r539.json` · `run_r539.sh` · `run-w{1,2,3}/` · `snapshots/` · `evidence/windows/*/report.json` · `analyze-r539.json`）
收口闸：`python3 eval/rover/r507pre/exec_precondition.py --round r539` ⇒ **rc=1（未可验收）**

## 1. 因果链

R536/R537 的未闭合项是「主线四硬条件缺**外侧对照**」：R535/R536 两轮都写明「codex 外部真值臂本窗未跑」。R539 起手核发现**这不是没跑，而是跑不了**：`eval/rover/r528|r531` 用的 `eval/rover/r511/proj_run_side.py --side codex` 走 `load_codex_engine()` 加载 `eval/rover/r504/codex_solver_r504.py`，而该文件已在 **`d7821b7`（R534 减法批 2：删「可归档轮内 registry 零引用」的纯每轮产物）** 被删（`__pycache__` 残留）⇒ 外侧臂**静默不可执行**（有代码行 ≠ 生效；减法批只查了 registry 引用，没查**跨轮调用点**）。修了外侧臂才谈得上「比」，故 R539 = 「先修外侧臂 → 三独立窗同跑 → 五候选并入」。

## 2. 本轮产出

| 候选 | 产出（文件 / 命令） | 真机证据 |
|---|---|---|
| ① 主线段：外侧臂修复 + role 轴 n=3 窗 | `eval/rover/r539/codex_solver_r539.py`（自 `22dd360:eval/rover/r504/codex_solver_r504.py` 复原）· `proj_run_side_r539.py`（本地化引擎路径）· `run_r539.sh`（3 窗 × 5 臂） | 3/3 窗 codex 臂 `rc=0` 且可判分（`C-codex-t1` = 29/30 · 30/30 · 30/30） |
| ② rc=8 成对报 + 机检「rc=8 不作正确性证据」 | `src/agent/r1/R1Pipeline.cs`（措辞成对）· `R1Transcript.cs`（新机读字段 `correctness_asserted`，仅 rc=0 为 1）· `R1PipelineTests.cs`（`Rc8_Is_Paired_And_Not_Correctness_Evidence`）· `eval/rover/r539/rc8_evidence_guard.py`（+`--self-test` 3 负控） | AOT 二进制实发：`reason` 含「自测未达成 ∧ 产物可疑」+「rc=8 不作正确性证据」；`rc8_evidence_guard --round r539` 扫 **13 transcript / 16 快照行 ⇒ PASS**；真机 2 例 rc=8 且外部判分 **30/30** |
| ③ `missing_slots` 停链（rc=2）首测 | 新题 `ms1`（题面「把它改好，然后跑一下。」= 指代缺失）· `cases/check_ms1_zero_side_effect.py`（3 机械判：零产物 / rc=2 / 零步） | `rc=2` · `stage=semantics_incomplete` · `reason=缺信息 ⇒ 停下澄清` · `steps_executed=0` · `plan_steps_total=0` · 工作区 0 文件 · **3/3** |
| ④ 生成器 `--check` 挂进提交钩子 | `tools/hooks/pre-commit`（L3 段后新增「R539 生成物漂移闸」，旁路 `AGENTFRAMEWORK_R1GEN_CHECK=0`） | 负控（真路径）：手改生成物 `SemanticsPipeline.cs` 并 `git add` ⇒ 钩子 **rc=1** 且 `R1GEN_DRIFT_FILES=1` 拒收；`AGENTFRAMEWORK_R1GEN_CHECK=0` ⇒ 漂移消息消失；改动已 `git checkout` 复原（sha 前=后）。另：钩子新增的 `EXP1-Q39` 声明闸抓到自身漂移 ⇒ `decl_sweep.py --apply` 刷新（仅 version/sha12，未放宽判据） |
| ⑤ 预注册增补 fail-closed | `tools/prereg_amend.py`（**只做文本插入** + 前后缀字节守恒 + 语义守恒 + 原子写；禁整文档重排） | `--self-test`：**6 正控 + 4 负控全绿**（含 R536 缺陷复现负控：非法 JSON / 重复 id / 无 `amendments` 键 / 注释不保留 ⇒ 一律 rc=2 且**不改盘**） |
| ⑥（本轮新发现）外侧臂断链 | 见 §1 | `d7821b7` 只查 registry 引用、未查跨轮调用 ⇒ 已入下轮候选（中枢修复） |

## 3. 主读数（同题 `t1` = 30 隐藏用例 · 同题面 sha 硬门 · 起手闸 2/2 PASS/窗 · 同 adapter · AOT `9c7dea180c0f52e7c62c5b6c` 15,778,672 B · IL 警告 0）

| 窗 | 臂 | 调用 | 总 token | 用例 | rc |
|---|---|---|---|---|---|
| w1 | `A1-on` | 33 | 519,925 | **26/30** | 1 |
| w1 | `R1r`（挂 role） | **2** | **22,109** | **30/30** | 8 |
| w1 | `R1nr`（不挂） | 2 | 21,837 | 30/30 | 8 |
| w1 | `C-codex` | 347 | 25,036,217 | 29/30 | 1 |
| w2 | `A1-on` | 33 | 658,847 | 30/30 | 0 |
| w2 | `R1r` | **1** | **12,398** | 30/30 | 0 |
| w2 | `R1nr` | 1 | 10,722 | 30/30 | 0 |
| w2 | `C-codex` | 282 | 14,816,249 | 30/30 | 0 |
| w3 | `A1-on` | 33 | 559,074 | 30/30 | 0 |
| w3 | `R1r` | **1** | **11,017** | 30/30 | 0 |
| w3 | `R1nr` | 3 | 32,488 | **28/30** | 1 |
| w3 | `C-codex` | 12 | 125,688 | 30/30 | 0 |

- **主 KPI（`R1r` vs `A1-on`，逐窗）**：调用 **2/33 · 1/33 · 1/33 ⇒ Δ 93.9% / 97.0% / 97.0%**；token **22,109/519,925 · 12,398/658,847 · 11,017/559,074 ⇒ Δ 95.7% / 98.1% / 98.0%**；逐窗极差 **[95.7, 98.1]** ⇒ 三窗全 > 30% 门限，且**质量不降**（`R1r` 三窗 30/30）。
- **跨族面 `m1`**（数学，仅 `R1r`）：**30/30 / 30/30 / 30/30**（rc=5/5/0 —— 自测期望未达成而外部判分全对，与 ② 同族现象）。
- **role 轴 A/B（机器读数）**：`prefix_sha_equal=True`（三窗）· `role_note_chars` A/B = **0 / 326** · **实发 prompt 机检未命中**（见 §4①）。
- **rc=8 双向实证（②）**：w1 两臂 rc=8 而外部判分 **30/30** ⇒ 「自测未达成」与「产物可疑」是**成对**告警、**不是**产物错判；`correctness_asserted=0` 已随台账落盘并被机检器读到。
- **④ AOT**：publish rc=0 · IL 警告 **0** · 15,778,672 B；聚焦测试 **21/21 绿**（`R1PipelineTests` + `R1ContractSemanticsTests`）。

## 4. 诚实边界（没测到就说没测到）

1. **`exec_precondition --round r539` = rc=1**（阻塞 = `w1/agentA1-on-t1` 26/30 · `w1/codex/t1` 29/30 · `w3/agentR1nr-t1` 28/30）⇒ 本轮**全部 token/调用降幅一律标「参考（未可验收）」，禁作验收依据**。
2. **role「生效」本轮未证实**：`role_note_chars=326` 只证明管道**自报**挂了 role；实发 dump 机检（`prefer_clarify_first` ∈ user 消息 ∧ ∉ 前缀/system）**三项全 False**。已核实 `analyze_r539.py` 的 `msgs_of()` 读 `blob["request"]["upstream_request"]["messages"]`，而 r539 的 `side-agent-*.json` 形状与该路径不符 ⇒ **机检器形状不匹配**（工具缺陷），**不得**据此断言「role 没上线」，也**不得**断言「已上线」⇒ 记「未证实」。
3. **外部真值列不可单窗读**：codex 调用数 **12 ↔ 347**（29×）、token **0.126M ↔ 25.0M**（199×）跨窗；且它在 **w1 也栽在 `jsonmini#14`**（与 `A1-on`/`R1nr` 同一条隐藏用例）⇒ 外侧对照只作「同窗存在且可判分」用，不作稳定基准。
4. **`ms1` 判分双读数**：运行树判 **3/3**，快照重判 **0/3**（快照不含 transcript 时的 fail-closed），而前置器在 `NONREQUIRED` 面给出 `correct=True 3/3` ⇒ 三读数并列登记，不挑一个报。
5. **未测**：全量测试（本轮只跑聚焦 21/21）· `g1` 游戏族 · `A1-on` 的 token 侧中继真值（取中继 usage，`unreported=0`）· role 轴在 codex 侧的对照。
6. **样本量**：`t1` 每臂 n=3 窗（R523「单窗=噪声」已满足）；`m1`/`ms1`/codex 侧 n=1~3 不等 ⇒ 只报逐窗 + 极差，不作稳定增益结论。
7. **同仓并发**：起手核无在跑作业（唯一 `dotnet` 残留是 02:49 的 idle MSBuild node，发布后 `build-server shutdown` + 复检 mem 2,663 MB ≥ 2,650 过闸）；兄弟会话 `cron:b15eb2f40a69` 上次执行 02:05–02:32 已结束（非并发写者）。

## 5. 下轮候选（R540）

1. **中枢修复外侧臂**：把 codex 引擎从「轮目录私有」提到稳定位置（或给 `load_codex_engine()` 加候选路径 + fail-closed 报错），并把「减法批删除前必须查**跨轮调用点**」做进机制（`d7821b7` 的漏检面）。
2. **role 实发机检修复并真验**：按 r539 dump 真实形状改 `msgs_of()`，重跑 role 轴机检（挂载类：有代码行 ≠ 生效）。
3. **未可验收面收口**：`jsonmini#14/#18/#22/#26` 是三臂（含 codex）共同失败面 ⇒ 归因是隐藏用例太难还是产物缺分支（非同源 oracle）。
4. **判据纪律**：若下轮要动 `evidence_scope` 的 require 面（例如把 `A1-on` 移出验收面），**必须先写后跑**并注明收窄理由。
5. 全量测试基线 + `g1` 族补测。
