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
