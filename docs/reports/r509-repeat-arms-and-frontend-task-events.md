# R509 — 同题重复臂（会话隔离）× 前端任务事件域（路线 A 实施）

日期: 2026-09-17 · 轮次: R509 · 前置: R508 收口 `6bec98f`
题面: p3 线程安全 KV 服务包 `kvsvc`（TTL + WAL + 并发 incr，12 条隐藏用例，铁律 11 可执行前置）
外部真值: codex-cli（@openai/codex 0.154.0），同环境同输入同模型 `deepseek-chat`

---

## 1 对照读数（保真，n=3/臂；codex n=2）

| 臂 | 跑次 | 整题全对 | 用例 | tokens min/mean/max | 调用 | 墙钟s | steps |
|---|---|---|---|---|---|---|---|
| 本侧 默认预算 | 3 | **2/3** | **35/36** | 72,831 / **80,995** / 90,167 | 7 | 25.9 | 6 |
| 本侧 显式 3 步 | 3 | **0/3** | 22/36 | 36,207 / **39,918** / 41,941 | 4 | 20.7 | 3 |
| codex（窗口 b） | 2 | **2/2** | **24/24** | 104,920 / **445,211** / 785,501 | 24 | 69.3 | — |

逐跑次：agentA = 12/12 · 11/12(`restart_drops_expired`) · 12/12；agentD = 0/12(全部) · 11/12(`restart_drops_expired`) · 11/12(`restart_recovery`)；codex = 12/12 · 12/12。

均值比（本侧默认 vs codex）：**tokens −81.8%**（81.0k vs 445.2k）· **调用 −70.8%**（7 vs 24）· **墙钟 −62.6%**（25.9s vs 69.3s）。
codex 侧单题方差 **7.5×**（104.9k ↔ 785.5k）⇒ R508 的「p3 −90.4%」是取到高位方的单点读数，本轮给出区间后收窄为 −81.8%（仍是量级差）。

## 2 本轮真产出：两处「仪器假红/假绿」

| # | 缺陷 | 症状 | 修 |
|---|---|---|---|
| D1 | **cfg 嵌套** | 首版跑器 `mkdir -p "$D/agent/cfg"` 后再 `cp -r <种子> "$D/agent/cfg"` ⇒ 落成 `cfg/cfg/base/...` ⇒ `模型目录为空` ⇒ **全臂 0 调用**（6 跑次全 12 用例失败，且 rc=0） | 只建父目录 + 落盘后**形态守卫**（`base/models.yaml` 必须存在，缺即 rc=3） |
| D2 | **会话态污染** | 重复臂共用 `session-id=r508-<arm>-<tid>`（`proj_run_side.py:78`）⇒ 首个调用继承上一窗口的失败/待答复态 ⇒ **0/12 假失败**（在 D1 存活窗口里同源） | 每跑次独立会话：`--arm <arm>-r<N>` ⇒ session 唯一（跑次间统计独立，替代「共享会话」） |

修 D2 后同臂重跑：默认臂 12/12、11/12、12/12（前值 0/12 消失）⇒ **D2 是 R508「3 步臂 2/2 通过」读数的真因，该读数作废**。

## 3 结论（对比数据）

1. **默认预算 > 显式 3 步**：整题全对 2/3 vs 0/3；用例 35/36 vs 22/36；tokens 均值 81.0k vs 39.9k（省 51%），但省下的 token 换不来通过率 ⇒ 收紧预算**被证伪**（与 R508「加长预算被证伪」同向：默认值即当前最优点；`AGENTFRAMEWORK_ACTION_ADAPTIVE_BUDGET` 维持默认关）。
2. **唯一跨轮不稳用例 = `restart_drops_expired`**（重启后 TTL 不应复活）：本侧 6 跑次中 3 败（默认臂 1/3、3 步臂 2/3，另单发探针 1/1 败），codex 2 跑次 0 败。该要求已写入 prompt 契约并以隐藏用例机械判对 ⇒ 是**真实质量缺口**（重启路径未自测），非仪器噪声。
3. token/调用/墙钟三项本侧均显著低于 codex（−81.8% / −70.8% / −62.6%），且本轮为区间对区间，不再是单点。

## 4 前端任务事件域（路线 A，已实施并真机验证）

新增（增量、老前端不破）：

| 面 | 内容 |
|---|---|
| 事件 | `task.started{task_id,session_id,api,started_at_ms}` · `task.completed{task_id,success,elapsed_ms,reply_chars,steps}` · `task.failed{同形,success:false}` |
| 快照 | `state.snapshot.tasks[]`（`state` ∈ running/done/failed；断线重连可读在飞/最近任务） |
| 响应 | `chat.send` 响应增 `task_id` |
| 会话 | `AGENTFRAMEWORK_FRONTEND_SESSION` 可注入（默认 `frontend-main` 逐位不变） |

证据：单测 **7/7**（含未知 task_id 拒绝、终态幂等不覆盖、异常路径 `task.failed`+快照 `state=failed`）；全量套件 **1643/1643**；AOT `IL_warnings=0` · 15,425,840 B · `sha256 4087c90c…` · `env -i --version` rc=0；真机 E2E（AOT + frontend-api + 真模型）断言 **A1–A8 全绿**，回复 = `2`（真答，1.22s）。

**假绿负控实测命中（本轮）**：首版 E2E 事件面全绿，但回复是上一轮续跑追问（0.01s、0 模型调用，共享 `frontend-main` 会话）⇒ 新增 A7（回复必须是真答）/A8（响应 ok=true）后判红，会话隔离后转绿。

## 5 诚实边界

1. 两侧**非同一次连续窗口**：codex 读数为窗口 b（adapter :48671），本侧为窗口 c（:48674）；同夹具、同 taskset、同题、同模型，端口差异不影响 token 语义，但非同窗连续跑。
2. n = 3（本侧）/ 2（codex）⇒ 只出区间与并列，**不出统计显著性断言**；不据总量断言优劣（H5）。
3. `restart_drops_expired` 的「摆动 vs 预算」未完全分离（两臂都失败过；3 步臂 2/3 > 默认臂 1/3 但 n 太小）。
4. 只覆盖程序题（p3）；见证型数学题无执行面。
5. 本仓库 30 分钟 cron 作业在 07:38–07:46 独立起了同名轮次的另一套器具（`eval/rover/r509/{aggregate_r509.py,proj_rep_run_side.py,make_prereg_r509.py,cases/,nc/,prereg-r509.json,evidence/snapshot-manifest-r509.json,evidence/nc-precond-*.json,evidence/prereg-oracle-p3.json}`）；**本报告与登记行不引用、不提交对侧文件**，对侧读数未在本轮核对。
6. R508 的「3 步臂更优」读数按 §2 作废；R508 其余读数与结论不变。

## 6 下轮候选（全部并入一轮）

1. `restart_drops_expired` 单点攻坚：把「重启后过期键不得复活」做成自测清单项（若为 prompt 契约覆盖不足则补契约；若为模型能力则记窄化宣称）。
2. 前端事件域第二段：`task.progress{phase,step_index,current_action,elapsed_ms}` + `approval.requested/responded`（现 `FrontendPromptService.RequestOperationApprovalAsync` 为静默保守拒绝）。
3. 与 cron 侧 R509 器具对齐：交换读数前先核 host/夹具同源，禁止跨器具相减。
