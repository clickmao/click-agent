# R491 — 声明门真机闭环 · 回放配对剪裁 · 起手闸陈旧节点收口（全候选并轮）

- 轮号：R491（承 R490，`eval/rover/r491/`）
- 主线：R413（把 r1=llama.cpp 长驻端口接进链管道做真假信息判别/本地生成）
- 本轮性质：**全部候选并轮**（用户令 2026-09-16：全部候选 + 未闭合遗留并入同一轮解决，禁单步、禁只挑一个）
- 器具：`derive_r491.py` / `derive_analyzer_r491.py`（由 R490 机派生，承 R488 教训「臂/驱动器禁手抄」）

## 0. 因果链

R490 结束时留了四件事：①真机闭环的两个红（I5 剪裁打点红=Clone 未透传计数器；T2 臂被起手闸挡掉）②起手闸内存红只报「内存不足」，真因不明 ③R479 的「入链 prompt 正文槽位化」是否真接线无人取证 ④本地模板答复只剪了 assistant 侧，**user 侧仍逐字回放**。

R491 把四件事并轮做完，主线 KPI（用户一轮任务总 token ≥30% 降幅，主因=不必要远端调用减少）改用**同一 AOT sha + 同一 12 轮夹具 + 同窗**的单变量真机臂重测，并用「三跑取最差臂」代替单跑读数（R490 的教训：主 KPI 单跑=单次读数，不得作验收证据）。

## 1. 候选台账（逐项：做/未做 + 原因 + 证据）

| # | 候选 | 状态 | 结果/证据 |
|---|---|---|---|
| ① | 真机臂闭环（声明门 × 3 跑 + 下界） | **做** | B 17 调用/81,871 tok → T1/T2/T3 均 6 调用；最差 −67.54% tok、调用 −64.71%、空正文 3→0；20/20 不变式全绿（`verdict-r491.json`） |
| ② | 候选②⑥ 陈旧残留进程收口（起手闸内存阈值专项） | **做** | 收 4 个空闲 agenthost（76 MB）+ 1 个 178 MB 陈旧 MSBuild 节点 + 1 个 224 s 残留节点；`reap_orphans.py`（fail-closed，只读 /proc 事实） |
| ③ | 回放**配对剪裁**（零远端调用轮的 user 侧） | **做（代码+判据表；门开真机增益下轮）** | `ReplayPairTrim`（默认关）+ `ToQueuePrompt(prompt, pairTrim)` + 计数/打点/Clone 透传；基线 adj=20/leak=20 已机检 |
| ④ | R479「入链 prompt 正文槽位化」取证定性 | **做（只取证，不接线）** | 机检：`ResponsesWire`/`LocalDecisionMap`/`ActionToolSpec` 生产引用数各 = 1（全部指向自身定义文件）⇒ **链上 0 引用**，接线属改远端正文字节面的独立窗口 |
| ⑤ | 判据器升级（T 三跑离散度=下界；未跑臂禁静默豁免） | **做** | `T_spread` 输出 min..max；把 R490 的「任意未跑臂 blocking=False」改为显式 `OUT_OF_SCOPE` 白名单（本轮白名单为空 ⇒ 未跑即红） |
| ⑥ | 起手闸陈旧 build 节点 fail-closed 收口 | **做（含三态消融）** | `reap_stale_build_nodes`（O1..O5 判据）；A/B/C 三态：修前红 → 年轻节点拒收（不杀）→ 年龄达标收口放行 |

## 2. 主 KPI 读数（同 sha 8b4efbb7… / 同夹具 p12 / 同窗单变量）

| 臂 | 门 | 调用 | total tok | prompt tok | cached | 空正文 | 成本(¥) | vs B |
|---|---|---|---|---|---|---|---|---|
| B（Aroleb） | 关 | 17 | 81,871 | 76,129 | 65,408 | 3 | 0.026871 | — |
| T1 | 开 | 6 | 22,584 | 20,456 | 14,592 | 0 | 0.007864 | **−72.42%**（调用 −64.71%） |
| T2 | 开 | 6 | 24,262 | 21,608 | 15,616 | 0 | 0.008754 | −70.37% |
| T3 | 开 | 6 | 26,576 | 22,219 | 16,000 | 0 | 0.010792 | −67.54% |
| **三跑下界** | 开 | 6 | — | — | — | 0 | — | **−67.54%** |

- 判决：`verdict-r491.json` = **PASS**，不变式 20/20；R490 的 I5 红**转绿**（`replay_trimmed_calls=5 / sum=20`）。
- 用户验收线（≥30%）在**三跑最差臂**下仍 −67.54% ⇒ 结论不依赖最好臂。
- 质量面：四臂 `false_premise` 全 True（详见 §5 诚实边界）。

## 3. 代码事实（本轮改动，行号=当前工作树）

- `src/agent.modelqueue/ReplayPairTrim.cs:17,20,23,31` — 新闸（env `AGENTFRAMEWORK_REPLAY_PAIR_TRIM`，默认关；Decide/IsEnabled/Stamp）。
- `src/agent/modelqueue/ModelQueueAdapter.cs:35-39,70,84` — `ToQueuePrompt(prompt)` 单参重载委托两参版本；**配对剪裁**只在「紧邻前一条是 user」时剔除（`qp.History[^1].Role=="user"`）。
- `src/agent.modelqueue/ModelQueueRouter.cs:47,1423-1424` — 计数 `ReplayTrimmedLocalUserTurns` + 打点 `replay_user_trimmed`/`replay_pair_gate`。
- `src/agent.modelqueue/ActionLoop.cs:181` — Clone 透传新计数（R490 I5 红的同类面，防再犯）。
- `eval/rover/r483/preflight_gate.py:29,166,186,300,325-327` — 起手闸 `REAP_MIN_AGE_S=60`、`_has_live_driver_ancestor`（O5）、`reap_stale_build_nodes`（O1..O5 fail-closed）、`--keep-stale-nodes` 对照开关。
- `src/agent.tests/VerificationFormTests.cs:124-146` — **跨语言口径漂移修复**：投影规则表键 `non_semantic_families`（数据文件里 0 命中）→ `rules`（与 Python 侧 `face_record_canon._load_projection_rules` 同键），fail-closed 校验条目形态。
- 测试：`src/agent.tests/R491ReplayPairTrimTests.cs`（两态判据表）；套件总数 1,521 → **1,540**（+19 例）。

## 4. 器具修缮（本轮真踩到的坑，全部留在 rack 里）

1. **5 位端口字面量不受命名空间改写管辖**：`49010` 里没有 `r490` 子串 ⇒ 派生器只改 `r490→r491` 会把端口留在旧值。修法：显式端口映射 + 断言「改写条数 ≥ N」。（`derive_r491.py`）
2. **辅助器具必须同批携带**：R491 首跑链时 `run_arm_real_r491.sh` 调 `teardown_assert.py` 而该文件未随派生搬过来 ⇒ 链在第 3 臂后 `rc=11` 中断。修法：派生器新增 `carry_aux`（上一轮目录里 .py/.sh 全量携带 + 命名空间改写 + `py_compile`/`bash -n`）与 `check_refs`（派生脚本引用的文件必须存在，fail-closed）。
3. **链脚本重构会留下半截 echo 行**：head/tail 拼接法把「臂调用行」换掉却留下旧的成功回显 ⇒ 改为「按 PLAN 生成臂块（调用行 + 回显行成对）+ 复用源文件 ALLDONE 行」。
4. **判据器的「静默豁免」是自欺入口**：R490 版对**任意**未跑臂给 `blocking=False` ⇒ 未测面被算成通过。修法：未跑臂 = 红，除非在显式 `OUT_OF_SCOPE` 白名单内。
5. **注释与自检顺序**：`register` 的序列化器自检必须在**改动之前**做（改动后再比原字节必然不等，会恒拒写）。
6. **`dotnet build-server shutdown` 不是收口面**：本机实测返回成功 (`shutdown_done=True`) 后 178 MB 节点仍存活 ⇒ 闸只能红。修法：闸内追加 fail-closed 收口（候选⑥）。

## 5. 诚实边界（没测到就说没测到）

1. **候选③门开态的真机增益本轮未测到**：本轮冻结的被测二进制里该闸默认关（只跑了单测两态判据表 + 基线计数）。下轮才有真机臂读数。
2. **真假判别面本轮不区分 B/T**：四臂 `false_premise` 全 True（R490 的 B=False 未复现）⇒ 增益只按远端调用数/token 数计，**不**宣称「r1 判别力」带来的质量增益。R1 在链上的角色是本地生成/判别通道，其质量面需要更强的对抗族（下轮候选）。
3. **R 臂（只本地闸、声明门关）本轮未跑**：夹具计划里 R491 只排了 Aroleb + T×3；跨轮禁相减 ⇒ 不作任何 R 读数。`cross_round_ref` 里保留 R489 旧产物仅供参照。
4. **注册表的一处红 → 绿不是本轮的审计**：`r444.instrument-acceptance`（语义投影 pin）在 R491 窗口内被**并发会话**改写 —— `eval/rover/r444/verdict-r444-analysis.json`(16:04)、`eval/capability/instruments-check.json`(16:02) 均为对侧在写，其 pin 值在我两次提交之间从 `35811a35f750` 变到 `60f8eb4deccb`（我 `--only` 作用域未含 r444 ⇒ **不是我改的**；对侧亦可能跑了全表 bind）。该面（`instruments-check.json`）在本窗口内先后读到 `passed 26→24` 与 `23/27` 两种工作树形态 ⇒ **处于并发改写中**，故本轮不做该面的登记判定。R490 两行的 `evidence_generated_with`（R2f）由官方器具补齐（COVERED 122 → 124），`r476` 因证据在工作树未提交而降级为 live/worktree-only（合法形态），`r483b` 因本轮改闸重 pin 到 `04e207751c50`。
   - 共享件并发写风险（与 R485/R486 同一族）：`docs/verification-registry.json` 是读-改-写单据，本轮两次提交都把它整文件带出 ⇒ 若对侧按下标旧快照回写，本轮 4 行会丢失。恢复式：`git show a118dc2:docs/verification-registry.json`。
   - 套件终值：**1540/1540 通过**（对侧重审后 r444 亦绿）；本轮的 4 行登记 + 19 例新测试为自有产物。
5. **起手闸收口是「器具自证」级证据**：三态消融用的诱饵是人工构造的 `argv0=MSBuild.dll sleep`（非真 MSBuild），只证明**判据链**（年龄/静默/无监听/无驱动器祖先）可复现，不证明覆盖所有真实残留形态。
6. **R490 的两行登记缺 `evidence_generated_with`（R2f）已补**：用官方器具 `bind_evidence.py --apply --only … --round`（COVERED 122 → 124，读回 OK），不是手写字段。
7. **AOT**：`publish_and_il_check.sh` 出 `IL_warnings=0`（全体 warning=2，非 IL）、体积 15,367,840 B（sha12 `2f348d11c6c7`）；**被测臂二进制另有冻结副本**，sha12 `8b4efbb734781b80`（`/tmp/pub_r491_armfrozen/agenthost`）。

## 6. 下轮候选（R492）

1. **候选③门开真机臂**：以 `AGENTFRAMEWORK_REPLAY_PAIR_TRIM=1` 跑 T×3，验收 = pair_face `leak` 20 → 0 且 token 不升、`replay_user_trimmed>0`（非空判据）。
2. **candidate⑤ 对抗族升级**：真假判别面当前不区分 B/T ⇒ 加严（多轮前置真值 + 反事实改写 + 不可能前提），目标是让「无本地判别」臂可测地掉分。
3. **R 臂补跑**（本地闸 × 声明门关）以给出「声明门自身增量」的同轮分母（本轮靠跨轮参考，禁相减）。
4. **能力自检面重审**（`r444` + `instruments-check.json` 24/26）：先重审两个 DRIFT 器具的声明 sha，再决定扩展投影遮蔽族还是重 pin；**禁止**用遮蔽真实语义红来换绿。
5. **E2E 链级验收（用户口径：验收要真机场景链）**：把 R491 的「门 × 剪裁」组合接到一次完整用户任务链（含 MCP/工具调用 + 长上下文），给出总 token/调用数前后对比。

## 附：本轮命令与读数（可复现）

```bash
# 1) 起手闸（收口后）
python3 eval/rover/r483/preflight_gate.py --out /tmp/gateC.json --round R491-NC-C   # PASS, 收口 1 个残留节点
# 2) 真机臂（Aroleb + T×3）
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR bash eval/rover/r491/run_rest_r491.sh
# 3) 判决
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR python3 eval/rover/r491/analyze_r491.py
# 4) 套件 + AOT
env -u AGENTFRAMEWORK_PY_RUN -u AGENTFRAMEWORK_ARTIFACT_REPAIR $HOME/.dotnet/dotnet test src/agent.tests/agentframework.tests.csproj -c Release
bash eval/rover/r491/publish_and_il_check.sh
# 5) 登记（行数据 = rows_r491.json；绑定 = 官方器具）
python3 eval/rover/r491/register_r491.py --bind
```
