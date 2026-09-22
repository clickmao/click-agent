# R638 / EXP1-Q43 — 器具面健康三态归属 + 冻结 pin 定向重审（承 AN.11 候选并轮）

> 轮形：**卫生/器具轮**（零 `src/` 改动 · 零新臂 · 零远端 · 零新增夹具语义）。
> 跳步声明（预注册自陈）：跳步「构建/AOT」（零 `src/` 改动 ⇒ 无新二进制）· 跳步「产品侧最小改动」（无单变量轴）。
> 预注册：`eval/capability/exp1-q43/prereg_q43.json`（`written_before_any_measurement=true`，M1–M6）。
> 采集日 2026-09-22 · 本文件 sha256（前 16）：见下表逐件读数。

## 1. 面基建读数（真机全量面）

- 命令：`python3 eval/capability/instruments_check.py`（31 器 / 68 命令）
- 读数：**可判据 19/29 通过 · 信息项 2/2 单列**（信息项 = 自指成员 `bind_evidence.check` / `bind_evidence.committed-state`）
- 落盘：`eval/capability/instruments-check.json`（291,656 B，canon-split 运行期字段另落 `.runtime.json`）
- **可比性声明**：仓内最近一次登记的面读数来自 **R516 时代**（`27/29`，committed 于 2026-09-17）⇒ 与本次读数**不可直接相减**，只做**逐条差集**（下表）。

## 2. 红项三态归属（逐条机检 · 禁单选归因）

| 面项 | 基线 rc | 归属 | 根因（证据） | 本轮处置 | 复跑读数 |
|---|---|---|---|---|---|
| `hooks.pre-commit` | 1 | **self** | 本侧改器具（两件 Q42 器具加负控臂）未刷登记表绑定 | 定向 repin（`bind_evidence --only … --round R638 --apply`，登记表 numstat **4/4**） | **rc=0**（scoped 面） |
| `bind_evidence.check` | 2 | **self** | 同上（同一 VIOLATION 的两个消费点） | 同上 | **rc=0**（scoped 面） |
| `r444.instrument-acceptance` | 违规 | **self** | 全量面重写其绑定的语义投影件（`instruments-check.json`），投影随真读数变化 | 定向 repin（`--only`，仅 2 行） | `bind_evidence --check` **rc=0 / 违规 0** |
| `exp1q31.stage-guard-hook` | 2 | **self（污染）** | 早先一次越长越界的面调用改写了 10 件被 pin 的面输出件 | 逐件 `git checkout --`（复原到 HEAD，**不动声明**） | **rc=0**（scoped 面） |
| `external.contrast-exec-precondition` | 1 | **foreign（对侧轮次遗留）** | R631 改器具（`af9bb7ae`）未重审其**冻结 pin**（声明 `28770b831e52` / 现盘 `67fba76283b7`） | 定向 repin：**只刷 `artifact_sha12`**，`pin_status` 保持 `frozen` / `pin_reason=archived-per-round`（scratch 副本预演 → 真表落盘） | 形式门禁转绿；该器**自检 FAIL + 声明字段异常残留**（结转） |
| `exp1q31.cap-headroom` | 2 | **pre_existing（结构性闸）** | `P2 余量不足: soft_cap/log_bytes=1.318 < K_MIN=2.00 ⇒ 扩面前先复测并抬阈值` | 未修（闸的自我裁决即为「先复测再扩面」） | 仍 rc=2 |
| `exp1q38.dir-node-archive` | 2 | **pre_existing** | 守恒式 `c3_nontrivial_face=False`（面非平凡性判据为假） | 未修（需独立定因轮） | 仍 rc=2 |
| `r444.prefilter-precheck` | 3 | **pre_existing** | 输入缺席 `MISSING_FILE:eval/rover/r441/…` | 未修 | 仍 rc=3 |
| `r444.analyze` | 1 | **pre_existing** | 同上族 | 未修 | 仍 rc=1 |
| `r446.judge-precheck` | 1 | **pre_existing** | 未定因 | 未修 | 仍 rc=1 |
| `exp1q2.docref-selftest` | 3 | **pre_existing** | 环境不可判 | 未修 | 仍 rc=3 |
| `external.contrast-interaction-kpi` | 0/substr | **pre_existing** | 声明字段 `input_surface_source` = `BAD/MISSING`（枚举外取值） | 未修 | 仍 FAIL |

**归属纪律**：`self` 只在**本侧动作时间线**内成立（器具改写 / 面调用）；`foreign` 钉到**不可变提交号**（`af9bb7ae` 是 HEAD 祖先）；其余记 `pre_existing` 并**逐条点名结转**，不用「红数下降」掩盖。

### 2b. 面跑的**破坏性副作用**（本轮自捕，未定因，单列）

- 事实：本轮全量面 + scoped 面 + `status_gen.py` 重生成之后，工作树出现 **526 件 track 文件被删除**（全部位于 `eval/capability/exp1-q38/archived_deps_depth3_dirs/**`）。
- 处置：逐件 `git checkout --` **从 HEAD 复原 526/526，零丢失**（复跑 `git status --porcelain | grep -c '^ D'` = **0**）。
- 嫌疑（**未定因，禁单选归因**）：`exp1q38.dir-node-archive` 的负控臂在面内打印 `NEG-CONTROL remove_file: None`，且该器同时报 `c3_nontrivial_face=False` ⇒ 该器的**负控可能是破坏性的**（删归档件）。**未做**复现确证（需独立轮在 `/tmp` 副本上重演）⇒ 记为「本轮观测到的破坏性面副作用 + 嫌疑件」，不作结论。
- 推论（纪律层）：面跑**不得假设无副作用**；跑面前后都必须有「track 删除数」的守恒读数（本例：跑前 0 / 跑后 526 ⇒ 若能先落这个读数，破坏性副作用当场可见）。


## 3. 候选逐项结论

| 候选（AN.11） | 结论 | 真机读数 |
|---|---|---|
| #6 两器入面（31→33） | **被面自身容量闸否决 ⇒ 登记行不落盘** | `exp1q31.cap-headroom`：`n_instruments=31 / n_commands=68 / log_bytes=76,369,420 / headroom=1.318 < K_MIN=2.00` |
| #1 序列化形态统一 | **预注册被证伪 ⇒ 零改动，开独立轮** | 含 `indent=1` 的 .py **606** 件；其中**活通路 8 件**（`roundcheck.py` / `gen_csharp.py` / `delete_ref_gate.py` / `run_round.py` / `run_probe.py` / `exec_precondition.py` / `kpi_probe.py` / `decl_sweep.py`）≠ 0 |
| #5 产物件尾 LF | **结转**（重开条件未满足） | R481（`189f206a`）以来新增 `.json/.jsonl` **253** 件，**220 件缺尾 LF（87.0%）** |
| #2 H6 通知件 >0 现场事件 | 未做（真仓干净态不可达，禁夹具顶替） | — |
| #3 写侧运行时探针 | 未做（重开条件 = 出现可观测真实写入路径） | — |
| #4 对侧 P1 | 未做（属对侧） | — |

## 4. 两件新器具的**有牙负控**（已就位，登记受闸待解锁）

| 器具 | `cmd` 读数 | `--neg-control` 篡改 | 负控读数 | 非空心证明 |
|---|---|---|---|---|
| `eval/capability/exp1-q42/verify_replay_archive_q42.py` | rc=0 · `VERDICT=PASS` | 把**一条违规行的原因码**换成「合法但含标记」的伪码（只动 V1 的输入） | rc=**2** · `red_checks=['V1_scopeA_single_reason_no_false_positive']` · `NC_DETECTED` | 篡改**未被捕获**时退 **0**（⇒ 面侧 `nc_expect:nonzero` 判红），故非恒真 |
| `eval/capability/exp1-q42/nc_prestate_q42.py` | rc=0 · `VERDICT=PASS` | 把对照物从钉死的 `ecd363d` 换成浮动 `HEAD` | rc=**2** · `red_checks=['N1_pre_sha_is_ancestor_and_differs','N2_prestate_has_only_old_expectation']` · `NC_DETECTED` | 同上（未捕获 ⇒ 退 0） |

## 5. 门禁与收口读数

- 形式门禁（本文件的两件 `covers` 之一）：`dotnet test … --filter "VerificationForm|SkillGeneralization|DevPlanDocRef"`
  - 首跑：`Failed 1 / Passed 13 / rc=1` —— 红 = 上表 `foreign` 那条冻结 pin（**修复前读数原样保留**，`eval/capability/exp1-q43/formgate_q43.txt`）
  - repin 后：**`Failed 0 / Passed 14 / rc=0`**（`formgate_q43b.txt`）
- `python3 eval/capability/bind_evidence.py --check`：违规 **2 → 0**（`bind_check_before_q43.txt` / `bind_check_after_q43.txt`）
- 登记表 numstat：**6/6 行**（3 处定向 repin；全表口径分布不可比 —— 工具自带 `DIST_SCOPE=only(n=…)` 声明）
- 文献小步：出口直探 **HTTP=200 / 0.48s**（可达 ⇒ 空采信可归因检索式）；3 次 query 的引号短语均被工具面拆散（8.6 万–39 万条）⇒ **0 采信**，连续 0 采信计数 = **1**（不降频）
- 未 push（推送暂停令在效）；本轮零 `src/` 改动 ⇒ 无能力分数、无 `kpi.jsonl` 行（与 Q39–Q41 同例）

## 6. 复现命令（逐条可独立复核）

```bash
cd /home/agentuser/AgentFramework
# 面读数（全量 / 定向）
python3 eval/capability/instruments_check.py
python3 eval/capability/instruments_check.py --only hooks.pre-commit --out eval/capability/exp1-q43/face_scoped2_q43.json
python3 eval/capability/instruments_check.py --only exp1q31.cap-headroom,exp1q31.stage-guard-hook,exp1q38.dir-node-archive,external.contrast-exec-precondition,external.contrast-interaction-kpi --out eval/capability/exp1-q43/face_scoped3_q43.json
# 两件器具的有牙负控（应退非零）
python3 eval/capability/exp1-q42/verify_replay_archive_q42.py --neg-control
python3 eval/capability/exp1-q42/nc_prestate_q42.py --neg-control
# 两条只读普查（M3 / M4）
python3 eval/capability/exp1-q43/census_q43.py
# 台账/证据一致性
python3 eval/capability/bind_evidence.py --check
# 形式门禁
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR dotnet test src/agent.tests/agentframework.tests.csproj --filter "FullyQualifiedName~VerificationForm|FullyQualifiedName~SkillGeneralization|FullyQualifiedName~DevPlanDocRef" --nologo -v q
```

## 7. 诚实边界

1. 面读数在**脏工作区**取得（仓内 83 件历史未跟踪件在场）⇒ 与「干净态」读数**不可直接比**；本轮已把本侧造成的 10 件污染复原到 HEAD。
2. `cap-headroom` 的 `log_bytes`（76.4 MB）**构成未定因** —— 只读到总量与阈值，未定位到构成件（下轮）。
3. 两件新器具的**登记行未落盘** ⇒ 器具面仍 **31** 件（扩面受闸）；它们的 `covers` 因此暂由本文件与计划文档承担。
4. 冻结 pin 的 repin 属**对侧轮次遗留**的修复：`self`/`foreign` 读数已分列，未写成对侧成果。
5. `r444.instrument-acceptance` 的语义投影 pin 会在**每次全量面**后被重写 ⇒ 该行**天然要求面后重审**；本轮按该设计重审一次（不静默降级）。
6. 未测到：`cap-headroom` log_bytes 构成 · 6 条 `pre_existing` 红的根因 · 尾 LF 写入器缺口的生产写侧归属。

## 8. 工件 sha256（前 16 位，采集于 2026-09-22）

| 件 | sha256[:16] |
|---|---|
| `eval/capability/exp1-q43/dag-r638.md` | `f5f5672d71bce559` |
| `eval/capability/exp1-q43/prereg_q43.json` | `0fdef0c35189e40a` |
| `eval/capability/exp1-q43/census_q43.json` | `759b94c19d3c42db` |
| `eval/capability/exp1-q43/face_before_q43.txt` | `5afde8538132db5e` |
| `eval/capability/exp1-q43/face_scoped2_q43.json` | `2180d991aa3aa872` |
| `eval/capability/exp1-q43/face_scoped3_q43.json` | `549e5eace8e422af` |
| `eval/capability/exp1-q43/formgate_q43b.txt` | `09c4137cf45c430f` |
| `eval/capability/exp1-q43/bind_check_before_q43.txt` | `6516caa0434e46d7` |
| `eval/capability/exp1-q43/bind_check_after_q43.txt` | `29a806301827c5c9` |
| `eval/capability/exp1-q42/verify_replay_archive_q42.py` | `76639858271bf9f2` |
| `eval/capability/exp1-q42/nc_prestate_q42.py` | `4de2e3d121215fa8` |
