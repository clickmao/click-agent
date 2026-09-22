# R630 轮报告 · 恒前缀尾部追加块（规格保真自检）轴

- 轮次：R630（2026-09-22）· 协议：`docs/plans/RF0005-completion-protocol.md` §1/§2/§3 · 级别 **L3**
- 单一变量轴：`AGENTFRAMEWORK_R1_ACTION_PROMPT` 第四取值 `spec`（既有 env，新档位）
- 判决：`rc=0`，`J0=J1=J2=J3=J4=true`；**轴裁定 = 定案关闭**（`swing=8 ≥ effect=0`）

## 1 起手闸与主线提醒（一步一行）

| 步 | 读数 |
|---|---|
| roundcheck preflight | `PASS FAIL=0 WARN=0`（P8 `PUSH_PAUSED=yes`） |
| 起手闸条款 | `ceiling=2863 prev_swing=285 margin=153 REQ=2803 (cap_binding=true spread=1MB)` |
| 起手闸 A1/A2 | `PASS` / `PASS`（mem 2865 / 2853 MB） |
| 起手闸 B（leak-selfcheck） | `rc=0` |
| 主线 | 铁律 10/11：真实开发任务 × 外部真值同环境同输入对照；本轮**外部真值臂缺席**（见 §5） |

## 2 产品侧改动（净改动**非零**，与 R629 的零改动轮不同）

| 文件 | 改动 | 量级 |
|---|---|---|
| `tools/r1gen/r1prompt.py` | 新增 `PREFIX_SPEC`（只加厚） | +25 / −0 |
| `tools/r1gen/gen_csharp.py` | 轴三档 → 四档（生成器） | +35 / −7（删行均为注释与档位表达式） |
| `src/agent/contract/StructuredPrompt.cs` | **生成物**（`gen_csharp.py` 产出） | 新增 4 成员 |
| `src/agent.tests/R524PrefixStabilityTests.cs` | 三条新单测 | +69 / −0 |
| `docs/api-surface.baseline.txt` | API 基线重生成 | **仅本轮 5 行**（已逐行核对） |
| `docs/verification-registry.json` | 器具绑定重钉 1 行（`r580.*`）+ 追加 1 行（`r630.*`） | 声明字段，未放宽判据 |
| `eval/capability/baselines.json` | 追加 2 条冻结不变量锚（`F_env.prefix.spec_{chars,sha256}`） | +30 / −0 |

## 3 机制面（器具闸）

- 前缀不变量 `gen_prefix_r630.py` **rc=0**：四档 15796 / 15794 / 15675 / **16182**，sha 互异，
  `body_append_only=true`（去尾闭合标签后新块正文以旧块正文逐位为前缀），`default_bytes_unchanged=true`。
- 同源闸 `gen_csharp.py --check`：`R1GEN_DRIFT_FILES=0`。
- AOT：`PUBLISH_RC=0 IL_WARNINGS=0 ERRORS=0`，ELF 19,870,960 B，sha16 `cefd045e8d1d4258`；
  双档装载冒烟 `SMOKE_RC=0` ×2，`drift_rc6_hits=0` ×2。
- 真机臂 J0/J1：T 档逐跑次 `prefix_chars=16182 ∧ prefix_sha256=b687c6dd…`（6/6），
  C 档 `15796 ∧ 25c97bef…`（6/6）⇒ 两档可区分；J4 C 档零回归成立。

## 4 能力面与成本面（真机 2 窗 × reps3）

| 臂 | 通过数（w211 / w212） | 中位 | 极差 | 计划未跑完 | 调用 | 新算 prompt | completion | 命中率 v_all |
|---|---|---|---|---|---|---|---|---|
| T（spec） | 58,56,58 / 58,50,58 | 58 / 58 | [50,58] | 3/6 | 11 | 11,251 | 46,482 | 0.8915 |
| C（缺省） | 58,58,58 / 58,54,58 | 58 / 58 | [54,58] | 1/6 | 14 | 11,061 | 58,490 | 0.9147 |
| C1（codex 真值） | **未测**（本窗未跑） | — | — | — | — | — | — | — |

- **效应 = 0**（逐窗中位差 0），**摆动 = 8**（T 极差 8 例；C 极差 4 例）⇒ §3 定案关闭：该轴**非承重变量**，禁调阈值。
- 失败形态：`stdout_mismatch`（期望 `WIN 15 15` / 格子图，实测**空**）——尾块**未消除**该形态。
- 成本列只作**并列观测**：铁律 11 前置器 `rc=3（DISCOVER_FAIL）` ⇒ **不宣称任何降幅**。
- 外部真值列：`F_merge.quality.cases_median_truth`（同冻结题集 sha，**跨窗**）⇒ 仅作参考，不进 J2。

## 5 器具自捕缺陷（三条，**留档不翻案**）

| # | 现象 | 真因 | 处置 |
|---|---|---|---|
| 1 | v1 12/12 跑次 0 秒退出 `rc=6` | 驱动脚本未做 cfg 端口替换、未起中继适配器（`Connection refused 127.0.0.1:48600`） | 跑次目录改名保留 `runs/r630-v1-void-notransport`（禁删）；脚本补端口替换 + 适配器就绪闸 |
| 2 | v1 判据器在**同一批 VOID 日志**上给 `rc=0 / J0=true` | 判据只看前缀读数，不看是否真达模型 | 留档 `v1-judge-falsegreen-r630.json`；判据加 **VOID 闸**（`calls<1 ∨ stage=llm_transport`） |
| 3 | v2 判据器把 `rc=5`（计划未跑完，**已真实调用**）当 VOID ⇒ 剔 5/12 跑次 ⇒ 停链 `rc=3` | 判据把「rc≠0」当「未达模型」 | 留档 `v2-judge-r630.json`；**同一批日志零重测复算** ⇒ v3；影子自检扩到 **7 态**（S6 全 VOID 必判 rc=2 / S7 计划未跑完不得判 VOID） |

另：`R1Transcript.prefix_pinned` 布尔仍按**缺省档**钉值比较 ⇒ spec 档恒 `false`（标签面缺陷，**本轮只登记不改**，防混淆单变量）。

## 6 文献小步（每轮必跑）

检索 1 次（预算 ≤3）：`"self-verification" "specification compliance" LLM agent code`（cs.CL, sort=date）。
**采信 0 · 观察 1 · 证伪 0**；候选 = 「判据聚合形态：总体通过数中位 → **按题族分列 + 族级最小值**」
（出处 arXiv **2609.23377v1**，逐字引文与权威性代理见 `docs/research/lit-review-ledger.md` §R630）。
连续 0 采信计数 = 1（未达 3 ⇒ 不降频）。

## 7 收口

- 形式门禁（`VerificationForm|SkillGeneralization|DevPlanDocRef`）**14/14**；
  `R524PrefixStability` **20/20**；`gen_csharp.py --check` DRIFT=0。
- `python3 eval/capability/status_gen.py --check` ⇒ **PASS（违规 0 / 基准漂移 0 / 缺源 0）**。
- kpi 行：`eval/capability/kpi.jsonl` R630（带 `baselines` id 列表）。

## 8 下一轮候选（逐候选，不挑选式汇报）

| 候选 | 状态 | 原因 / 判据 |
|---|---|---|
| C1 · 判据聚合形态改为**按题族分列 + 族级最小值**（J2 单一自由度） | **未做** | 文献候选，本轮预算被主线真机臂吃满；判据 = 同批 run 上两形态给出族级**符号相反**的读数 |
| C2 · 同窗 codex 外部真值臂（补 `C1` 列） | **未做** | 本轮窗未跑 codex（省时窗约束）；补后 J2 可加对外宣称 |
| C3 · `R1Transcript.prefix_pinned` 改为**档位感知**（`Sha256PinnedForCode`） | **未做** | 属**标签面**改动，与轴同轮会混淆单变量 ⇒ 单独立轮，判据 = spec 档 `prefix_pinned=true` 且缺省档不变 |
| C4 · 铁律 11 前置器对 r630 的题集发现（`DISCOVER_FAIL rc=3`） | **未做** | 需把 r630 的 taskset/两侧落盘摘要纳入发现契约；否则成本列永久只能并列 |
| C5 · 复现 R618 的 `AGENTFRAMEWORK_R1_ACTION_EXEC` 轴在 w211/w212 窗的读数 | **未做** | 与 R618 窗集不相交 ⇒ 只可并列不可相减；优先级低于 C1/C3 |
