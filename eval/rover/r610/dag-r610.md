# R610 DAG（RF0004.2 首轮 = M3 第一刀：动作候选进 R1 契约 + 本地机械裁选）

意图：把「编排决策由**闸族系**给出、**远端只做候选声明**」这条 M3 设计动因落成**可机检的最小一片**：
契约面部新增可选字段 `action_candidates`（前缀**只加厚**）＋ 本地机械裁选器（逐条裁定、可机检原因码）＋
三计数落台账（声明数 0 ⇒ 字段缺席 = 旧行为逐字节）。

## 节点 / 依赖边

| # | 节点 | 依赖 | 可并行 | 产物 |
|---|------|------|--------|------|
| N1 | 契约面加厚（单一源 `tools/r1gen/contract.py` → 生成 `StructuredContract.cs` / `StructuredPrompt.cs`） | — | ✗（同文件串行） | 前缀 15291→15697 字符，sha `f1280f71…`→`127fb301…` |
| N2 | 本地裁选器 `src/agent/r1/ActionCandidates.cs`（白名单/必填参数**取执行面与声明面**，禁另立表） | N1（工具枚举同源） | ✓（新文件，与 N1 不同文件） | `Select(...)` 纯函数 + `Selection{Declared,Accepted,Rejected,RejectReasons,AcceptedIds}` |
| N3 | 台账三字段（`R1RunResult` / `R1Transcript` 渲染 + `R1_STATS` 标记，声明数 0 ⇒ 缺席） | N2 | ✗ | 字段缺席可控 |
| N4 | 单测 6 条（正控 / 判别性负控 / 同源闸 / 零回归 / 边界 / 轴解析） | N3 | ✗ | `ActionCandidatesTests` 6/6 |
| N5 | 同源闸 `gen_csharp.py --check`（生成物 == 原型，drift 0） | N1 | ✓ | `R1GEN_EXIT=0 / R1GEN_DRIFT_FILES=0` |
| N6 | 形式门禁 14/14 + API 基线重生（增 16 / 删 0） | N4 | ✗ | Failed 0 / Passed 14 |
| N7 | 预注册 `prereg-r610.json` + 本 DAG（**先写后跑闸**） | N1–N6 | ✓ | 先于任何臂落盘 |
| N8 | AOT 重发布 `artifacts/pub_r610/agenthost` + 起手闸（REQ=2650+clamp(170,60,cap)） | N1–N6 | ✗ | bins-r610.json 钉 sha |
| N9 | 真机臂（第十三窗集 w199..w201：T×3 / C×3 / codex 真值×1）+ 判据器 → 判决 | N7,N8 | ✗（严格串行） | `verdict-r610.json` / `kpi-table-r610.json` |
| N10 | 收口五件（轮工件 / 证据文档 / registry / kpi 行带 `baselines` / 逐名列名提交） + `status_gen.py --check` PASS | N9 | ✗ | 提交 |

## 可并行面

- 无依赖边且不写同仓的节点：N5（`--check` 只读比对）与 N4 可并行；文献小步（网络面）与 N1–N6 可并行。
- **同仓有在飞写者（RF0006 兄弟会话）时：并行节点限只读，禁任何重算**（本轮实测该条件成立 ⇒ N8/N9 顺延，见下）。

## 收尾重启判据

- N9 失败/未起：**只重启 N8→N9 这条边**（N1–N7 产物在盘、prereg 已「先写」）⇒ 不重跑全轮。
- N8 因窗口不可开（内存闸 fail-closed）失败：**只重启 N8**，不许下调闸值（§3：「有效窗<2 ⇒ 造窗，禁下调阈值」同family）。
- N6 红：只重启 N6（补测/重钉），不动 N1–N5。
- 判决后若 J1 未达（声明不到岸）：按预注册②**撤回本轴**（净产品改动退回声明面单列），只重启 N2/N3 的收窄分支。

## 本轮实况（2026-09-21 09:44–10:0x tick）

- N1–N7 全部落地（N5 drift 0 / N6 14/14 + API 增 16 删 0 / N4 6/6）。
- **N8/N9 顺延**：起手闸三条件同时红 —— ① 同仓兄弟写者**在飞改 `src/`**（`src/agent.llamacpp/LlamaCppGeneratorOptions.cs` mtime 09:59:03，AOT 发布件无法代表「本轮 src 改动的发布件」⇒ 被测件身份不成立）；② 兄弟 `dotnet run`/MSBuild/VCSCompiler 在飞（不得拆共享编译节点）；③ `MemAvailable` 2019MB < REQ（2650+170=2820MB）⇒ 窗口 fail-closed。
- 收尾重启边 = **N8→N9**（下 tick 同 prereg 起臂；prereg 已在臂前落盘，不构成事后补写）。
