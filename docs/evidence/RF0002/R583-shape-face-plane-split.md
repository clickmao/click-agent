# R583 · RF0002 §3 验收面 P2/P3 判据收窄与重注册（调用面分层 + 形状面真机臂）

- **轮次**: R583 · 日期 2026-09-19 · 承 R581（首验：P2/P3_eviction FAIL）/ R582（轮检器具）
- **预注册**: `eval/rover/r583/prereg-r583.json`（先于任何真机跑次落盘；P6 于起臂前追加）· **DAG**: `eval/rover/r583/dag-r583.json`
- **产品面**: **零源码改动**（只跑既有二进制 + 读归档数据 + 落盘器具）
- **真机二进制**: `src/agent.host/bin/Release/net10.0/agenthost` sha256 `fe1fb720…`（HEAD `8c14da6`，未重建）
- **命令面**: `agenthost --role ./skeptic.rbin --session-id <id>` 经 stdin REPL 逐轮投递 · 四臂串行（S0 44s / S1 12s / D 24s / N 10s）
- **前置闸**: 远端预检 http=200；MemAvailable 2738MB；磁盘 15GB（起手回收 /tmp 陈旧产物 8.05GB，2.3 万→3 千目录）；对侧 0 在飞

## 1 · 量：命中轮「调用」是哪个面（归档数据分层，未重跑）

| 臂 | 轮 | route | agent 面调用 | 宿主面调用 | 窗口内合计（R581 原口径） |
|---|---|---|---|---|---|
| R581 臂A | 1 | remote | 1（prompt 4362 / completion 599） | 0 | 1 |
| R581 臂A | 2 | local_skip | **0** | 4 | 4 |
| R581 臂A | 3 | local_skip | **0** | 7 | 7 |

- agent 面 = `llm_call.agent_session` 非空 ∧ `turn>=1`；宿主面 = session 空 ∧ `turn=0`。
- 交叉校验：两条独立路径（session / turn）逐调用一致 ⇒ `cross_check_fail=0`（不符即 rc=2 fail-closed）。
- 臂 A 宿主面占比 **11/12 = 91.67%** ⇒ 命中轮「零远端调用」在**窗口口径**下结构性不可达（可省面只有 agent 面）。
- 命中轮 `completion` 上升（616 / 1408）**100% 来自宿主面**，agent 面 completion = 0 ⇒ 非本地消化的副作用。
- **R581 的 P2 FAIL 保留不改**；本轮 agent 面口径为**新注册**（与 R432「先分通道再汇总」同族）。

## 2 · 计数器的生产面：`hits` 结构性恒 0

- `_shapeHits++` 唯一写点 = `src/agent.nlp/NlpGate.cs:129`（`Decide` 内 learned-shape 分支）；`NlpGate.Decide` 的**生产调用点 = 0**（调用方只调 `IsPatched` / `IsLearned` / `ReportOutcome` / `ShapeCounters` / `LearnFromRemote`）。
- 真机配对：R581 臂A 轮2/轮3 与 R583 臂 S1 轮2 均为 `shape=1 ∧ hits=0` ⇒ 「形状命中」与 `hits` 在生产面解耦。
- 处置：**P3b 判据面由 `hits>=1` 改为 `shape=1`（IsLearned 呈报）**；R581 的 P3_eviction FAIL 不翻案。

## 3 · 真机臂（单变量：形状库有无）

| 臂 | 库 | 轮 | 结果 |
|---|---|---|---|
| S0 负控 | absent | 2 | `route=remote / shape=0`（`mechanical:nonack→remote`）⇒ 结构面单独不命中 |
| S1 治疗 | fixture 1 行 | 2 | `route=local_skip / shape=1 / face=repeat / basis=mechanical:repeat→local`；**agent+宿主面调用均 0**；`local_gate_skip_reply=repeat_verbatim` |
| D 降级 | fixture 1 行 | 1 | `repeat_degrade_remote{reason=no_replayable_prev}` ∧ 同轮 `shape=1 / route=remote` |
| N 族外 | fixture 1 行 | 1 | `shape=0 / learned=0` |

fixture = R581 真机学到的形状行（`repeat\tzh\t1\t一|再|来|遍`，sha256 `c98f8ab3e8a49acb…`），逐字复用、不重造；库起手不存在（`data/nlp` absent）。

## 4 · 判据裁定（rc=0，6/6 PASS，负控 3/3 有牙）

| 判据 | 期望 | 实测 | 裁定 |
|---|---|---|---|
| P1 形状面行使（分层） | S1 轮2 `shape=1 ∧ route=local_skip ∧ face=repeat` ∧ agent 面调用 0 | 全中（agent 0 / 宿主 0） | **PASS** |
| P2 分层不增远端 | 命中轮 agent 面调用 < 学习轮 agent 面调用 | 1 → 0 | **PASS** |
| P3a 降级路径可达 | 臂 D 落 `repeat_degrade_remote` | 逐字落盘 | **PASS** |
| P3b 形状命中呈报 | 臂 D 该轮 `shape=1`（`hits` 结构性 0） | `shape=1 / route=remote` | **PASS** |
| P4 负控有牙 | S0 同输入无库 ⇒ remote ∧ `shape=0`；N ⇒ `shape=0 ∧ learned=0` | 全中 | **PASS** |
| P5 库落盘守恒 | 预置后 S1/N 保持 1 行 | S1 = fixture sha 逐位不变；N 同 | **PASS** |
| P6 库去重/装载面 | 行数 1→2（分支 B） | D 跑后 2 行（sha `04ad26a8…`） | 分支 B 成立；「两行逐字相同」子项**不成立**（见 §5） |

## 5 · 自捕：形状库内存剔除不落盘（真缺陷形态，登记不定因修复）

- 臂 D 后库文件 1 → **2 行**：第1行 = fixture，第2行 = `repeat\tzh\t1\t一|新|来|遍|重`（**face/lang/band 三元组与第1行相同**，`Same()` 本应拦住）。
- 机理：degrade 点调 `ReportOutcome(useful:false)` **只从内存 `Shapes` 移除**，不重写文件；同轮远端成功后 `LearnFromRemote` 的 `Same()` 因内存已空而未拦住 ⇒ 追加行。
- 同源：R581 `shapes-r581.txt` 的两行逐字相同 = 同机理（臂A/臂B 输入同文）⇒ R581 登记为「机理未定因」的重复行异常在本轮**定因**。
- 口径诚实：P6 的候选机理（「`Same` 未拦住」）与真机理不符（真机理 = 内存剔除后重新学习）；判据按预注册照原样判，机理在 `posthoc-r583.json` 修正。
- 影响：库行数不能当形状数；内存剔除的形状跨进程「复活」；`MaxPatches` 只封顶内存。
- 处置：本轮零产品改动 ⇒ 只登记；修复需产品改动放行（R584 候选①）。

## 6 · 候选⑤ 落地（作业环境自备 key 面）

- 常驻作业 `b15eb2f40a69` 的 prompt 原缺 key 自备步骤（R581 v1 全臂 VOID 的直接原因）。
- 动作：store 备份（`~/.agentframework/backups/cron-jobs-r583-20260919T211153.json`，size 9771 / sha256 `50d86771…`）→ 外科式替换「环境前置」行 → 回读断言（新串计数 1 / `keys.env` 引用 1 / 其余字段与 job id 逐字段不变）。prompt 4195 → 4347 字符。
- 证据：`eval/rover/r583/cron-prompt-keyface-r583.json`。key 值不入仓库、不入 prompt（推送暂停令在效）。

## 7 · 诚实边界

- 零产品源码改动 ⇒ **不宣称任何质量/成本降幅**（无可比窗口）。
- 单轮 n=1 每臂 ⇒ 只作机制存在性证据，不作分布结论。
- codex 外部真值同题对照 / 回复质量 / 轮数 / 问答计数：**本轮未测**（非质量对照窗）。
- R581 判决（P2 FAIL / P3_eviction FAIL）保留，不翻案；本轮的判据分层是**新注册**。

## 8 · 器具与产物

- 器具：`extract_r583.py`（分层判据 + 3 负控自检）、`plane_split_r583.py`（归档分层 + 天花板算式）、`run_arms_r583.sh`
- 读数：`readings-r583.json` / `verdict-r583.json` / `plane-split-r583.json` / `posthoc-r583.json` / `arm-meta.txt` / `pre-arm-state.txt` / `gate-pre-r583.txt` / `arm-{S0,S1,D,N}.out.txt` / `telemetry-offset-*.txt`
- 台账：`eval/capability/kpi.jsonl`（R583 行）· 登记：`docs/verification-registry.json`（`r583.shape-face-plane-split`, L3）

## 9 · 门禁与构建读数（收口）

| 项 | 读数 |
|---|---|
| build | `dotnet build src/agent.host/agent.host.csproj -c Release` ⇒ 10 Warning(s) / **0 Error(s)**；重建二进制 sha256 逐位不变（`fe1fb720…`，与跑臂期同一件） |
| 形式门禁 | `dotnet test --filter "VerificationForm|SkillGeneralization|DevPlanDocRef"` ⇒ Failed 0 / Passed **14/14** |
| 真机臂 | 4 臂 rc=0（S0 44s / S1 12s / D 24s / N 10s）；远端预检 http=200；收尾残留 0 进程、库已复原 absent |
| 轮检 | `tools/roundcheck/roundcheck.py audit --round R583` ⇒ **FAIL=0 / WARN=1（R9 暂存面为空=提交后常态）/ rc=0**（R1–R8+W1 PASS） |
| 缓存命中率（agent 面, 口径 = `cache_hit_tokens / prompt_tokens` 逐调用中继 usage） | S0 90.0% / S1 91.9% / D 88.1% / N 92.4%（命中轮 S1 零调用 ⇒ 该轮不产生命中面读数） |

