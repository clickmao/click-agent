# R492 · 付费量口径审计：中继真值 vs 宿主打点（含对 R491 汇报的一处更正）

- 轮次: R492 | 落盘: 2026-09-16T16:16:56+08:00 | 起手闸: **红**（MemAvailable 2078 MB < 2650 MB ∧ 对侧 EXP1-Q34 正在跑 dotnet 门禁 pid 1827142）⇒ 本轮**不起上游、不起 AOT**，只做离线审计
- 预注册: `eval/rover/r492/prereg_r492.json`（先于机检落盘）
- 器具: `eval/rover/r492/host_log_audit.py`（通用代码逻辑，语言无关；只读已录产物）
- 读数: `eval/rover/r492/host_log_audit.json`

## 因果链

R491 汇报把「中继付费调用数」与「宿主 `llm_call` 行数」当同义词 → 核账发现 R491-Aroleb 中继 17 次 vs 宿主 `llm_call` 16 行 → 若按宿主合计会少算 5,792 tok → 追下去发现**行其实存在**（记在 `point=llm_call_continue`），但该行**不带 prompt 量** → 结论从「漏记一次调用」更正为「**token 字段覆盖不全**」，并顺带查出两个更常见的陷阱（空正文诊断行同 `request_id` 重复 ⇒ 不去重会**多算**调用；旧格式 r474/r477 才是真未打点）。

## 读数（24 臂全量核账）

| 格式代 | 臂 | 中继付费调用 | 宿主调用（去重后） | 调用 gap | 宿主 token 字段缺失 | 判 |
|---|---|---|---|---|---|---|
| 旧格式 | r474/Arole | 20 | 16 | **+4** | 16,373（21.52%） | GAP |
| 旧格式 | r477/Arole | 21 | 13 | **+8** | 26,320（35.74%） | GAP |
| 对齐后 | r482/Arole | 21 | 21 | 0 | 0 | OK |
| 对齐后 | r487/R、r488/Ss | 14 / 14 | 14 / 14 | 0 | 0 / 0 | OK |
| 对齐后 | r489/R2 | 16 | 16 | 0 | 0 | OK |
| 对齐后 | r490/T1 | 6 | 6 | 0 | 0 | OK |
| 对齐后 | **r491/Aroleb** | 17 | 17（含 1 续调用点） | 0 | **5,215（6.37%）** | OK（量缺） |
| 对齐后 | r491/T1·T2·T3 | 6 / 6 / 6 | 6 / 6 / 6 | 0 | 0 | OK |

- **调用数**：r482 起 100% 对齐（18 臂全 0 gap）；真缺口只在旧格式 r474/r477（4/3/8/3 次）。
- **token 量**：唯一缺口 = r491/Aroleb 的**截断续调用 prompt 5,215 tok**（宿主 `llm_call_continue` 行只落了 retry completion 577，未落其 prompt）⇒ 用宿主口径会读到降幅 **70.54%**，真值 **72.42%**，**低估 1.88 pp（保守方向）**。
- **重复行**：r482 起各臂 `host_dup_rows_collapsed` = 3–10（空正文诊断行与 `llm_call` 同 `request_id`）⇒ **不去重会把调用数算多**（NC 已抓）。

## 候选台账（并轮 · 逐项）

| 候选 | 状态 | 证据 |
|---|---|---|
| ①宿主打点漏记审计（付费量双列口径） | **做** | 24 臂核账；3 负控全检出（`--no-dedupe`/`--ignore-continue`/`--drop-host-row` 均 `detected_inconsistency=True`） |
| ②G2 判据 supersede（悬空 ≤0.10 锁为验收线） | **做** | `eval/recall/prereg_r492_g2_supersede.json`（旧 `prereg_r481a.json` 逐字节未动，sha256 `bed52c5b…` 记录在案） |
| ③付费明细明文产物入库 | **做** | `eval/rover/r491/paid-plaintext/`（13 件）+ 3 导出器具，随本轮提交 |
| ④配对剪裁门开真机 T×3 | **未做** | 起手闸红（2078 MB < 2650 MB）+ 对侧 dotnet 占用 |
| ⑤禁常量兜底臂真跑 | **未做** | 同上（需上游窗口） |
| ⑥R486 门禁 + 提交 | **未做** | 同上（需 dotnet 窗口） |
| ⑦链级 E2E（工具 + 长上下文） | **未做** | 同上（需上游 + AOT 重发布） |
| ⑧EXP1 面重审 | **未做（避双写）** | 对侧 EXP1-Q34 正在写 `verification-registry.json` |

## 更正（对上一条汇报）

上一条我写「宿主打点漏记 1 次付费调用（5,792 tok）」——**该表述不成立**，撤回。事实：该调用**已打点**（`point=llm_call_continue`，`reason=truncated`，`recovered=true`），漏的只是它的 **prompt 量 5,215 tok**；`5,792 = 5,215 + 577`，其中 577（retry completion）宿主有落。

## 诚实边界

1. 预注册 H1（「R491-Aroleb gap==1」）与 H3（「gap 只出现在带工具轮的臂」）**被本轮实测否证** ⇒ 按判据纪律记为 FAIL + 单列 `checks_posthoc`，未回改预注册文件。真结论 = 调用数无缺口、量字段有缺口。
2. 未做**代码级**根因（为何 `llm_call_continue` 行不落 prompt）——需 dotnet 窗口读实现。
3. 旧格式 r474/r477 的 gap 属历史读数，其原报告用的是中继真值 ⇒ **不改变任何已发布降幅**，只说明「凡按宿主行数汇总的旧口径会偏低」。
4. 本轮**零真机调用**，无新 token 读数；`verification-registry.json` / `improvements.md` 未写（避与对侧双写），登记结转下轮。

## 下轮候选

① 把「付费量双列 + `llm_call_continue` 补 prompt 量」做成打点修复（需 dotnet 窗口，属**实现**而非器具）② ④⑤⑥⑦ 四个窗口受限候选（起手闸转绿后并入同一轮）③ `verification-registry.json` 补 R492 行 + R491 明文产物绑定 ④ 旧格式臂（r474/r477）gap 的历史一致性复核（只读）
