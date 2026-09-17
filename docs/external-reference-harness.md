# 外部参照对比器具（codex-cli 基准）· 常态开发流程

状态: 生效（R455 起入册）。用户钦定：「可以将对比流程加入开发文档内」。

## 1. 目的
**本文档 = 主线方法的常态载体。** 用户 2026-09-17 钦定更正：**主线 = 用「随机游戏 / 数学难题 / 程序题」的真实开发任务，与外部真值（codex-cli）同环境·同输入对照，对本项目做质量自检**；本节所述器具就是该主线的执行面（见 `iteration-master-plan.md` §0-0 铁律 10）。

用**外部真值**（另一套真实 agent 框架在同一模型上的行为）检验本 agent 的链机制，替代封闭系统自证。
服务判据 = 用户钦定 KPI：**一轮任务总 token ↓≥30%（主要是不必要的 LLM API 请求少了）**；一等上游指标 = **问询次数（澄清轮）**。**KPI 是主线的判据之一，不是主线本身。**

## 2. 硬性铁律（违一条则整批数据作废）
| # | 铁律 | 违反后果 |
|---|---|---|
| E1 | **同环境**：两侧工作目录初始内容逐字节相同（`md5sum` 全员一致后才许开跑） | 数据作废 |
| E2 | **同输入**：两侧逐轮文本出自同一 `suite-turns.json`（同一 `md5`） | 数据作废 |
| E3 | **同模型**：两侧经同一 adapter 打到同一真实模型（`deepseek-flash`） | 数据作废 |
| E4 | **零重试**：`response.completed` 必须带 `input_tokens`/`output_tokens`，否则 codex 侧会重连重发 ⇒ **破坏返回基准**（R454 教训：6 连次） | 数据作废 |
| E5 | **单句输入不算**：输入必须逐模块可测（缓存命中 / 闸门 / 吸收 / 动作），单句「继续下一轮」不构成对照 | 数据作废 |
| E6 | 判分**机械**：产物按字节等值判定，禁模型裁判；只读落盘证据，禁事后补记 | 数据作废 |
| E7 | **可验收前置（用户 2026-09-17 令）**：两侧产出物必须**可实际执行且正确**才构成「可验收对比数据」—— 独立执行路径物化到磁盘 + `python3 -I -B` 实跑 + 逐条隐藏用例机械判对（整题全对）；任一侧不可执行或有错题 ⇒ 该轮读数记**未可验收** | 该轮读数未可验收（禁作验收依据） |

## 3. 标准套件（6 轮，单会话两侧各跑一遍）
| 轮 | 输入 | 覆盖模块 |
|---|---|---|
| T1 | 当前目录下一共有几个 .py 文件？ | 只读理解 / 是否伪执行 |
| T2 | 把 .py 文件的个数写入 count.txt（只要数字） | 动作通道 |
| T3 | x/y/z.txt 顺序合并写 merged.txt | 动作通道 / 多文件 |
| T4 | 读 merged.txt 统计字母数写 stats.txt（chars=<n>） | 多步推理 + 动作 |
| T5 | 继续 | 闸门 / 吸收（driver 类输入） |
| T6 | notes.md 第一行写 first.txt | 动作通道 / 文本处理 |
判分期望：`count.txt=4`、`merged.txt=ALPHA\nBETA\nGAMMA\n`、`stats.txt=chars=14`、`first.txt` 含 `R455 fixture note`。

## 4. 度量（两侧同式）
- 逐调用：`prompt_tokens` / `prompt_cache_hit_tokens` / `completion_tokens` / `tools[]` 数量 / 工具调用数
- 逐轮：远端调用数、澄清问句数（`ASK` 标记）、产物通过数
- 汇总：`Σcached/Σin` 命中率、`x/4` 产物通过、**问询次数**、总 token
- 边界：两侧静态面/工具面不同源 ⇒ **不得**据总量断言「谁更省」；只允许「同输入下行为差异」与本侧内趋势。

## 5. 器具与用法
| 件 | 路径 |
|---|---|
| 透传工具适配器（统一入口 + usage 注入 + 请求/应答全量落盘，Authorization 永不落盘） | `eval/rover/r455/adapter_tools.py` |
| 夹具生成（两侧逐字节同） | `/tmp/r455_setup.sh` |
| 套件 runner（codex 单会话 `exec` + `exec resume`；我方单会话 driver 6 轮） | `eval/rover/r455/run_suite.sh` |
| 判分器（机械等值 + 逐调用 token/cache + 模块表） | `eval/rover/r455/judge_suite.py` |
| 预注册（结构性不变量 + 事后项分离） | `eval/rover/r455/prereg-r455.json` |
| 诊断报告（机制根因） | `docs/reports/agent-chain-diagnosis-r455.md` |

命令：
```
bash /tmp/r455_setup.sh                       # 夹具（两侧同）
bash /tmp/cxprobe/start_adapter.sh            # adapter @48615
bash eval/rover/r455/run_suite.sh             # 两侧 6 轮（后台，禁中断）
python3 eval/rover/r455/judge_suite.py --ns r455
```

## 6. 已知限制（诚实边界）
- codex 侧本机 `bwrap` 不可用 ⇒ 用 `--dangerously-bypass-approvals-and-sandbox` 在 scratch 目录跑（审批/沙箱面不对等，报告须标注）。
- 两侧静态面不同源（codex instructions 16,979 字符 + 9 工具 vs 我方 4,300 字符 + 0 工具）⇒ token 总量不可直接比较，只比行为与同侧趋势。
- 闸门/本地 r1 需 llama-server（内存闸 `MemAvailable≥2650MB`）；未起时记 `n/a`，**不得**计入「闸门通过」。
- 我方无动作环（R455 机制诊断）⇒ 动作类轮次预期 0 产物；该差异是**被测对象**，不是器具缺陷。

## 7. 开发任务对照套件 R502（主线常态执行面 · 2026-09-17）

主线（用户钦定更正）= 用「随机程序 / 数学难题 / 游戏」真实开发任务 + 外部真值（codex-cli，同一真实模型）同环境·同输入对照做质量自检。本节 = 该主线的可复跑执行面。

| 件 | 路径 |
|---|---|
| 冻结题集（**6 题** = 4 程序族 `life_k`(游戏族)/`topo_min`/`vm_run`/`json_mini` + 2 见证型数学族 `witness_sqrt_mod`/`witness_min_counterexample`，seed 20260917，probe 口径 sha `18e7c8dddb54e220`；oracle 正控 **57/57=1.0**；逐族定向 dump 后机合并，禁抽样碰运气） | `eval/rover/r502/taskset-r502.json` |
| 外部真值解法器（codex-cli 作为 probe `command:` 解法：stdin 题面 → stdout 回复；空回 = no_code，不记 0 分） | `eval/rover/r502/codex_solver_r502.py` |
| 对照 runner（同冻结题集 / 同 adapter / 同机械判分；缺任一侧面 ⇒ rc=3） | `eval/rover/r502/run_contrast_r502.sh` |
| 预注册（**先于首跑**，机取 **9 件**哈希 + 6 条判据，禁手抄；题集元信息与正控基线亦机取） | `eval/rover/r502/prereg_r502.json` |
| 对照判分（**只读落盘**，不重跑；产出 `verdict-r502.json`） | `eval/rover/r502/judge_contrast_r502.py` |
| 负控（仪器两端 / fail-closed / 预注册三态 / solver 自检） | `eval/rover/r502/nc_r502.sh` |

- **codex 持久路径**：`~/.agentframework/tools/codex-env/node_modules/.bin/codex`（`@openai/codex@0.154.0`，与 R455 同版 ⇒ 跨轮同版可复现）；旧 `/tmp/codexenv` 仍在，但 /tmp 不可托付。
- **判据（预注册，先于首跑）**：H1 仪器判别力两端（oracle 1.0 ∧ mutation 0.0）· H2 外部真值可用性（0 题 ⇒ 记 `unreported`，禁当 0 分能力）· H3 同输入机检（两侧 `taskset_sha` 相等且 == 预注册值）· H4 同模型机检（adapter 落盘 model 字段）· H5 读数分列（逐题 mode + 两侧 usage 分列，**禁**据 token 总量断言优劣）· H6 fail-closed（缺侧 rc=3）。
- **首跑前负控实测（2026-09-17，全绿）**：程序面 oracle 1/1 ∧ `mutation:json_loose` 0/1；**游戏族** oracle 1/1 ∧ `mutation:life_wrap` 0 整题全对（0/1，且 3 题实测 16/36 用例 ⇒ 变异被隐藏用例抓到）；缺侧 judge rc=3；预注册三态 rc 0/1/3 + 复原 0；solver `--selftest`/`--dry-run` rc=0；生成器自测 `tasks.py --selftest` **47/47**。

```
bash eval/rover/r502/nc_r502.sh                                  # 首跑前负控（本地，不吃真机窗）
bash eval/rover/r502/run_contrast_r502.sh                        # 两侧对照（需内存窗干净 + 无并发真机测量）
python3 eval/rover/r502/judge_contrast_r502.py --codex <cj> --agent <aj> \
        --prereg eval/rover/r502/prereg_r502.json --adapter-log /tmp/r502_env/adapter
```
- **待办**：① ~~真机首跑~~ **已完成（2026-09-17，rc=0 全绿）**：同窗 6 题对照 —— 两侧整题全对 **6/6 = 1.000**（57/57 用例）；codex 14 调用/113,850 tok/97.18 s，本侧 10 调用/**49,709 tok**/21.12 s（tokens −56.3%、调用 −28.6%、墙钟 −78.3%，同质量）；同模型机检 24/24 行 `deepseek-chat`；② 扩面（更多游戏族/见证族 ⇒ 重跑预注册）；③ 效果面残留：R501 t8 本地改写被 guard 以 `question_mark` 拒收（见 improvements v0.98.2）。

### 7.1 首跑读数（真机, 2026-09-17, rc=0）

| 侧 | 整题全对 | 用例 | 调用 | tokens | 墙钟 |
|---|---|---|---|---|---|
| 外部真值 codex-cli（同模型） | 6/6 = 1.000 | 57/57 | 14 | 113,850 | 97.18 s |
| 本侧 AOT agenthost | 6/6 = 1.000 | 57/57 | 10 | **49,709** | **21.12 s** |

判据: H1 仪器判别力 ✓ · H2 外部真值可用 ✓ · H3 同输入机检 ✓（两侧 taskset_sha `18e7c8dddb54e220`）· H4 同模型机检 ✓（落盘 `request.upstream_request.model`；v2 修字段路径）· H5 分列（禁总量断言）✓。
**诚实边界**: 两侧静态面不同源（codex 自带 agentic 循环/沙箱/命令执行）⇒ **禁据 token 总量断言优劣**；n=6 单跑单窗；prereg 标签 `deepseek-flash` 为本仓侧标签、供应商侧名 `deepseek-chat`。

### 8. 证据不可变纪律（R505 入册, 由 R504 实测缺陷倒逼）

R504 判分后被后续候选作业**静默覆盖** 9 个 adapter 文件（同一 `DEMO_OUT` + 进程内计数器重开）⇒ 读数当场成立、事后不可重放。以下四条为对照类实验的硬约束：

1. **命名空间守卫**：目标工作目录与证据目录非空即拒跑（rc=4），且**不启动任何作业**；一次实验一个命名空间（含端口）。
2. **判分只读仓内不可变快照**：阶段结束立即把 adapter 落盘件 `cp` 进仓内 `evidence/<批>/`，并写逐文件 **sha256 冻结清单**；此后判分只吃快照 ⇒ 判分 = 快照的纯函数，可无限次重判（器具改版不必重跑被测对象）。
3. **重放检查**：`check_usage_replay.py --usage <冻结清单> --dir <目录>` 逐文件比对 in/out；失配 rc=2 且**点名**文件。它在**判分后**（另一进程、另一时刻）再跑一次 ⇒ 跨时间第二次取数。R504 实况即被它点名 9 文件。
4. **改版留痕与影响面机检**：判据器/归因器任何改版都要：① 记录旧/新 sha256 与改版范围；② 用**快照重判**给出影响面（冻结判据、用量、质量表须**逐位不变**，只有被声明的判据可变）；③ 影响面超预期 ⇒ 旧读数作废、必须重跑。
5. **禁「内容变化」判新鲜度**：判分器是确定性纯函数，产出可与旧件逐字节相同 ⇒ 判「这次真的跑了」只能用**完成标记**（如自报 `verdict ->`）+ 独立临时产物，不能用 sha 变化。

### 9. 可验收前置 H0：两侧产出物须「可实际执行且正确」（用户 2026-09-17 令）

铁律原文：「**对比 codex 时，一定要让产出物可实际执行并正确才算可验收对比数据的前置状态**」⇒ 入册为本文件 §2 **E7** + 宪法条款 `iteration-master-plan.md` §0-0 **铁律 11**。

**为什么必须**：判据器（`judge_contrast_r5xx.py`）吃的是**已落盘摘要** —— 判分器内部跑过一遍就算数；而两侧产出物形态**不同源**：本侧 = 写盘文件（`code_source=artifact`），codex 侧 = **回复正文代码**（`code_source=transcript`）。不做独立执行就存在「读数成立、产出物其实跑不起来」的空心面。

**怎么做**：`eval/rover/r507pre/exec_precondition.py`
1. **物化**：artifact 文件原样取用；transcript 代码落盘成真 `.py`（两侧统一到「磁盘上的可执行文件」这一形态）；
2. **独立执行**：`python3 -I -B <file>`，公开样例 stdin 实跑，`rc≠0` 即判**不可执行**（超时 rc=124 / 崩溃 rc≠0 都算）；
3. **正确性**：逐条 hidden 用例喂 stdin，规范化 stdout **等值**；**整题全对**才算「正确」（部分对 = 不正确）；
4. **输出**：`executable_and_correct` + `blocked`（逐条点名 `side/tid exec=? cases=?/?`）；退出码 `0 可验收 / 1 未可验收 / 3 输入缺失 fail-closed`。

**真读数复算（2026-09-17，只读仓内已落盘摘要与题集）**
| 轮 | codex（程序题） | 本侧（程序题） | 前置结论 |
|---|---|---|---|
| R502（4 程序 + 2 见证） | 4/4 执行且正确 | 4/4 执行且正确 | **可验收**（`−56.3%` token 读数成立） |
| R503（5 + 3） | 5/5 | **4/5**（`vm_run` 8/12 用例） | **未可验收** ⇒ `−33.5%` 降级为参考读件 |
| R504（7 + 4） | 7/7 | **6/7**（`wythoff` 10/13 用例） | **未可验收** ⇒ `−37.8%` 降级为参考读件 |

⇒ **操作口径**：只有「两侧全跑通 ∧ 全对」的轮次才发**可验收对比读数**；本侧有错题的轮次，其 token/调用降幅一律标「参考（未可验收）」，直到该题产出物修正并**同窗复跑**。

**器具 L2 自检**：`python3 eval/rover/r507pre/selfcheck_r507.py` ⇒ 正控（两侧好码 ⇒ 绿、两次跑逐字节同）+ 负控（错值 / 语法错 / 运行即崩 / 死循环 / 缺输入 / 产物缺失：注入缺陷**必红且点名**）**9/9 通过**；证据件 `eval/rover/r507pre/evidence/precondition-selftest.json`。

**一次调用（任意轮收口用）**：`python3 eval/rover/r507pre/exec_precondition.py --round r504` —— 自动发现 `eval/rover/<r>/taskset-<r>.json` + `data/probe/probe-*-<r>.json` 两侧落盘摘要（`DISCOVER` 行打印实际取用件），rc `0 = 可验收 / 1 = 未可验收(逐条点名 `side/tid`) / 3 = 输入缺失 fail-closed`；读数落 `eval/rover/r507pre/precondition-<r>.json`（**仓内相对路径**，可移植）。已复核 R502/R503/R504：`--round` 与显式传参两路读数**逐字节一致**（`True / False(vm_run 8/12) / False(wythoff 10/13)`）。

### 10. 交互 / 人性化 KPI 对照（R507 补测 · 用户 2026-09-17 问「有对比过提问数量，人性化，等其他 kpi 么」）

**覆盖清单（诚实分栏）**

| KPI | 两侧对照状态 | 真源 |
|---|---|---|
| tokens / 题、tokens / 满分题 | **有**（本侧 `process_metrics`；codex 走中继 usage） | `eval/probe/process_metrics.py` / adapter 快照 |
| 调用数（远端 call）、墙钟 | **有** | adapter 快照 / 各轮 `verdict-*.txt` |
| 整题全对（用例级）+ 可执行前置 | **有**（R507 §9 / 铁律 11） | `eval/rover/r507pre/exec_precondition.py` |
| 轮数 / 首次通过率 / 修复率 / 饱和 | **仅本侧有**（codex = `n/a`，禁按 0 冒充） | `eval/probe/process_metrics.py --multiturn` |
| **提问数量（对用户）** | **本轮补测**（§10.1） | `eval/rover/r507pre/kpi_interaction_r507.py` |
| **人性化（回复面代理）** | **本轮补测**（§10.2） | 同上 |
| **menu 式问询**（`r458` 焦点令） | **本轮补测**（§10.1 末列） | 同上 |
| **内部问询**（`[微步骤隔离问询]`，不骚扰用户但计 token） | **仅本侧有**（codex 自带循环不落此标记 ⇒ 结构不可对照） | 冻结适配器快照 |
| 用户回答频率（真实会话面） | **未测**（需多轮对话题集 / 真实会话，见诚实边界） | — |

**§10.1 提问 / menu（对用户）—— 真读数（2026-09-17，只读已落盘回复与冻结快照）**

| 轮 | 侧 | 题数 | 提问题数(率) | 问号数 | menu 题数(率) |
|---|---|---|---|---|---|
| r502 | agent / codex | 6 / 6 | 0(0.0%) / 0(0.0%) | 0 / 0 | 0(0.0%) / 0(0.0%) |
| r503 | agent / codex | 8 / 8 | 1(12.5%) / 0(0.0%) | 1 / 0 | **1(12.5%) / 2(25.0%)** |
| r504 | agent / codex | 11 / 11 | 1(9.1%) / 1(9.1%) | 1 / 1 | **0(0.0%) / 2(18.2%)** |
| r505a | agent / codex | 11 / 11 | 1(9.1%) / 0(0.0%) | 1 / 0 | **0(0.0%) / 2(18.2%)** |
| r505b | agent / codex | 11 / 11 | 1(9.1%) / 0(0.0%) | 1 / 0 | **0(0.0%) / 1(9.1%)** |
| r505c | agent / codex | 11 / 11 | 1(9.1%) / 0(0.0%) | 1 / 0 | **0(0.0%) / 2(18.2%)** |

⇒ ① **提问数量**：单轮题集下上限 1/题，两侧 0–1 ⇒ **该 KPI 在现题集无区分度**（要真测须多轮对话题集 / 真实会话）。
⇒ ② **menu 式问询（`r458` 焦点令）**：本侧 R504 起 **0/11 = 0%**，codex **9.1–25.0%** ⇒ **未达且低于外部真值**（唯一例外 R503 本侧 1/8）。

**§10.2 人性化（回复面代理）—— 真读数**

| 轮 | 侧 | 人话字/题 | 面板行/题 | 协议帧(轮) | 产物路径泄漏(轮) | 交付代码字(归一) |
|---|---|---|---|---|---|---|
| r502 | agent / codex | 1147.2 / 133.2 | 14.0 / 0.0 | 12 / 0 | 11 / 0 | 12934 / 10438 |
| r503 | agent / codex | 1332.1 / 106.9 | 14.1 / 0.0 | 16 / 0 | 14 / 0 | 16996 / 10791 |
| r504 | agent / codex | 1029.3 / 127.2 | 15.2 / 0.0 | 22 / 0 | 24 / 0 | 16693 / 12290 |
| r505a | agent / codex | 1059.7 / 192.5 | 15.6 / 0.0 | 22 / 0 | 31 / 0 | 20034 / 10343 |
| r505b | agent / codex | 1221.6 / 193.1 | 15.3 / 0.0 | 22 / 0 | 25 / 0 | 22947 / 11201 |
| r505c | agent / codex | 1154.1 / 158.6 | 15.1 / 0.0 | 22 / 0 | 24 / 0 | 25660 / 11388 |

⇒ 本侧用户面回复**每答复 14.0–15.6 行机器面板**（banner / 命令菜单 / `[01] 意图分析` / `[0x] 子任务` / `@chatbox:{…}` 协议帧 / `· ./data/artifacts/…` 落盘路径），codex **三项全 0**。人话字/题 ≈ 6–10× codex ⇒ **可量化的人性化缺口**（面板与遥测帧占据了用户可见面）。

**§10.3 内部问询（本侧结构构成，`r505` a/b/c 冻结快照）**

| 快照 | 调用 | 含内部问询调用(率) | 标记数 | prompt tok(问询占比) | cache 命中/未命中 |
|---|---|---|---|---|---|
| r505 a+b+c (agent) | 58 | **4 (6.9%)** | 4 | 280949 (**1.1%**) | 158080 / 122869 |

⇒ 内部问询**只计 token 不打扰用户**，占比 1.1% ⇒ 不是 token 降幅的杠杆（与 R505 结论一致）。

**器具与用法**
- 回复面：`python3 eval/rover/r507pre/kpi_interaction_r507.py --round r504 r505a`（自动发现 `data/probe/probe-*-<r>.json` + 回复件；读数落 `eval/rover/r507pre/kpi-interaction.json`）
- 内部问询：`python3 eval/rover/r507pre/kpi_interaction_r507.py --adapter-dir eval/rover/r505/evidence/a/adapter-agent …`（吃**冻结快照**，不重跑）
- 口径：问号/menu 只在**剥离代码围栏与面板行之后**的 prose 上计（面板规则由 `src/agent.host/Program.cs:473/562` 与现盘回复反解，见器件 `CHROME_PATTERNS`）
- 自检：`--selftest` ⇒ **SELFTEST=OK**（4 用例：反问+menu 正控 / 围栏内 `?` 不计 / 纯代码 / 本侧面板须被剥离 + codex chrome=0 控制），证据件 `evidence/interaction-kpi-selftest.json`
- 负控：`python3 eval/rover/r507pre/nc_interaction_kpi_r507.py` ⇒ **`detect:NC_DETECTED`**（正控绿 + 两处注入必被抓：取消围栏排除 / 取消面板剥离；正控就红 ⇒ `NC_HOLLOW` 弃权）

**诚实边界（§10）**
1. 「人性化」= **可机检表面代理**（长度 / 面板行 / 协议帧 / 泄漏 / menu 有无），**不是语义人性化**；无机械代理的面（语气、共情、是否答非所问）**未测**。
2. 面板剥离规则 = 源码 + 现盘反解，非语义判据；已用 4 用例自检 + 2 处注入负控，但**新面板形态**可能逃逸 ⇒ 规则改版须重跑对照。
3. 「交付代码字（归一）」对本侧是**上界**（产物含候选 + 回退件）；两侧形态不同源（本侧写盘 / codex 回复内代码），仅作规模参照，**不作质量判据**。
4. **用户回答频率**未测：单轮题集上限 1/题（实测两侧 0–1）⇒ 真测需**多轮对话题集**或真实会话面（`state.db` 1,179 轮），本文件尚无该类题集 ⇒ 记 `unreported`（禁按 0 冒充可比）。
5. codex 侧 `n/a` 项（轮数 / 首通率 / 内部问询）= **结构不可对照**，不是 0。
6. 各轮均为**单窗**读数（R505 a/b/c 为同批 3 窗）；未做跨窗聚合成区间。

### 11. 外部真值结构样本：Fable 5.1 泄露 system（用户 2026-09-17 指定 · R525 重构依据）

- **来源**：`github.com/elder-plinius/CL4R1T4S · ANTHROPIC/Claude-Fable-5.1.md`（用户附的抖音视频未取到页面：短链 302 → 分享页对 curl 返回 404/JS 墙；分析对象 = 视频所指的原始文件本身）。
- **自测读数（不引用二手口径）**：275,723 B / **274,608 字符** / 2,196 行；顶级段 **270** 个（≥1.5k 字符 63 个，<200 字符 122 个）；`<function>` 工具 schema **46** 个，占 161,245→252,856 字符 = **33%**。
- **关键形状**：整份 = **一个逐字节恒定前缀**（唯一变量只有 model/date 行），每轮只做尾部追加；工具 schema 亦在常量区；记忆/隐私规则（何时写、何时不写）是**常量规则**而非每轮材料；环境/文件系统配置收尾；隐形字符检查（私用区 / 变体选择符 / tag 块）全 0。
- **分区序（自测偏移）**：身份/产品 → 儿童安全 → 记忆系统（`preferences_guardrails` 10,784 字符，最大段）→ 隐私/never_store → 行为守则 → 搜索/版权 → **工具 schema(46)** → skills 目录碎片 → network/filesystem 配置。
- **厂商协议侧旁证**：修改 system/工具定义会作废此前思考块；`prefix_mismatch_behavior: drop_block`；缓存读价 0.025× 输入 ⇒「常量在前、只追加」是**协议级约束**，不是风格偏好。
- **映射表（R525 落地，`SessionBaseline` §1..§11）**：身份/产品 → §1 身份与目标 ｜ 安全底线 → §2 安全与诚实底线 ｜ 记忆系统/never_store → §3 记忆与召回规则（新）｜ 行为守则 → §4 行为与输出纪律 ｜ — → §5 工程与执行纪律 ｜ 工具协议 → §6 工具协议（原生工具声明 = 逐调用恒定）｜ skills 目录 → §7 技能菜单与按需加载（新）｜ network/filesystem → §8 环境与工作区 ｜ — → §9 失败模式 / §10 汇报格式 / §11 模块地图。
- **诚实边界（未取用）**：46 个工具的语义细节、UI 卡片工具族、以及「270 段是否分级按需加载」均无证据 ⇒ 不作宣称；本样本是**消费端会话** system（claude.ai），与我方 agent 的运行时形状不可直接等价，只作**结构**对照。

## 参照面固化（2026-09-18）

此前语料与设计抽取件只存在于 `/tmp`（易失）⇒ 已入仓，路径与 sha256 钉子如下（用于复现与防篡改）：

| 文件 | 字节 | sha256 |
|---|---|---|
| `docs/external-reference/claude-fable-5.1-corpus.md` | 275,723 | `c57de521ca050e24…` |
| `docs/external-reference/DESIGN-RATIONALE.md`（七条设计动因） | 4,966 | `24390e5e31a7cc25…` |
| `docs/external-reference/R1-EXTRACT.md`（抽出的 R1 子集） | 3,528 | `27189e1ac964fb52…` |
| `docs/external-reference/proto-{contract,r1prompt,pipeline,demo}.py`（远程真调原型） | 8,581 / 7,062 / 4,733 / 6,925 | `f78eae67` / `858646be` / `e0af4c13` / `0303548b`（前 8 位） |
| `src/agent/contract/StructuredPrompt.cs`（落地侧: `PrefixChars`/`PrefixSha256Pinned`） | — | 钉子随代码 |

对照臂侧（外部真值）：`codex-cli 0.154.0` 持久路径 `~/.agentframework/tools/codex-env/node_modules/.bin/codex`；
四臂脚本 `eval/rover/r531/run_r531.sh`（A0-off / A1-on / A2-merge / **C-codex**），侧驱动 `eval/rover/r511/proj_run_side.py --side codex`。
**验收前置铁律（11）**：`python3 eval/rover/r507pre/exec_precondition.py --round <r>`；`r532` 实测 **rc=3（DISCOVER_FAIL: taskset/codex/agent 三侧皆 None）** ⇒ 该轮单侧读数一律「参考（未可验收）」。
