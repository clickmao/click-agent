# R516 轮志: 节点成功必须绑产物证据 + 节点写范围契约 (fail-closed)

DocRef: `docs/plans/v1.00.0-r516-node-scope-contract.md` · 前态锚: `eval/rover/r515/evidence/report-orch-v2-12step.json`
主线: `docs/reports/iteration-master-plan.md` §0-0 铁律 10 (外部真值对照自检) · 铁律 11 (exec_precondition 前置闸)

## 1 因果链
R515 真机 12 步臂抓到的**假绿**:远端节点 `n4` 178 ms、`n3` 5 ms 即 Completed, 但工作区**零产物** (归档可查) ⇒ 「节点成功」与「真实交付」之间没有机械绑定;
R515 v2 的修法只是把范围写进**提示词**, 属软约束, 无机器可检机制。R516 把这条链**机制化**:① 节点成功必须绑工作区磁盘证据 (否则判 Failed);
② 写范围从提示词升级为**范围文件 + 机检** (越界写 ⇒ Failed 且点名路径);③ 同层 (会并发) 写范围重叠 ⇒ **建立 agent 之前** rc=2 拒收 (零 LLM 调用);④ 产物归属统一由编排器 (单一权威源) 负责, 宿主侧重复实现删除。

## 2 落地 (代码事实)
- 新件 `src/agent/intent/NodeScopeFile.cs`(9,204 B):DSL `nodeId | 路径[,路径]`;fail-closed 解析;`InScope/Matches/Overlaps`;`Validate` (未知节点 + 同层重叠)。
- `src/agent/intent/TaskOrchestrator.cs`:`WorkspaceRoot`/`NodeScopes`/`RequireScopedArtifacts` 三选项;**逐节点快照差** (`Snapshot/Diff`) 取代宿主实现;`ScopeViolations` 台账;`NodeTelemetry.Scope/Artifacts`;`ValidateScopes` 静态门面。
- `src/agent.host/OrchestrateCommand.cs`:`--scope` 参数;范围校验在 **agent 建立之前**(零 token)⇒ 失败 rc=2;宿主 `Snapshot/Diff` 实现删除 (单一权威源);报告新增 `scope_file` / 节点 `scope` / `files` / `scope_violations` / `scope_undeclared`。
- 新测 `src/agent.tests/TaskOrchestratorScopeTests.cs`:22 例 (零产物/越界/删除越界/范围内完成/未声明旧行为锚/同层重叠拒/跨层允许/未知节点/DSL 负样本/段边界匹配/本地节点亦受绑)。

## 3 真机 5 臂 (AOT + adapter 真值 + 真模型, 判据器只读落盘)
| 臂 | 二进制 | 计划 (逐字节 md5 一致) | rc | 节点判定 | 机检读数 |
|---|---|---|---|---|---|
| RED | R515 旧 AOT | plan-red.txt | 0 | Completed | 报告**无 scope 字段** ⇒ 前态确无机制;`files=['A answer.txt']` |
| G1 | R516 新 AOT | plan-red.txt + `--scope scope-red.txt` | 1 | **Failed** | `no_artifact`「节点无产物 (假绿防护)」 |
| G2 | R516 新 AOT | plan-write.txt + `--scope scope-write.txt` | 0 | Completed | `files=['A out/hello.py']`, 违约 0 ⇒ **真干活节点不误杀** |
| G3 | R516 新 AOT | plan-outside.txt + 同 scope | 1 | **Failed** | `out_of_scope` 点名 `outside/rogue.py` (声明范围 out/) |
| N | R516 新 AOT | plan-overlap.txt + `--scope scope-overlap.txt` | **2** | 未起臂 | 报告未生成 · adapter 调用 **24→24** (零 LLM) · stderr 点名 `tasksvc/ ∩ tasksvc/model.py` |
前态锚 (冻结归档, 机器读):`n4`/`n3` Completed ∧ `files=[]` ⇒ 本轮闭合的假绿现场。
**VERDICT: PASS (6/6 判据, `eval/rover/r516/evidence/verdict.json`)**。
## 4 本轮产出与读数
| 项 | 命令 | 读数 |
|---|---|---|
| 范围机检解析 | (单测) | 22/22 通过 · 全量 **1706/1706** rc=0 (`evidence/unit-scope-tests.txt`, `evidence/full-tests.txt`) |
| AOT 重发布 | `dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_r516` | rc=0 · **IL 警告 0** · 15,592,688 B · sha12 `b31af1d94da1` (R515: 15,555,120 B ⇒ +0.24%) |
| 真机 5 臂 | `bash eval/rover/r516/run_scope_e2e.sh` | **VERDICT PASS 6/6** · 负控臂零 LLM (`evidence/verdict.json`) |
| 形式门禁 | `bash eval/rover/r516/gates_r516.sh` | bind `R2E_R2F_EXIT=0` · decl_sweep `drifted=0` · registry `ROWS=232 bad=[]` |
| 登记 | `register_r516.py` + `bind_evidence --only agent.node-artifact-scope-contract --round R516 --apply` | `TOUCHED=1` · `SER_ASSERT=OK` · `WRITE_READBACK=OK` · `UNCHANGED=0` |
| 铁律 11 前置闸 | `python3 eval/rover/r507pre/exec_precondition.py --round R516` | **rc=3 DISCOVER_FAIL** (taskset/codex/agent 三空) ⇒ 本轮**不宣称** token 降幅 |

**远端调用/token 同窗读数 (按 adapter side-*.json 落盘时刻归因到臂, 标「参考 (未可验收)」)**
| 臂 | 调用数 | prompt_tok | completion_tok |
|---|---|---|---|
| RED (旧 AOT, 1 步) | 5 | 12,348 | 264 |
| G1 (新 AOT, 1 步) | 4 | 7,346 | 127 |
| G2 (新 AOT, 3 步, 真干活) | 8 | 20,122 | 530 |
| G3 (新 AOT, 3 步, 越界) | 7 | 14,768 | 423 |
| N (负控, 未起臂) | **0** | 0 | 0 |
| 合计 | 24 | 54,584 | 1,344 |
注:各臂步数/模型输出非定长 ⇒ 与 R515 归档跑次**不可相减** (不同夹具); 本轮读数的用途是「机制是否真落地」, 不是用量降幅判据。

## 5 诚实边界
- **未测到**:token ↓≥30% 判据本轮**无读数** (前置闸 rc=3, 无对照题集);「编排 vs 单轮」规模臂 (R515 双包 24 用例) 仍未跑 (内存闸 2650 MB 是硬约束, 本轮实测 MemAvailable≈2.55–2.71 GB 摆动)。
- **未测到**:节点写范围契约在**多层并发** (同层多写者之外) 场景下没有被真机跑过; 快照差的归属唯一性在并发窗内不作宣称 (E2)。
- **未复核**:R515 未在 `iteration-master-plan.md` / `improvements.md` 落轮节 (兄弟会话只落了 `docs/reports/r515-*.md` + registry + eval) ⇒ 本侧不代写对侧轮节, 缺口记在 §3 计划 §6-E5。
- **已知抖动 (前置缺口, 不计入本轮)**: `instruments_check.py` 面本轮「可判据 27/29 通过」, 2 红为 `external.contrast-exec-precondition` / `external.contrast-interaction-kpi` —— 二者的 `cmd` 实测 rc=0、`negative_controls.pass=true`, 判红只因**自身登记行的 L2 字段声明缺口** (`input_surface_source=BAD/MISSING`、`input_fingerprint=EMPTY_FP_FOR_EXTERNAL`, `owner_round=R507`); R516 的 `bind_evidence --apply` 作用域含且仅含 R516 行 ⇒ 与本轮改动无交集。**未做** HEAD 独立树复跑 (归档树非 git 仓 ⇒ `git show HEAD:` 依赖的检查全败, 该路径已废弃并如实记为未复核)。

## 6 下轮候选 (R517)
① 规模臂 (R515 双包 24 用例 + `--scope`) 争主线判据; ② 对 R515 `plan-p4-v2.txt` 声明范围后重跑, 机检 n3/n4 是否被新机制判 Failed (本轮只做了前态锚); ③ 写范围运行时互斥 (目录级独占锁, 超出「起臂前拒收」); ④ `improvements.md` R404–R407 回填 (结转); ⑤ D4 判据在 HTTP 题族可达面扩展 (结转)。

## 7 事故与修复 (R516 自抓, 记为诚实边界而非静默)
**现象**: 提交前钩子 BLOCKED (R2e) —— `r444.separability-precheck` 自证器具路径与声明不符, `r444.instrument-acceptance` 语义投影 pin 与现盘不符。
**根因 (机检定位)**: ① 我在 `/tmp/r516/head_tree` 建了一份**归档影子副本**去跑器具面 (想取 HEAD 基线, 该路后废弃); ② `eval/rover/r444/precheck_prefilter.py:22` **硬编码** `ROOT = pathlib.Path("/home/agentuser/AgentFramework")`, 于是**影子副本进程写回了真实仓**的产物, 且 `INSTRUMENT.relative_to(ROOT)` 失配 ⇒ 产物与登记行被写入**绝对 /tmp 路径** (`provenance.instrument` / `evidence_generated_with.instrument`); ③ 器具面每次执行都会**重跑**自身 evidence_cmd ⇒ 产物 (及其 pin) 必然随树态漂移 (自指成员)。
**修复 (逐条可复跑)**: `python3 eval/rover/r444/precheck_prefilter.py --out eval/rover/r444/precheck-prefilter.json` (rc=0) → `--neg-control` (rc=2 设计值, 负控「检出 ≥1 反例」OK) → 登记行 instrument 复原为仓内相对路径 → `bind_evidence --only r444.separability-precheck --round R516 --apply` 与 `--only r444.instrument-acceptance` (各 `R2E_R2F_EXIT=0`) → 提交态核验 `COMMITTED_STATE_CHECK=OK (rows=232 claims=296 blobs=252)`。
**残留**: 两条 r444 行的 `audited_by_round` 因本轮定向重审由 EXP1-Q34/EXP1-Q39 前进为 R516 (pin 确由 R516 写入, 属事实记录)。
**教训 (下轮候选 ⑥)**: 器具面复跑前必须先确认**无影子副本**; 硬编码 ROOT 的器具在副本内执行会污染真实仓 ⇒ 需给器具面加「根路径自证」负控 (副本内跑必须判红)。
