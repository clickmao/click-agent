# R511 · 规模探界 (E1) + delete_file 人工审批真机闭环 (E2)

**日期**: 2026-09-17 · **轮号**: R511 · **AOT**: `/tmp/pub_r511/agenthost` (sha12 `139ac3bc986b1b03`, 15,467,520 B, `IL_warnings=0`)
**窗口**: `/tmp/r511/run-w2` (E1) · `/tmp/r511/e2e` (E2) · **夹具**: `eval/rover/r511/taskset-r511.json` (taskset_sha12 `822e1c2bb4e7`)

## 1 目的

回答「本 agent 自动能处理多大规模的任务」，并把「审批通道真机不可达」这一历史缺口闭合。E1 = **规模探界**（同环境·同输入·同模型，单变量 = 步数预算）；E2 = **第 5 个工具 `delete_file` + 人工审批 fail-closed 真机闭环**。

## 2 E1 夹具与窗口体检

| 项 | 值 |
|---|---|
| 题面 | **p3**（逐字节复用 R508 taskset 的 p3，sha `efa48cb2ccef`；3 文件/218 行目标，12 隐藏用例）· **p4**（新题 `tasksvc`：3 文件/636 行目标，12 隐藏用例） |
| 臂 | `dflt` = 默认预算 6 步 · `s12` = `AGENTFRAMEWORK_ACTION_MAX_STEPS=12`（其余全同） |
| 跑次 | 每臂 n=2，**每跑次独立 session**（R509 铁律：`--arm <臂>-r<N>`） |
| 起手闸 | 连续 2 次 PASS |
| 模型 | `request.upstream_request.model = deepseek-chat`（H4） |
| 窗口体检 | 56 次调用 · `unreported_usage=0` · **无「空正文且无 tool_calls」异常调用**（`empty_text` 均为正常 tool_calls 轮） |

读数（`evidence/report.json`、`evidence/window.json`）：

| 臂 | 题 | 整题全对 | 用例 | 步数/预算 | 调用 | 落盘 | 墙钟 | 臂 tokens |
|---|---|---|---|---|---|---|---|---|
| dflt-r1 | p3 | ✗ | 0/12 | **6/6 (用尽)** | 7 | 2 文件/259 行 | 30.8 s | 137,004 |
| dflt-r1 | p4 | ✗ | 4/12 | **6/6 (用尽)** | 7 | 3 文件/562 行 | 41.2 s | |
| dflt-r2 | p3 | ✗ | 0/12 | **6/6 (用尽)** | 6 | 2 文件/249 行 | 32.0 s | 133,747 |
| dflt-r2 | p4 | ✗ | 4/12 | **6/6 (用尽)** | 8 | 2 文件/541 行 | 21.3 s | |
| s12-r1 | p3 | ✗ | 0/12 | 0/12 | 0 | **0 文件（模型口述不落盘）** | 23.4 s | 168,237 |
| s12-r1 | p4 | **✓** | **12/12** | 11/12 | 12 | 3 文件/**636 行** | 37.8 s | |
| s12-r2 | p3 | **✓** | **12/12** | 7/12 | 8 | 4 文件/738 行 | 45.0 s | 169,539 |
| s12-r2 | p4 | ✗ | 4/12 | 4/12 | 5 | 3 文件/509 行 | 22.8 s | |

## 3 结论（规模上限）

1. **默认 6 步预算：本窗 4/4 跑次整题全对 = 0**。全部 4 个臂在 p3/p4 上都把 6 步用尽（`e=True`），落盘 2–3 文件后停止 ⇒ 失败模式 = **预算耗尽**，不是模型看不懂题。
2. **提到 12 步后本窗出现 2/4 整题全对**，其中一次完成 **636 行 / 3 文件**（p4 12/12，步 11/12），另一次完成 738 行（p3 12/12）⇒ 抬高预算确实抬高上限。
3. **上限由步数预算决定，而非模型能力**：同一模型在 12 步下能一次写对 636 行三文件包；在 6 步下连 218 行档都做不完。
4. **失败模式两类**：(a) 预算用尽（本窗 4/4 dflt）；(b) **模型「口述不落盘」**（1/4 s12 跑次：两次终答输出 9.4 KB / 12.2 KB 代码文本、0 次工具调用、工作区 0 文件）—— 与预算无关，属行为型失败。
5. **跨窗对照（同题 p3）**：R509 默认臂 **2/3 全对（35/36 用例）**、R510 after 臂 **3/3（36/36）**、本窗默认臂 **0/2（0/24 用例）** ⇒ **窗口间摆动大于臂间差异**。218 行档在默认预算下已处临界态，任何单窗读数都不足以作承诺；引用必须带区间与 n。

## 4 判据器判别力（防假绿）

- 正控：参考解 12/12 PASS。
- 缺陷注入负控（3 臂，均判红且按预期点名，`evidence/nc-cases.txt`）：`--now` 被忽略 ⇒ 11/12 判红；**非原子写（原地重写）** ⇒ **精确点名 `no_temp_residue`**（inode 未变）；**id 复用** ⇒ 点名 `expire_removes_expired_tasks` + `list_filter_and_order`（nc3 与 nc2 点名集不相交 ⇒ 判据非同一把锤子）。
- 用例结构判据（非读源码）：临时文件零残留 + **每次更新换 inode**（temp+rename 的可观测后果）+ 跨进程持久（每条命令独立进程）。

## 5 E2 审批真机闭环（第 5 个工具）

| 项 | 值 |
|---|---|
| 变更 | `ActionToolDecl.DeleteFile="delete_file"`（声明面与 Names 同源，`ToolsJson`/`ActionToolSpec` 双侧同步）· `WorkspaceActionPort.DeleteFileAsync`（边界解析 → 审批门 → 真删）· `ApprovalUnavailableExitCode=125` / `ApprovalDeniedExitCode=124` fail-closed · 宿主 DI 把 `IUserPromptService` 接到审批门（未注册 ⇒ 一律拒绝） |
| 单测 | R511 新测试 **10/10**；全量 **1663/1663**（R510 1653 → +10） |
| AOT | `PUB_RC=0` · `IL_warnings=0` · 15,467,520 B（+0.19%）· `VERSION_RC=0` |
| 真机 E2E | `eval/rover/r511/run_e2e_approval.sh`（AOT + frontend-api + 真链真模型）⇒ **`E2E_APPROVAL_VERDICT=PASS` 10/10** |

真机事件链（approve 臂）：`task.started → plan.created → task.progress → approval.requested{kind=DeleteFile,summary=删除文件: victim.txt} → approval.responded{approved=true,answered_by=RealUser} → task.progress → …`，**磁盘证据：victim 文件已被真删（exists=False）**；deny 臂：`approved=false,answered_by=Denied` ⇒ **文件原封不动（exists=True）**。真答 5.62 s / 2.78 s（排除 0.01 s 陈旧续跑假绿）。

## 6 器具缺陷与诚实边界

1. **未落盘预注册**：本轮为探索性测量，判据 = 机检 + 负控，**未在起臂前落盘预注册文件**（与 R509/R510 的 A/B 轮不同）⇒ 数字只能作探索读数，不得当预注册假设的证伪。
2. **`usage_self=null`**：本侧跑器未落 per-arm usage ⇒ tokens 由 `usage_from_dumps` 按 dump 区间事后重算（`unreported_usage=0`，非冒充 0）。
3. **s12-r1/p3 的 0 调用**是模型「口述不落盘」行为（dump #029/#030：9,442/12,197 字符纯文本、`finish_reason=stop`），**不是器具故障**；已按行为型失败记入。
4. **n=2/臂**，且跨窗摆动显著（同题 p3：2/3 → 3/3 → 0/2）⇒ 只出区间与并列，不出显著性；本轮**无 codex 外部对照**（主线 token ≥30% 判据未测）。
5. p4 用例覆盖 p4 契约（stdout 单 JSON / 退出码 / TTL 时钟 / 原子写 / id 不复用），**未覆盖并发写与安全边界**。

## 7 下轮候选

1. **预算与规模的定量曲线**：p3/p4 × 预算 {6, 9, 12, 16} × n≥3，出「行数档位 ↔ 所需步数」曲线，替代单点结论。
2. **「口述不落盘」失败模式的机制定位**：入站/出站两侧计数（是否 `tool_calls` 被截断 / 终答早退），并给抑制策略（如强制落盘前置）。
3. **codex 外部对照补齐**：p4 同题同夹具 n≥2 两侧，落 token/调用/墙钟区间（主线判据）。
4. **审批通道扩展**：`delete_file` 之外的敏感操作（覆盖写 / 越界移动）纳入同一审批门；超时秒数的产品决策待用户裁定。
5. **预注册纪律**：探索性轮次与 A/B 轮次分开标注，起臂前落盘 `prereg-r511.json` 式文件。
