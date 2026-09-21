# R618 DAG · RF0004.2 · M3 **第二刀 = 执行面接线**

轮次：R618 ｜ 协议：`docs/plans/RF0005-completion-protocol.md` §2 固定环 0–9
意图：把 R610 第一刀产出的 **`accepted` 采纳集接到执行面**（R617 实测声明到岸 9/9 而 `accepted` 消费者数 **0**），
使 `docs/plans/RF0004-three-capability-development-plan.md` §0.1「多轮工具编排」的「**编排决策来自结构化字段（非自由文本动作环）**」
从「声明面成立」升到「执行面成立」，M3 出口闸「调用数按 request_id 去重 ≤ 旧臂 50%」才具备可判前置。

## 节点 / 依赖边 / 并行面

| # | 节点 | 依赖 | 出口证据 | 状态 |
|---|---|---|---|---|
| N1 | 起手闸（环境）| — | `roundcheck preflight --round R618` **rc=0**（P1 key / P3 mem 2871MB ≥ 2775 / P4 disk 4GB / P7 R618 空闲 / P8 PUSH_PAUSED） | ✅ |
| N2 | **可行性前置（只读）**：R617 的 33 条远端回复里「候选 → 执行面」的可映射率 | — | 201/201 可映射（118 `write_file` + 83 `run_command`，0 无执行面）；(工具,参数) 与 `plan` 逐字匹配 196/201（97.5%）⇒ 载体可行、自述期望可继承 | ✅ |
| N3 | 产品侧**最小**改动：`AcceptedAction` / `ActionExecPlan`（映射器）/ `Selection.AcceptedActions` / 管道载体 / 台账四字段 / 单测 9 条 | N2 | 定向测试 **41/41**；AOT 0 IL；API 基线重钉 **20 行**（全属本轮） | ✅ |
| N4 | 构建 + AOT 重发布 + 装载冒烟 | N3 | `artifacts/pub_r618/agenthost`；`PUBLISH_RC=0 ∧ IL=0 ∧ ERR=0` + 冒烟非空 | ✅ |
| N5 | 预注册（**先写后跑**）| N1 | `prereg-r618.json`（`written_before_run=true`，驱动器 fail-closed 机检） | ✅ |
| N6 | 真机臂轮：w208..w210 ×（C1 codex ×1 + T ×3 + C ×3）= 21 跑次 | N4,N5 | `runs.jsonl` + 逐窗判决 | 待 |
| N7 | 判决 `judge_r618.py`：J0 轴生效 / J1 机制面（**执行面消费**）/ J2 零回归 / J3 成本三列 / J4 能力面并列 / J5 M3 出口闸读数 + 铁律 11 | N6 | `verdict-r618.json` | 待 |
| N8 | 收口：report + registry + `kpi.jsonl` + §7 块 + 文献台账 + `status_gen --check` + 形式门禁 + 逐名列名提交 | N7 | 提交号 + 五闸读数 | 待 |

**并行面**：N2 与 N3 互不依赖，但**同仓只有一个写者**（本会话）⇒ 按 DAG 令不开子 agent 写仓；
N2 已以只读探针完成（零产品改动、零子进程、零远端）。

## 收尾重启判据（不重跑全轮）

| 触发 | 重启哪条边 |
|---|---|
| J0 FAIL（两臂 `exec_source` 不可区分 / 与预注册不符）| 重启 **N3 边**（器具/载体检修，**不重测**：同一批 transcript 可只重跑后处理）|
| J1 守恒违例 > 0（`executed + unmapped != accepted`）| 重启 **N3 边**（映射器丢条目 = 器具缺陷，rc=2），禁改判据凑绿 |
| 单跑次 `rc=124` 超时（R615/R617 各复现 1 例）| **不重启**：按既有纪律单列 `invalid`，禁计入质量分母、禁调阈值 |
| 有效窗 < 2（真值自败窗剔除后）| rc=3 停链、先造窗集（R3），**禁下调阈值** |
| 铁律 11 `rc≠0` | 不重启：全部成本/质量读数标「参考（未可验收）」 |

## 诚实边界（写进预注册，不做事后补记）

1. 第二刀只接**动作面**（`write_file` / `run_command`）；`read_file` / `list_dir` / `delete_file`
   在 R1 窄腰**无对应节点** ⇒ 计 `action_candidates_unmapped` 单列（**第三刀** = 信息类工具的「回执走尾部载体」）。
2. 候选 schema **不含** `expect_stdout` ⇒ 自述期望由 `plan` 里 (工具, 参数) 逐字相等的节点**继承**
   （实测继承率 97.5%）；继承数落台账 ⇒ 「换载体是否丢自检」可机检。
3. 轴**默认 off**（未放行的产品分支不动）⇒ C 档 = 旧行为，且台账不出现新字段（逐字节同）。
4. 本轮**不改前缀**（`tools/r1gen` 零改动）⇒ 恒前缀 chars/sha 与 R617 同值，缓存硬门 ≥97% 照旧适用。
