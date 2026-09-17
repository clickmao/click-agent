# R503 — 题集扩面 v3 + 守卫归因穷举 + 冻结行重钉裁定

日期: 2026-09-17 · 树态: /home/agentuser/AgentFramework (git 本地, `.git/PUSH_PAUSED` 在位 ⇒ 禁 push)
主线: 用户 2026-09-17 钦定 — 用「随机游戏 / 数学难题 / 程序题」真实开发任务, 与外部真值 (codex-cli, 同一真实模型) 在**同环境·同输入·同模型**下对照自检 (方法载体 `docs/external-reference-harness.md`)。

---

## 0. 因果链

1. R502 首跑对照 (6 题: 4 程序族含 1 游戏族 `life_k` + 2 见证族) ⇒ 两面 6/6 整题全对, 但**只 1 个游戏族** ⇒ 主线的「随机**游戏**」覆盖面不足, 判据的外部效度受限。
2. 扩面必然改 `eval/probe/*` (声明器具) ⇒ 门禁 `bind_evidence --check` 立刻报 `R2E_R2F_EXIT=2` (两条冻结行 `probe.randomized-selfcheck` / `r433.probe-code-source-artifact-channel` 的 `instrument_sha12` 与现盘不符)。
3. R501 候选① 写作「t8 guard `question_mark` 误拒 ⇒ 修链」。**本轮机检该诊断不成立**: R501 t8 遥测 `src_len=612 / msg_len=5` ⇒ 本地输出只有 5 字且带问号, **长度带 (⑦) 同样必拒**; 且本地提示第 4 条本就写着「不得反问、不得提问, 输出中不得出现问号」。⇒ 真实病因 = **引擎退化 (把 612 字原文写成 5 字反问)**, 不是守卫误判; 守卫 fail-fast 只报了**先撞上的那一条**, 才把病因伪装成 ②。若照候选① 原样放宽 ②, 反而会削弱一条正确判据。
4. 由此定本轮三件: ① 题集扩面 (游戏族 1→2, 见证族 2→3) ② 守卫**归因穷举**(不改判定语义, 只让「为什么拒」不再撒谎) ③ 冻结行**重钉裁定** (器具改 ⇒ 重审 + 重生成证据).

---

## 1. C1 题集扩面 v3 (新增 2 族)

器具改动 (`eval/probe/`):

| 文件 | 新增 | 性质 |
|---|---|---|
| `tasks.py` | 游戏族 `sub_game` (减法博弈: ref=正推 DP / check=记忆化递归极小极大, 双路径必需一致才发题); 见证族 `witness_mod_inverse` (ref=朴素扫描 / check=`pow(a,-1,p)`); `HARD_INPUTS["sub_game"]` 6 条 (含 `2 2 / 1 3` ⇒ LOSE 等) | 纯扩面 |
| `grade.py` | 见证判定分支 `mod_inverse` (验语义: `0<=x<p ∧ (a*x)%p==1`); selftest +4 (39) | 纯扩面 |
| `run_probe.py` | `REF_SRC["sub_game"]` (独立参考程序) + 负控 `mutation:sub_greedy` (恒取最大 ⇒ 必假) + 2 条 selftest (31) | 纯扩面 |

**自检三连 (每条跑 2 次, rc=0, 逐条 PASS)**:

| 器具 | 自检 | R502 基线 | R503 |
|---|---|---|---|
| `tasks.py --selftest` | 发题器 | 45/45 | **53/53** |
| `grade.py --selftest` | 判定器 | 34/34 | **39/39** |
| `run_probe.py --selftest` | 编排器 | 29/29 | **31/31** |

**冻结题集 v3** (`eval/rover/r503/taskset-r503.json`): 8 题 = 5 程序族 (`life_k`, **`sub_game`**, `topo_min`, `vm_run`, `json_mini`) + 3 见证族 (`witness_sqrt_mod`, `witness_min_counterexample`, **`witness_mod_inverse`**); file sha256 `3e648f5b2ee9…`, 探针口径 sha `929a88e1b02cdccf`。构造法 = 逐族定向 dump 后**机合并** (`eval/rover/r503/build_taskset_r503.py`, 逐族 1 题, 合并前断言族名唯一/旧 tid 不泄漏/无残留)。

**oracle 正控 (本地, 8 题 70 用例)**: `70/70 = 1.0000`, 8 族全 1.0 (`sub_game` 12/12, `witness_mod_inverse` 1/1) — 4.63s。

**负控 (`eval/rover/r503/nc_r503.sh`, 全绿 `NC 总判: OK`)**:
- NC1 `json_mini` oracle 1.0 / `mutation:json_loose` 整题 0
- NC1b `life_k` oracle 1.0 / `mutation:life_wrap` 整题 0
- NC1c **(新)** `sub_game` oracle **2/2** 整题全对 / `mutation:sub_greedy` 整题 **0** — 用例级 rate=0.2083 (>0 属正常: 贪心在多数局面与最优手同值) ⇒ 此处**判红口径必须取整题**, 与 R502 NC 口径一致 (这行本身就是一次口径修正, 见 §4)
- NC2 缺侧 rc=3; NC3 预注册三态 `{uniform:0, drift:1, missing:3, restored:0}`; NC4 外部真值解器 selftest 6/6; NC5 dry-run rc=0

---

## 2. C2 守卫归因穷举 (判定语义不变, 归因不再撒谎)

文件: `src/agent.modelqueue/LocalParaphraseChannel.cs` · `Guard()`

- 改动前: 逐条 `if (违规) return Reject("<名>")` ⇒ **fail-fast**, 只报第一条。
- 改动后: 前置不可判项 (`source_empty` / `empty_output`) 仍单条早返; 其余 6 条 (②`question_mark` ③`think_leak` ④`identifier_lost` ⑤`identifier_added` ⑥`claim_added` ⑦`length_band`) **逐条穷举**, 破几条报几条 (固定序, 名+界值 ≤2 项/条)。
- **接受/拒绝集合逐位不变** (同名判据, 只是不再短路) ⇒ 对 token / 远端调用数**中性**; 价值 = 归因可核 (R494「真值必枚举全部 Emit 点」同款纪律).

测试: `src/agent.tests/R498LocalParaphraseTests.cs` 新增回归 `守卫_归因必须穷举_R501_t8_实证形状`: 原文 612 字 / 输出 `要继续吗？`(5 字) ⇒ 必须**同时**报出 `question_mark`+`identifier_lost`+`length_band`; 并附负向对照 (单条违规仍须单名, 不得见规则就拼)。`R498LocalParaphrase` **33/33** 通过。

---

## 3. C3 冻结行重钉裁定 (器具已改 ⇒ 重审)

机检触发: `bind_evidence.py --check` ⇒ `R2E_R2F_EXIT=2`, 两条 VIOLATION。裁定 (**扩面不改既有判据 ⇒ 重钉, 而非降级/删行**), 器具 `eval/rover/r503/ruling_r503_repin.py` (定向 `--only`, 保留现盘格式, 幂等, 改前打印 diff 计划):

| 行 | 器具 | instrument_sha12 | artifact_sha12 | audited_by_round |
|---|---|---|---|---|
| `probe.randomized-selfcheck` (L4) | `eval/probe/tasks.py` | `32815065ff7a` → `9c8f09e3ff8f` | `00a88bf4cba1` → `0cdf31bdb101` (证据**重生成**) | R502 → **R503** |
| `r433.probe-code-source-artifact-channel` (L3) | `eval/probe/grade.py` | `ef0a81d495ee` → `21a33eaeb660` | `04b4b41e39c3` (历史归档 md, 不重生成) | EXP1-Q34 → **R503** |

**证据重生成** (行 1): `python3 eval/capability/exp1-q28/gen_probe_evidence_q28.py --out eval/capability/exp1-q28/probe_selfcheck_evidence.json` ⇒ P1–P8 全绿, 三阶段读数 `[[53,53],[39,39],[31,31]]` rc=0, 产物内 `provenance.instrument_sha12=9c8f09e3ff8f` 自证一致。
（副作用留痕: 本次产物 `write_face.status=has-repo-writes`, 动因 = `run_probe --selftest` 会写 `data/probe/replies/*.txt` (含新增族 `mutation_sub_greedys0-p00{2,3}.txt` / `oracles0-p004.txt`); 与 R502 同机制, 非新增行为。）

**正控/负控 (全部机检)**:
- 正控: 重钉后 `bind_evidence.py --check` ⇒ `R2E_R2F_EXIT=0`, 无 VIOLATION; `dotnet test --filter VerificationFormTests` **7/7 通过** (改前是 1 failed)。
- 负控 N1: 在 scratch 副本上把行 1 的 `instrument_sha12` 钉成 `deadbeefcafe` ⇒ 门禁立刻报 **2 条** VIOLATION (含产物自证 `9c8f09e3ff8f` vs 声明 `deadbeefcafe`) ⇒ 门禁非空转。
- 负控 N2: 同一 scratch 副本按真值重钉行 1 ⇒ 行 1 消失, 仅余行 2 (未重钉) ⇒ 门禁按行定位, 不误伤。

裁定理由 (为什么**不**改 claim 文本): registry 的 `capability`/`negative_control` 是**带轮号的史实句** (如「R398 真机…」「grade.py --selftest 34/34」), 在句内追加 R503 会混轮 ⇒ 重审结论落本文档 + `docs/improvements.md`, registry 只动 3 字段。行 2 的归档 md 不重生成 (它记录 R433 当时的读数), 其器具增量已核为**纯扩面** (既有断言语义逐条未动)。

---

## 4. 诚实边界

- **本轮的 `sub_game` 扩面只到「发题器/判定器/编排器 + 本地 oracle/负控」**: 真机两面 (codex / agent) 对照读数见 `eval/rover/r503/verdict_r503.json` (本轮同窗); 未跑: 人评质量面 (n≥3)、遥测直写并发面、全量 n≥10。
- **C2 对 token/远端调用数的影响 = 中性 (0)**: 它不改判定集合, 只是归因穷举。**不得**把它算进「token ↓≥30%」的任何功劳。
- R501 候选① 原诊断 (「②误拒」) 本轮**被证伪并收窄为**: 「②③④⑤⑥⑦ 短路导致的**归因不全**」; 引擎退化 (612→5 字) 本身**未修** (属本地引擎能力面, 需另立证据, 不在本轮)。
- 行 2 的证据面是**历史归档** (未重生成) —— 这一条是**声明过的缺口**, 不是「已重生成」; 若后续要它也能重生成, 需要先建 r433 可重放夹具 (下轮候选)。
- 本轮未做 AOT 之外的性能面读数; AOT 二进制 `/tmp/pub_r503/agenthost` 15,409,088 B (sha256 `0431c3da97a4cc88…`), IL 类 (`warning IL####`) 警告 **0** (`warning` 总数 8 = NU1510×? + CS8625×? 既有告警, 与 R502 发布同族).

---

## 5. 下轮候选

1. **(主线) 扩面 v4**: 第二程序族陷阱 (`pair_closest_abs_sum` 已在题集内) → 增**图论游戏族** (`wythoff`/`nim_multi`, 需含必胜手唯一性证明) + 见证族 `witness_crt`; 目标 10 题, 保持「同环境同输入 md5 一致才开跑」。
2. **(链) 本地引擎退化面**: R501 t8 形状 (612→5 字) 需**独立证据**: 用 `eval/capability/*` 自检循环扫 3B 引擎在「长原文 (≥600 字)」上的退化率 ⇒ 若显著 >0, 再谈「按长度分档的本地吸收策略」(可能真降远端调用).
3. **(归档) r433 可重放夹具**: 让行 2 的证据面可重生成 (当前为史实 md).
