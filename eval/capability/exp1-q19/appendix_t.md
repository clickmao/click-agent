## 附录 T — EXP1-Q19（2026-09-15）L2 器具登记：契约字段面落地 + 全量面复跑（含证据覆盖闸）

**本轮只做一步**：L.8 候选① 的**登记写入与机检扩展**（候选① 原文为「对侧空闲 + 全量面复跑」——
对侧本轮**活跃**，故只做不依赖 dotnet 的登记与 python 机检面；形式校验仍结转）。
改动面 = `eval/capability/instruments.json` + `eval/capability/instruments_check.py` + `eval/capability/exp1-q19/`
+ 两处**器具自身**的写入面修正（`exp1-q17` 无改动，`exp1-q1/selftest_scope.py` 补 `--out`）；
**未动** `src/`、`skills/`、`docs/verification-registry.json`、`eval/rover/`、任何 `probe_*.py`、任何既有语料产物。

### T.1 起手闸（先读数，后动手）

| 闸 | 读数 | 判定 |
|---|---|---|
| 对侧并发 | `r462_w_bench.py`（arm 3/5 `qwenpaw-flash-2b-q4km`）+ 其 `llama-server` + 自匹配 1 条 = 4 | **活跃** ⇒ 零 dotnet |
| 内存 | `MemAvailable 1860MB` < 2600MB | **未过** ⇒ 零 dotnet |
| 写者仲裁 | `.git/ROUND_CLAIM` 不存在 | 无抢写冲突 |

`eval/capability/exp1-q19/gate_q19.json` 留档（含对侧 pid/ppid/cmd 逐条）。

### T.2 契约 L2 缺什么（机检后补）

契约 §L2 要求每器具登记：`id` / **版本** / `self_test_cmd` / **负控** / **输入指纹（sha256）** / 口径四元组。
登记表现状（11 行）= `cmd` / `nc_cmd` / `kpi_quad` —— **版本、输入指纹全缺**，且**没有任何机检**读这三项。

本轮补齐并**让机检去读**（新增字段一律由**文件字节派生**，不手打）：

| 字段 | 来源 | 机检 |
|---|---|---|
| `version` + `version_source` | 器具内声明的 `*_version` 常量（**排除** `prereg_*`），否则 `content-sha12:<sha>` | 形态一致 + 声明态取值合法 |
| `instrument_sha12` | 器具文件 sha256[:12] | **重算比对**（漂移 ⇒ 判红） |
| `input_fingerprint` | `[{path, sha12}]`（cmd 字面量抽取 ∪ 读数声明；输出参数后的路径剔除） | **重算比对 + 路径必须存在** |
| `kpi_quad` | registry schema {单位,分母,真值源,口径档} | 四键齐备 |

**机检自身也要有负控**：`--fingerprint-drift-inject` 在内存中篡改首条被选行的指纹期望值 ⇒ 必须判红。

### T.3 双证读数（先跑，后登记）

`eval/capability/exp1-q19/l2_probe.json`（正控 rc/marker + 机械负控 rc）——**只有双证成立才写进登记表**：

| 器具 | 正控 | 负控（注入/缺输入） | 双证 |
|---|---|---|---|
| `exp1q11.other-bucket-decompose` | `RESULT: PASS` | 缺语料 ⇒ rc=3 | ✅ |
| `exp1q15.unit-axis-guard` | `SELFTEST 10/10 pass` | 缺 cites rc=2 ｜ Q18 冻结 **VOID 臂** rc=2 | ✅ |
| `exp1q15.unit-axis-guard-q16` | `SELFTEST 14/14 pass` | 缺 cites rc=2 | ✅ |
| `exp1q17.archive-field-provenance` | `checks 15/15` | VOID 臂 rc=2 ｜ 缺归档 rc=3 | ✅ |
| `exp1q18.rebuild-constructor` | `BUILDER_OK` | 注入变异源版本 ⇒ `NC_OK`、dst 未写、rc=3 | ✅ |
| `exp1q13.index-scope-out-classifier` | `"all_pass": true` | **无外部注入入口** | ⛔ `pending_nc` |

双证 5/6；未登记的那一件**不补假负控**，记 `pending_nc` 待下一轮补入口。

### T.4 全量面复跑（收敛过程如实入档）

首轮与后续各轮读数（`evidence_q19.txt` 为全文）：

| 轮 | 读数 | 结果 |
|---|---|---|
| 首跑 | 11 行时代 + 新行写入前 | 17/17（但**尚未有副作用闸**） |
| [D] | 机检自身负控 | `rc=1` + `DRIFT(want=deadbeef0000 got=…)` ⇒ 负控成立 |
| [A] | 改了 `instruments_check.py` 后 | 机检**当场抓到自己的登记漂移**：`instrument_sha12 DRIFT(want=bf9d38151bb0 got=601c9fb3683b)` ⇒ 机制非空心 |
| [F] | 加入副作用闸后 | **16/17**：`SIDE-EFFECT ⇒ ['exp1-q17/selftest_q17.json','exp1-q17/verdict_q17.json']` |
| [G] | q17 输出改落 scratch | 16/17：`SIDE-EFFECT ⇒ ['exp1-q1/selftest.json']`（另一件旧器具同病） |
| [H] | q1 加 `--out` | 16/17：`--out` 被 unknown-arg 闸拒（rc=2）⇒ 白名单同步补 |
| **[I] 终态** | **17/17，`rc=0`，副作用面为空** | ✅ |

### T.5 本轮发现的**器具缺陷**（三件，全部自捕，均非被测对象缺陷）

1. **负控模式覆盖正控证据**：`--fingerprint-drift-inject` 原先把结果写回 `instruments-check.json`
   ⇒ 正控证据被负控读数的 0/1 覆盖（首跑实测发生）。修 = 负控模式独立命名空间 `instruments-check-drift.json`。
2. **器具把结果写回「轮次证据路径」⇒ 复跑即证据降级**（两件）：
   - `exp1-q17 --selftest` 默认 `--out` = `verdict_q17.json` ⇒ 复跑把 **C12 确定性块抹成 `determinism: null`**（实测 diff）；
   - `exp1-q1/selftest_scope.py` 硬编码写 `selftest.json`（无 `--out`）⇒ 同类。
   修 = 器具输出指向 scratch 目录（q17 走命令行 `--out/--fixtures-out`；q1 补 `--out` + unknown-arg 白名单同步）。
   两支被弄脏的轮次证据已 `git checkout` 复原（复原后 `git status` 干净）。
3. **登记表的命令面必须「以读数为单源」**：首版写入器只刷新字段、不刷新**已存在行**的 `cmd`
   ⇒ 改了器具调用方式却仍跑旧命令（实测发生，第 [F] 轮仍复现同一条副作用）。修 = 已存在行按读数刷新 `cmd`/负控面。

**新增机器闸（本轮产出，防该类缺陷复发）**：全量面收尾比对 `git status --porcelain -- eval docs`
前后差集，白名单只放行全量面自身产物与 scratch ⇒ 出现**新的脏文件**即判红（`SIDE-EFFECT: …` + `side_effects[]` 入档）。
它先在**未修状态**下报红（复现缺陷），后在**修正状态**下为空（证明闸有判别力，而不是恒绿）。

### T.6 诚实边界（不得越读）

1. **旧 11 行指纹 n=0**：其 `cmd` 字面量不含输入路径（输入面在驱动脚本／内部 fixture）⇒ 指纹面只覆盖新登记的 exp1 行。
   **不得**宣称「全部器具输入已冻结」。
2. **口径四元组命名分叉**：契约文本 {分子范围,分母来源,本地入账,截断规则} vs registry 实际 {单位,分母,真值源,口径档}。
   机检按 registry；不伪造契约命名的内容，冲突登记待裁定。
3. **形式校验仍结转（第五轮）**：对侧活跃 + 内存未过闸。登记表改动**尚无** dotnet 侧消费者
   （`status_gen --check` 只读 `docs/verification-registry.json`），故本轮不构成「未跑校验的登记宣称」。
4. **q1 器具被本轮改动**（补 `--out` 与白名单）：其 `instrument_sha12` 随之更新为 `content-sha12` 新值；
   默认行为（无参调用）逐字未变 —— 但不构成「该器具语义已复核」，只声明**写入面**变了。
5. **测量窗口非纯净**：对侧 bench 在场；本侧全程静态 python，未用模型/未跑 dotnet。
6. 证据等级 **L2-static**（真机执行 + 双证 + 字段重算 + 副作用闸），无编译/测试/AOT ⇒ 不报 L3/L4。

### T.7 下轮候选（L.8 剩余项）

① **形式校验结转清账**（需对侧空闲）→ ② 旧 11 行输入指纹补全 + `exp1q13` 负控入口 → ③ relocated 面正例语料（独立预注册轮次）→ ④ 阶段 B 可配语言集（独立预注册轮次）。
