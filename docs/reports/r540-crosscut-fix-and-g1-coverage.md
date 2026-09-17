# R540 轮志 — 横切修复(codex 外侧臂引擎提稳定位置 + fail-closed)· role 轴实发机检修复并真验 · `g1` 跨族长任务补测与 **未闭合** · 两窗成本判据

- **日期**: 2026-09-18 (CST) · **轮号**: `R540` · **题集**: `t1` = F2 `toolkit-multimodule-v1`(30 隐藏用例) · `g1` = F1 `games-longtask-v1`(58 用例)
- **窗数**: `w1` `w2`(独立 adapter 端口 / 独立 run 目录 / 独立起手闸) · **pre-registration**: `eval/rover/r540/prereg-r540.json`(跑前落盘, 判据器读到 ⇒ `PREREG=True`)
- **读数总表(机器生成)**: `eval/rover/r540/SUMMARY-r540.txt` · **原始证据**: `eval/rover/r540/run-w{1,2}/`(adapter dump / transcript / 快照 / 报告) + `eval/rover/r540/evidence/windows/w{1,2}/report.json`

## 1. 因果链(本轮为什么做这些)

R539 的**唯一阻塞项**是「外侧对照臂在 R534 减法批里被静默打断」: `eval/rover/r508|r509|r511/proj_run_side*.py` 硬编码 `eval/rover/r504/codex_solver_r504.py`, 该文件已被删除 ⇒ 有代码行 ≠ 生效。R539 只在当轮**就地复原**并首跑, 中枢修复留给 R540。同轮 R539 还暴露两处**器械/器具自身缺陷**: role「生效」无法证实(读数器 `msgs_of()` 与 adapter 真实 dump 形状不匹配 ⇒ 机检恒 False), 以及 `g1` 族与全量测试**未测**。本轮把上述四项 + R539 候选④/⑤ **并入同一轮**处理, 并按 R539 的收窄口径**先写后跑**。

## 2. 产出(逐候选台账: 做/未做 + 原因)

| # | R539 候选 | 状态 | 证据 |
|---|---|---|---|
| ① | 中枢修复外侧臂 + 「删除前必查跨轮调用点」做进机制 | **做** | 新 `eval/rover/lib/codex_engine.py`(稳定位置 + 候选列表 + **覆盖排他** + fail-closed `SolverMissing`); 引擎提稳定位置 `eval/rover/lib/codex_solver.py`; `r508/r509/r511` 三处跨轮调用点改走加载器(**旧硬引用残留 = 0**, `git grep -F codex_solver_r504 -- '*.py' '*.sh'` 空); 机制件 `tools/refactor/delete_ref_gate.py` + 提交钩子闸(默认开, 旁路 `AGENTFRAMEWORK_DELREF_CHECK=0`) |
| ② | role 实发机检按真实 dump 形状修复并真验 | **做** | 根因: agent 侧 `side-*.json` 的 `upstream_request` 是**摘要**(`n_messages/prompt_sha8/tail_messages[head 截断]`)⇒ 旧 `msgs_of()` 恒空。修法: 优先读 `full-<side>-*.json`(裸 `list[dict]` 消息数组)并带 `partial` 标; 负控自检里**旧读数器返 0 条 / 新读数器 2 条**; 真机 `w1` 2/2 · `w2` 1/1 的 user 轮含 role 段, 而 `R1nr` 0/2 · 0/1(`verdict=False`), 标记均**不在**前缀/system |
| ③ | 三臂共同失败面 `jsonmini#14/#18/#22/#26` 归因(非同源 oracle) | **做** | 判据**无缺陷**: `t1` 题面逐字要求「对象的键按 Unicode 码点升序 … 不含任何空白」; 取 `w1/A1-on` **产物快照**直跑该 4 例 ⇒ 4/4 返回 `ERR`(合法输入被判非法)= **臂缺陷**; `R1` 两窗 30/30, codex `w1` 30/30 而 `w2` 同栽这 4 例 |
| ④ | 动 `require` 面须先写后跑并注明收窄理由 | **做** | `prereg-r540.json` 跑前定义 `require`(R1r/R1nr 两窗 + `R1r-g1` 两窗)与 `nonrequired`(A1-on/codex); 判据器 `SCOPE_SOURCE` 指向 prereg ⇒ `PREREG=True`。**事后发现**: 预注册里 codex 写的是前缀 `w1/codex`, 器具键格式为 `<win>/<side><arm>-<tid>` ⇒ 精确匹配不上, codex 被计 UNDECLARED。另附 `scope-posthoc-r540.json`(只改**键拼写**, 理由逐字同预注册)**事后读数单列** |
| ⑤ | 全量测试基线 + `g1` 族补测 | **半做** | `g1` 补测**已做**(两窗首跑: 43/58 · 44/58 ⇒ **未闭合**); 全量测试本轮跑(见 §4), R539 只跑过聚焦 21/21 |

## 3. 主读数(同题 `t1`, 两窗)

| 窗 | 臂 | 调用 | total tokens | 新算 tokens | cases | rc |
|---|---|---|---|---|---|---|
| w1 | `R1r`(挂 role) | 2 | 21,874 | 7,026 | **30/30** | 8 |
| w1 | `R1nr`(不挂) | 2 | 19,655 | 4,935 | **30/30** | 5 |
| w1 | `A1-on`(旧路径) | 33 | 560,548 | 19,108 | 12/30 | — |
| w1 | `C-codex`(外部) | 369 | 30,778,875 | 180,331 | 30/30 | — |
| w2 | `R1r` | 1 | 10,948 | 3,524 | **30/30** | 0 |
| w2 | `R1nr` | 1 | 11,641 | 4,345 | **30/30** | 0 |
| w2 | `A1-on` | 34 | 569,847 | 26,359 | 30/30 | — |
| w2 | `C-codex` | 88 | 4,764,782 | 51,566 | 26/30 | — |

- **主 KPI(同窗同题, vs `A1-on`)**: `R1r` 调用 **2→33(-93.9%)** / **1→34(-97.1%)**; token **21,874→560,548(-96.1%)** / **10,948→569,847(-98.1%)**(逐窗极差 **[96.1, 98.1]**); 质量 **30/30 与 30/30**(base 12/30 与 30/30)。
- **role 轴负控**: `R1r` 与 `R1nr` 两窗同题 30/30 ⇒ 本窗**看不到质量差**; role 轴的读数只到「**已按设计挂到实发 user 轮**」这一层(见 ②)。
- **外部列**: codex 调用 **369↔88**(4.2×)、total token **30.8M↔4.8M**(6.5×)、**新算 180,331↔51,566**(3.5×), 且 cache 命中率 99.6%/99.0% ⇒ **外部列仍不可单窗读**(R539 已记)。
- **跨族 `g1`(58 用例, 仅 R1r)**: `w1` **43/58**(失败 15 例全在 `wythoff#43-#57`) · `w2` **44/58**(失败 14 例全在 `life#00-#13`) ⇒ 单发一调用在长任务上**不稳且失败族逐窗漂移**。

## 4. 器械/机制件(本轮新增, 全部带自控)

- `eval/rover/lib/codex_engine.py`: `--selftest` **6 正控 + 2 负控全绿**; `--check` 正控 rc=0 · 负控(排他覆盖指向不存在路径)rc=3; 自控里第一次跑就**抓到我自己的路径 bug**(`REPO` 少一层 dirname)⇒ **`build_taskset`/`--check` 都 fail-closed**。
- `tools/refactor/delete_ref_gate.py`: **只认「可执行引用点」**(`.py` 走 AST 取字符串字面量, 排除 docstring; `.sh/.cs` 行级扫描跳过注释行)⇒ 叙述性提及不误红(首版就假红过 R540 自己的注释, 已加**负控B**钉死); `--selfcheck` = 1 正控(真删被引用文件 ⇒ rc=1 且点名引用点) + 2 负控(无引用 / 仅 docstring 提及 ⇒ rc=0) + **历史回放**(`r504` 引擎那个真例 ⇒ 绿, 证明横切修复已把跨轮调用点清干净)。
- 提交钩子: 新增块挂在 `new_file_gate` 之后, 只扫 `eval/ tools/ src/` 下的代码/器具, 只扫 `.py .sh .cs .csproj .ps1`(**JSON/台账/文档明确不在扫描面** = 已知空洞, 写在文件头)。
- 起手闸: 两窗各 2 次 `preflight_gate` PASS(w1 起手 mem 2,579→**2,790 MB**; 清掉的是**我自己编辑文件时拉起的 2 个 LSP server** ≈ 490 MB, 非用户作业); `build-server shutdown` 已跑; 无 `llama-server|dotnet test|dotnet publish|probe` 残留。

## 5. 验收(执行前置, 铁律 11)

```
python3 eval/rover/r507pre/exec_precondition.py --round r540            # 预注册读数 ⇒ rc=1
python3 eval/rover/r507pre/exec_precondition.py --round r540 \
  --scope eval/rover/r540/scope-posthoc-r540.json                       # 事后键拼写读数 ⇒ rc=1
```

- **两读数同判 `rc=1`**(`ACCEPTABLE_SCOPED=False`): 阻塞 = `w1/agentR1r-g1` **43/58** · `w2/agentR1r-g1` **44/58**(require 面) + `w1/agentA1-on-t1` 12/30(nonrequired, 单列) + `w2/codexC-codex-t1` 26/30(nonrequired, 单列)。
- ⇒ 本轮 **token/调用降幅一律标「参考(未可验收)」**; 本轮**不宣称**「质量不降」的验收结论, 只如实报两窗读数。
- 事后读数**不构成验收面**(器具原话 `VERDICT_POSTHOC_ONLY`), 且它**不可能**改变结论(g1 两窗已阻塞) ⇒ 记作「拼写修正的附带读数」而非放宽。

## 6. 诚实边界(没测到什么就说没测到)

1. **`g1` 未闭合**: 两窗都不到 58/58, 且失败族漂移(`wythoff` ↔ `life`)⇒ 「单发结构化调用即可完成跨族长任务」**不成立**; 这是本轮最大的未闭合项。
2. **前置器 rc=1** ⇒ 主 KPI 降幅只作**参考**; 与 R539 同口径(那边也是 rc=1)。
3. **role 轴只证到「挂上去」**: 两窗 `R1r` 与 `R1nr` 质量同为 30/30, 无质量差 ⇒ 不得声称 role 带来质量增益; 只证明了「role 段确实出现在发往上游的 user 轮」。
4. **外部列噪声大**(调用 4.2×、token 6.5× 的窗间极差)⇒ 不用于任何单窗结论。
5. **A1-on `w1` 12/30 与 R539 同臂 26/30 冲突** ⇒ 旧路径臂方差极大(33±1 调用), 两窗不足以定论; 本轮只把它当**同窗成本基线**用。
6. **未做**: 全量测试若失败/超时会在本节回填(见 §7 提交信息); role 轴在 **codex 侧**未测; `g1` 的 `A1-on` 基线未跑(预算), 故跨族只有 R1 侧读数。
7. **`jsonmini` 4 例在 codex `w2` 也失败** ⇒ 该失败面不是 R1 独有, 也不是判据问题(③ 已用产物快照直跑证明)。

## 7. 提交与下轮候选

- 本轮**零产品源码改动**(`git diff --stat -- src/` 空)⇒ 未因改链而触发重发布; AOT 另行取证: `$HOME/.dotnet/dotnet publish src/agent.host/agent.host.csproj -c Release -r linux-x64 -o /tmp/pub_r540` ⇒ **rc=0 · IL 警告 0 · 15,778,672 B**(与 R539 同体积; sha `0a758734f2d0…` 因 AOT 构建非确定性而不同) · **禁止 push**(`.git/PUSH_PAUSED` 在位), 仅本地 commit。
- 本轮**他人遗留**一并修: `docs/api-surface.baseline.txt` 重钉(+1/-0 行, 见 §6 边界 ⑥ 与 §4)。
- **全量测试**: 首跑 **1858 中 1 红**(`PublicApiSurfaceTests`)⇒ 重生基线后 **1858/1858 绿**(`eval/rover/r540/logs/tests-full.txt` / `tests-full-after-baseline.txt`)。
- **下轮候选 (R541)**: ① `g1` 类长任务的**自测/修复回路**(单发不成立; 候选形态 = 让管道在长任务上允许「写→自测→按 rc 修复」而**不**退回旧路径的多轮 LLM 往返) ② role 轴的质量增益需要一个**能区分**的题面(现题面两臂同分 ⇒ 无分辨力) ③ `wythoff/life` 失败族是否由题面规格不完整导致(需要非同源 oracle 判) ④ 全量测试基线补齐 ⑤ 外部列( codex)的窗间方差归因: 是上游 relay 抖动还是 codex 自身重试策略。
