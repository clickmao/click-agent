# EXP1-Q45 / 命名空间 `eval/capability/r518/` — improvements.md 轮节覆盖面机检化 + 8 缺节回填

> 命名空间说明：`r518` 是**本作业（60m 能力自检循环）本轮的器具目录**（`eval/capability/` 父目录下），
> 与主线轮号 `R518` 无因果关系；主线对照轮使用 `eval/rover/rNNN/`。
> 本轮 `route.first` = `EXP1-Q44` 的 `next①`：「`improvements.md` 的 R404–R416 轮节回填（文档轮）」。`EXP1-Q45` 将其**闭合**。

## 1. 因果链

`improvements.md` 的「轮节」是**跨轮可比性的权威台账**：任何一轮的读数只在「该轮有节 + 该节带着来源锚」时
才能被后人复核。历史登记（R409 段、R420 段）两次声称「R402–R407 / R404–R416 未回填」，但**没有任何工具**
能回答「现在到底缺哪几节」——只能靠人读。⇒ 本轮把「覆盖」变成**可机检判据**，先把缺节机检出来，再逐节回填。

## 2. 判据（`scan_round_sections.py`，rc 0/1/2）

| 判据 | 语义 | 现行读数 |
|---|---|---|
| **C1 覆盖** | 语料根里的轮号必须在文档有同名节（节轮号 = 节头行**第一个** `R\d{3}`） | PRE 缺 **8** → POST **0** |
| **C2 分区序** | 轮号 ∈ [401,421] 的节沿行序**非递增** | PRE 违例 **1**（R403 错位）→ POST **0** |
| C3 信息项 | 全局序违例数 / 同轮号多节（多分区下可合法） | 37 → 36；duplicates 4（跨区，合法） |

- **语料根 = git 提交标题 ∪ `docs/plans/*r<NNN>*.md`**。只扫 git 标题会**结构性看不见** R405/R406：
  这两轮的产物在 R407 的**同批提交** `cd8feeb` 内（提交标题不含其轮号）⇒ 判据可达面 < 语料面。
- 分区序判据的区间 [401,421] 是**人为选定窗口**；窗口外的全局序违例（36 条，历史区/版本区各自有序）只作信息项。

## 3. 真机读数

```
PRE  (/tmp 原始: scan-pre.txt)                     POST (scan-post.txt)
UNIVERSE: git=19 plan_only=2 [405,406]             UNIVERSE: git=19 plan_only=2 [405,406]
SECTIONS=118  ZONE=13                              SECTIONS=126  ZONE=21
C1 MISSING n=8: R402 R404 R405 R406 R407           C1 MISSING n=0
               R417 R418 R419                      C2 ZONE_ORDER_VIOLATIONS n=0
C2 ZONE_ORDER_VIOLATIONS n=1 (R403 @line736)       C3 INFO global=36 duplicates={507,502,501,482}
SCAN_EXIT=1                                        SCAN_EXIT=0
```

回填动作自身的守恒读数（`backfill_round_sections.py`）：

| 项 | 读数 |
|---|---|
| 节数 | HEADERS **128 → 136**（期望 +8，命中） |
| 总行数 | 2714 → **2790** |
| R403 节搬迁 | 搬前搬后**逐字节相同**（1941 B），落点 `R404 < R403 < R402`（`R403_POSITION_OK=True`） |
| 原文件被改行数 | **2**（即两处过期口径行；原文逐字保留，仅行尾追加更正段） |
| 幂等 | 重跑 ⇒ `IDEMPOTENT_SKIP`（rc=0，零变化） |
| 器具自检 | `--selftest` **n=4 / fails=0**（缺节必抓 / 分区序违例必抓 / 基线必绿 / **报告路径冒烟**） |

新增/回填的 8 节：`R402`（rover 生成链性能归因）`R404`（bge 融合对账 + 口径订正）`R405`（本机增强计划）
`R406`（Jinja 子集 chat template）`R407`（qwen2 attn bias 层归属）`R417`（探针反饱和）`R418`（过程/成本 KPI）
`R419`（探针多轮化）。每节带**来源锚**（提交 sha / 计划文档 / 证据目录）并标「**读数未改**」。

## 4. 本轮暴露的器具缺陷（全部真机暴露后修，前一版读数作废）

1. **节轮号取「行内最大 R 号」** ⇒ `## R403 — …随 R408 退役…` 被读成 `R408` ⇒ 同时误报「R403 缺失」与「R408 重复」。
   修正 = 取**第一个** `R\d{3}`。
2. **`report()` 键类型错误**（`len(int)`）⇒ 真机首跑即崩，而 `--selftest` 全绿：自检只覆盖 `analyse`，
   **未覆盖报告路径**。修正 = 加「报告路径冒烟」臂（缺此臂 = 空心自检）。
3. **行锚手抄漂移两连**：① 整行字面量锚多打 `- ` ⇒ 命中 0；② 改用行前缀后，`lstrip("-*>")` 会**吃掉加粗标记 `**`**
   （`**台账缺口…` 被削成 `台账缺口…`）⇒ 命中 0。修正 = 只剥「项目符号 + 空格」形态；两次都靠 **fail-closed 未写盘**兜住。

## 5. 复现

```bash
cd /home/agentuser/AgentFramework
python3 eval/capability/r518/scan_round_sections.py --selftest   # SELFTEST_EXIT=0 n=4
python3 eval/capability/r518/scan_round_sections.py             # SCAN_EXIT=0 (PRE 状态为 1)
python3 eval/capability/r518/backfill_round_sections.py         # 幂等: IDEMPOTENT_SKIP
```

## 6. 诚实边界

- 回填内容**全部来自**提交标题 / 计划文档 / 落盘产物 ⇒ **不是新实验读数**；R405 无收口节 ⇒ 状态按计划原文
  登记（「计划已登记；P0/P1 待执行」），**不补写**读数；R404 无独立轮志 ⇒ 证据目录 `eval/bge/r404/`。
- 36 条窗口外全局序违例**未被判定**（历史区/版本区各自有序）⇒ 不得读作「文档已全局有序」。
- 与对侧（30m 作业）并发：本 tick 只做只读机检 + 过滤式形式门禁，不占主线真机臂/发布物。
