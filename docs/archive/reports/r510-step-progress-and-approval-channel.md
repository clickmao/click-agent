# R510 — 步进事件真发 + 审批通道闭环 + 自检契约泛化 (A/B 实证)

日期: 2026-09-17 (CST) · 基线: R509 (host sha12 `fe07205ba3b8`) · 本轮 host sha12 `993d0fa548e9`

## 1. 因果链 (为什么这几件事在同一轮)

R509 的欠账有二: ① `task.progress` 只在 `FrontendTaskRegistry.Progress(...)` 里**登记**, 全链无一处调用 ⇒ 前端拿不到步进 (封闭系统自证: 单测看得见 registry, 真机看不见事件); ② `RequestOperationApprovalAsync` 是保守拒绝占位 ("P2 欠账") ⇒ 前端批准/拒绝**打不通**。
主线 (铁律 10) 的单点缺陷: p3 隐藏用例 `restart_drops_expired` 反复挂 —— 自治自测面只覆盖 happy path, 契约承诺的"进程重启后状态"无人测。
三件事的共同点是**同一条链的两端**: 出站面 (前端可观测) 与自治面 (agent 自测)。故本轮同轮处理, 一次 AOT 发布。

## 2. 产出 (文件 → 命令 → 读数)

| 面 | 变更 | 证据 |
|---|---|---|
| 步进事件真发 | 新增 `src/agent.modelqueue/ActionProgressObserver.cs` (AsyncLocal 绑定, 未绑定零开销); `ActionLoop.cs` 每次工具执行后 `ReportAsync` | 单测 `R510StepProgressAndApprovalTests` |
| 前端绑定 | `FrontendApiChatRouter.cs` chat.send 作用域内 `BindProgress` → `task.progress` 事件 + `FrontendTaskRegistry.Progress` | E2E: 3 条 progress |
| 审批通道 | `FrontendPromptService` 真实现: `approval.requested` → 等 `approval.respond` → `approval.responded` 收口; 超时/拒绝/取消/被覆盖**一律不批准**; `ApprovalEnvelope.cs` 新增; `FrontendEventHub.IApprovalReplySink` + `AttachApproval`; 路由 `approval.respond` case; `Program.cs` 同源挂接 | 单测 6 条 (批准/拒绝/超时/未知 id/幂等/被覆盖) |
| 自检契约泛化 | `SessionBaseline.cs` 二.3: 契约的**每条非功能语义** (重启后状态/持久化重放/并发原子性/过期清理) 要有独立用例, 只测主路径视为未自检 | A/B 见 §3 |

AOT: `dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_r510` → rc=0, **IL 警告 0**, 体积 15,438,368 B (R509: 15,425,840 B, **+12,528 B / +0.08%**)。

单测: `dotnet test src/agent.tests/agentframework.tests.csproj` → **1653/1653 PASS** (含新增 10 条); 变更前同工程 1653/1653。

## 3. 真机 E2E (AOT + frontend-api + 动作环开 + 真模型)

`bash eval/rover/r510/run_e2e_frontend_progress.sh` → `E2E_RC=0`, 判据 6/6 PASS (机械判分, `assert_e2e_progress.py`):

- 事件序: `task.started → task.progress×3 → task.completed` (R509 只有 started/plan/completed, **无 progress**)
- 首条 progress: `step_index=1, tool=write_file, ok=true` ⇒ 步号/工具/成败来自**真实执行**
- 反伪造: 工作区真的出现 `r510_progress.txt` (ws_files 非空) + 回复长度 173 ⇒ 非自报
- `state.snapshot.tasks[0]`: `state=done, step_index=3, current_action=run_command`
- 审批回程负控: `approval.respond(apr-doesnotexist)` → `outcome=unknown_approval` (**不静默当批准**)

## 4. A/B: 自检契约泛化 vs 基线 (`run_ab_selftest_clause.sh`, 同窗·同夹具·同模型·每跑次独立 session)

夹具 md5 一致 (`cases/p3_cases.py` = r508/r509 冻结件 `8d13fd53…`); 起手闸连续 2 PASS 才起臂; 预注册 `eval/rover/r510/prereg-r510.json` (起臂前写入)。

| 臂 | host sha12 | 全对轮次 | 逐用例 | 隐藏用例 `restart_drops_expired` | calls/轮 | tokens/轮 (adapter 真值) | 用时 |
|---|---|---|---|---|---|---|---|
| agentBefore (旧 AOT) | fe07205ba3b8 | **1/3** | 24/36 | **1/3 PASS** | 7.0 | 91,252 | 35.6s |
| agentAfter (新 AOT) | 993d0fa548e9 | **3/3** | 36/36 | **3/3 PASS** | 7.0 | 87,057 | 36.2s |

失败点名 (before): rep1 仅 `restart_drops_expired`; rep2 11/12 挂 (产物未成形)。
⇒ 单点攻坚的**靶点用例从 1/3 → 3/3**; 调用数不变, token -4.6% (见 §5 口径)。

**机制归因: 未成立 (如实记)**。回看落盘产物: after 臂 2/3 跑次写出了自带 `--selftest` 且含 restart 相关用例 (`selftest.py` restart_hits=2/3, 195/227 行); before 臂 1/3 (ab1, hits=4; ab3 的 selftest 无 restart 命中; ab2 无 selftest)。**但 before-ab1 自带 selftest 含 4 处 restart 相关仍挂 `restart_drops_expired`** ⇒ 本轮读数只能记作「条款 + 采样」的共同结果, **不能**把 1/3→3/3 归因给该条款单独作用 (n=3, 方差占优)。机制归因留 C3 (n≥5 + 逐跑次自测覆盖度编码)。

## 5. 验收前置 (`exec_precondition.py --round R510`) — 机器复跑, 非自报

```
DISCOVER layout=project windows=3
r510ab1 agentAfter/p3 12/12 rc=0 correct=True claimed=True | agentBefore/p3 11/12 rc=1 correct=False
r510ab2 agentAfter/p3 12/12 rc=0 correct=True claimed=True | agentBefore/p3 1/12  rc=1 correct=False
r510ab3 两臂 12/12 rc=0
SELF_REPORT_AGREES=True
EXECUTABLE_AND_CORRECT=False (全局)
PRECOND_RC=1
```

- rc=1 的阻塞**全部来自对照臂** (旧 AOT, 已知故障基线的测量装置), 交付物臂 (新 AOT) 三窗全 12/12。
- 依铁律 11: **rc≠0 ⇒ 本轮 token/调用降幅一律标「参考（未可验收）」** —— 本报告 §4 的 calls/tokens 列即按此标注, **不作验收依据**。
- `evidence_scope` 未在 prereg 中声明 (SCOPE_SOURCE=None) ⇒ 不追溯补写 (禁事后补记); 下轮若再用"含基线故障臂"的面板, prereg 里先写 scope。

## 6. 诚实边界

1. **未测到**: 审批通道的**真机**触发 —— 动作环声明工具只有 `list_dir/read_file/write_file/run_command`, 无删除类工具 ⇒ `Workspace` 的删除审批在真机不可达; 审批闭环只有单测证据 (E2E 只做了 `unknown_approval` 负控)。下轮候选: 动作面加 `delete_file` 工具 (走审批) 并把 E2E 打通。
2. **未测到**: `task.progress` 在"前端断线重连"时的补发路径 (只测了同连接内实时事件 + snapshot 快照)。
3. **样本量**: A/B 各 3 轮、单题 (p3)、单模型; 质量提升的读数稳健性有限 (before rep2 的大面积失败说明该管道自身方差大), 不做跨轮相减结论。
4. **未验收**: 主线的 token 判据 (≥30%) 本轮**未测** —— 本轮无 codex 侧对照, 也不涉及 R1 role 挂载轴; §4 的 token 数字只是同题 A/B 的参考读数。
5. `SessionBaseline` 前缀文本有改动 (**+74 字符**), 前缀长度/缓存口径需在下轮 KPI 复算时刷新既有控制期望。

## 7. 下轮候选

- R511-C1: `delete_file` 工具 (经审批) + 真机 E2E 打通 `approval.requested/responded` 全闭环 (补 §6.1 空档)。
- R511-C2: 断线重连时 `task.progress` 补发 (以 `step_index` 去重) + E2E 断言。
- R511-C3: 主线继续单点: 对 `restart_recovery` / `incr_concurrent_atomic` 做同类 A/B (n≥3), 并核 `SessionBaseline` 前缀 KPI 期望刷新。
- R511-C4: 全表 `evidence_cmd` 可重放性普查 (静态) + 本地 3B 长原文回放。
