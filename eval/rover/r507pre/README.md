# R507（器具目录 `r507pre`）· 可验收前置（两侧产出物须「可实际执行且正确」）

> 用户令（2026-09-17，逐字）：「**对比 codex 时，一定要让产出物可实际执行并正确才算可验收对比数据的前置状态**」
> 入册：`docs/reports/iteration-master-plan.md` §0-0 **铁律 11**（宪法级）+ 「四条硬条件」④；`docs/external-reference-harness.md` §2 **E7** + **§9**。

## 为什么

判据器（`eval/rover/r5xx/judge_contrast_r5xx.py`）吃的是**已落盘摘要**，判分器内部已经跑过一遍就算数；而两侧产出物形态**不同源**：

| 侧 | `code_source` | 形态 |
|---|---|---|
| 本侧 agent | `artifact` | 真写盘文件（`data/artifacts/py_*.py`） |
| codex-cli | `transcript` | **回复正文里的代码块**（没有文件） |

⇒ 不做独立执行，就存在「读数成立、产出物其实跑不起来」的空心面。本器具把两侧统一到「**磁盘上的可执行文件**」再看两件事：**能不能跑**、**跑出来对不对**。

## 怎么用

```bash
python3 eval/rover/r507pre/exec_precondition.py \
    --taskset eval/rover/r504/taskset-r504.json \
    --codex  "data/probe/probe-cmd:<hash>-seed0-codex-r504.json" \
    --agent  data/probe/probe-agent-seed0-agent-r504.json \
    --label R504 --out eval/rover/r507pre/precondition-r504.json
# 退出码: 0 = 两侧可执行且正确(可验收) / 1 = 未可验收(逐条点名) / 3 = 输入缺失(fail-closed)
```

四步：① 物化（artifact 原样用 / transcript 落盘 `.py`）→ ② 独立执行（`python3 -I -B <file>` + 公开样例 stdin，`rc≠0` 即不可执行）→ ③ 正确性（逐条 hidden 用例 stdin，规范化 stdout 等值，**整题全对**才算正确）→ ④ 输出 `executable_and_correct` + `blocked`。

非程序题（`kind=math` 见证型）没有执行面 ⇒ 记 `exec=not-applicable`，只核正确性（**不冒充执行读数**）。

## 读到的真数据（2026-09-17，只读仓内已落盘摘要）

| 轮 | codex（程序题） | 本侧（程序题） | 前置 |
|---|---|---|---|
| R502 | 4/4 执行且正确 | 4/4 执行且正确 | **可验收**（token −56.3% 成立） |
| R503 | 5/5 | **4/5** — `vm_run` 8/12 用例 | **未可验收** ⇒ −33.5% 记「参考」 |
| R504 | 7/7 | **6/7** — `wythoff` 10/13 用例 | **未可验收** ⇒ −37.8% 记「参考」 |

## L2 自检（正控 + 负控）

```bash
python3 eval/rover/r507pre/nc_precond_r507.py      # 9 例 ⇒ NC_TOTAL=OK
python3 eval/rover/r507pre/selfcheck_r507.py       # 复算真读数 + 写证据 ⇒ PRECOND_SELFTEST=OK
```

9 例 = 正控（两侧好码 ⇒ 绿）· 确定性（两次跑逐字节同）· 错值 · 语法错 · 运行即崩 · 死循环（超时 rc=124）· 非程序题（无执行面）· 缺输入（rc=3）· 产物缺失（`no_code`，不冒充通过）。**注入缺陷必红且必点名**。证据件：`evidence/precondition-selftest.json`。

## 边界

① 本器具只**读**已落盘摘要，不重跑被测对象（真机复跑另轮）；② 「整题全对」口径 ⇒ 部分对判**不正确**；③ 判据器自带的内部判分**不算**该前置；④ 本目录为 R507pre 前置器具轮，不占用主线编号。

## 登记（registry L4 / instruments 成对器具）

- registry 行: `external.contrast-exec-precondition`（**L4**，判据 = 成对正控/负控、注入缺陷必失败**必点名**）
- 器具对: cmd = `python3 eval/rover/r507pre/selfcheck_r507.py`（`PRECOND_SELFTEST=OK`）; nc = `python3 eval/rover/r507pre/nc_oneshot_r507.py`（`detect:NC_DETECTED`，含**正控必须先绿**否则报 `NC_HOLLOW` 弃权）
- 读数: `bind_evidence --check` rc=0 / `R2E_R2F_EXIT=0` · `decl_sweep --check` drifted=0 · 形式门禁 `VerificationForm` 7/7（Failed 0）

## 一次调用（任意轮收口）

```bash
python3 eval/rover/r507pre/exec_precondition.py --round r504   # 自动发现题集 + 两侧落盘摘要
# DISCOVER taskset/codex/agent 行打印实际取用件; rc 0=可验收 / 1=未可验收(点名) / 3=输入缺失
```

已复核：`--round` 与显式传参两路读数**逐字节一致**（R502 `True` / R503 `False(vm_run 8/12)` / R504 `False(wythoff 10/13)`）。
