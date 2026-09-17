# EXP1-Q46 / 命名空间 `eval/capability/exp1-q46/` — 记录面**假开放项**闭合 + 时效字段登记

> 命名空间说明：`exp1-q46` 是本作业（60 分钟能力自检循环）本轮的器具目录；主线对照轮用 `eval/rover/rNNN/`。
> 本轮 `route.first`（起手读数）= §7 最新块里的「**另一本台账（未在本轮动）**: `improvements.md` 自身的
> **R404–R416 轮节**尚未回填」。本轮把它**闭合**（记录面），并登记块内两处**时效缺口**（只登记、不代写）。

## 1. 因果链

`scripts/capability_cycle_status.py`（v5/D8）把「推进对象」路由到**主报告 §7 最新块**的点名开放项。
该块第 185 行的开放陈述写于 EXP1-Q44（`32125b7`）时点，**盘面随后已变**：EXP1-Q45（`1ef590a`）把
`improvements.md` 的 8 处轮节逐节回填并机检化（`eval/capability/r518/scan_round_sections.py`：
前态 `C1 MISSING n=8` → 后态 `n=0`，`SCAN_EXIT=0`），且 `docs/improvements.md` 自身已带更正行
（「旧口径作废」留痕）。⇒ 路由指向的是一个**假开放项**：每个 tick 都会先去推一件已经做完的事。

**归属（三态分列）**：回填动作 = `self`（本循环上一 tick，EXP1-Q45）；主线侧机检更正 = `foreign`（R518）；
本轮 = 只在记录面闭合 + 登记，**不改产品源码、不跑真机臂、不占主线轮号**。

## 2. 预注册与裁定（`prereg_q46.json` → `verdict_q46_v2.txt`）

| 判据 | 预注册内容 | 实测 | 判 |
|---|---|---|---|
| P1 | 起手: `master_open==1` ∧ `route.primary=master-block` ∧ first 含「另一本台账」 | 完全命中（`status_pre.json`） | PASS |
| P2 | 盘面证伪: scanner `rc=0` ∧ `C1 MISSING n=0` | `SCAN_EXIT=0` / `C1 MISSING n=0` / `ZONE 21` | PASS |
| P3 | 改写后: `master_open==0` ∧ `route.primary=backlog` ∧ first=`exp1` ∧ `open_count=8` | 四项全中（`status_post_v2.json`） | PASS |
| P4 | 不变量: backlog 面逐字不变（8/8）∧ `block_fields=29` | 8 条逐字相同；29→29 | PASS |
| P5 | 最小 diff: 本文件 `numstat == 1 1`，行数 307 不变 | `1 1`；307→307 | PASS |
| P6 | 幂等: 编辑器二次运行 ⇒ `IDEMPOTENT_SKIP` ∧ sha 不变 | rc=0，`sha16` 不变 | PASS |
| P7 | 成对负控: (a) 合成三臂 1/0/2；(b) 前态锚（不可变提交 `32125b7` 的 blob，断言祖先 ∧ 字节不同）复现 `master_open=1` | (a) 1/0/2；(b) `master_open=1` ∧ first=前态原文 | PASS |
| P8 | 探针自检改写后仍 `34/34` | `34/34 passed`，rc=0 | PASS |
| P9 | 形式门禁（dotnet 过滤）14/14；窗口被占则如实标 SKIPPED | **SKIPPED**（见 §4 ②）+ 零 dotnet 替代机检 rc=0 | 降级（如实标注） |

裁定合计：**14/14 PASS（`VERIFY_EXIT=0`）**。

## 3. 真机读数（改写前 → 改写后）

```
master_open         1        →  0
route.primary       master-block → backlog
route.first         「另一本台账…」 → exp1 本地索引/代码引用图（进行中, 探索）
open_count          9        →  8      (backlog 8 逐字不变, 仅 master 项闭合)
block_fields        29       →  29      (行数不变, 仅一行内容替换)
close/quoted_fenced 3 / 1    →  3 / 1   (新行零围栏命中 = 不是靠「含关闭词」凑绿)
```

## 4. 自捕器具缺陷与诚实边界（各自保留首跑读数，不覆盖）

① **「旧键必须消失」在键与新文本重叠时恒假（两处，本轮自捕）**
   - 一部 `edit_block_q46.py`：用「另一本台账」当锚点键，而该串在新文本里**同样出现** ⇒ 读回
     `readback_anchor_gone` 恒假 ⇒ `rc=2 READBACK_MISMATCH`，而**改写其实已落盘**（rc 与行为分离）。
     首跑 `edit_apply.txt` 原样保留；修法 = 锚点键换成**前态独有**串；修后 `edit_apply_v2.txt` = `IDEMPOTENT_SKIP rc=0`。
   - 二部 `edit_line_v2_q46.py`：同族第二次（键在新文本里仍保留）⇒ `edit2_apply.txt` rc=2 恒红，
     修后 `edit2_v2fix.txt` = `IDEMPOTENT_SKIP rc=0`。**纪律**：旧键必须**前态独有**（机检：前态计数=1 ∧ 后态计数=0）。
② **形式门禁 SKIPPED（窗口被对侧占用）**：13:46:58 窗口体检（`window_pre_formgate.txt`）显示对侧 30m 作业的
   `eval/rover/r483/preflight_gate.py --round R519` **在飞**、`MemAvailable=2579MB`（低于 2800 阈值） ⇒ 真缺陷 71
   纪律下**不跑 dotnet build**（会打断对侧 R519 起臂）。替代机检（零 dotnet，`subst_check_v2.txt`）= 新行内
   **4 条路径引用逐条存在** ∧ **3 个提交号存在且标题语义相符** ∧ `docs/improvements.md` 含 R404 段与更正行；
   三处形式门禁作用域（登记表 / `skills/` / `docs/plans/`）**触达数 = 0/0/0** ⇒ 本轮改动不落其作用域内。
   **残余风险**：门禁未跑，属**覆盖性复核缺口**，如实登记（不作「已过门禁」宣称）。
③ **时效字段（只登记不代写）**：块内「最近一轮（R509）/ HEAD `0b88277`」滞后现盘 HEAD `29f75c3`（R518）
   **9 轮**。该字段刷新归**主线轮收口**（共用工作树下代写会与对侧写者撞车）⇒ 本轮只登记。
④ **覆盖**：本轮改的是**记录面**（陈述与机检读数对齐），不构成能力面读数；`route` 翻转只说明「路由的输入
   面变准了」，不等于能力提升。
⑤ **路径引用不完整（一部自身缺陷，机检抓到）**：v1 行写裸文件名（`scan-pre.txt` 等）⇒ 替代机检 rc=2；
   按 R435 纪律**把引用写显式**（v2，改文档不放宽判据），修后 rc=0。首跑 `subst_check.txt`（rc=2）原样保留。

## 5. 文件清单

| 文件 | 作用 |
|---|---|
| `prereg_q46.json` | 预注册（P1–P9，含被证伪/降级的单列） |
| `edit_block_q46.py` / `edit_line_v2_q46.py` | 两版编辑器（派生锚点 + 唯一性 fail-closed + 幂等 + 行级不变量 + 读回） |
| `marker_pair_q46.py` | 成对负控（三臂，样本取自**产物原文**：前态锚 blob / 现盘真机行 / 合成真开放行） |
| `capture_q46.sh` / `window_check.sh` | 读数采集（分步落盘 + 显式标记）与起手窗口体检 |
| `subst_check_q46.py` | 零 dotnet 替代机检（路径/提交号/作用域触达） |
| `verify_q46.py` | 预注册裁定（14 条 CHK + 显式退出码） |
| `append_kpi_q46.py` | 台账追加（键集对齐 + 幂等 + 全文件可解析回读） |
| `status_pre/post(_v2)/nc_prestate.json` | 三态读数（前态 / 后态 v1 / 后态 v2 / 前态锚臂） |
| `edit_*.txt` / `marker_pair*.txt` / `subst_check*.txt` / `verdict_q46_v2.txt` | 逐次运行的**原始**读数（失败读数不覆盖） |
