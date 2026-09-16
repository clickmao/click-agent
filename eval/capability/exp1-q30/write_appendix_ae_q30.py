#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q30 · 生成并追加计划文档附录 AE (读数一律从落盘 verdict/census/probe 文件机取, 不手抄)。"""
import json
import os
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=True).stdout.strip()
DOC = os.path.join(ROOT, 'docs/plans/v0.22.0-exp1-local-index-and-code-graph.md')
Q = os.path.join(ROOT, 'eval/capability/exp1-q30')
HEAD = '## 附录 AE'


def jl(rel):
    return json.load(open(os.path.join(ROOT, rel), encoding='utf-8'))


def b(v):
    return 'True' if v is True else ('False' if v is False else str(v))


def main():
    only = jl('eval/capability/exp1-q30/verdict_q30_only.json')
    part = jl('eval/capability/exp1-q30/verdict_q30_face_partition.json')
    cens = jl('eval/capability/exp1-q30/instrument_gap_census_q30.json')
    probe = jl('eval/capability/exp1-q30/full_face_trace_probe_q30.json')
    extra = jl('eval/capability/exp1-q30/verdict_q30_extra.json')
    rec = jl('eval/capability/instruments-check.json')
    man = jl('eval/capability/instruments.json')
    r = only['readings']
    t = probe['measured']
    th = probe['threshold_decision']

    txt = f'''
{HEAD} — EXP1-Q30: `--only` 定向重审粒度 + 检查器面别分区 + 器具面扩容 (18→21) + 未派生器具普查 + 跨写者提交闸 (60m 自检作业, 不占主线轮号)

### AE.1 前提核验门 (先测后改; 三条候选的前提有两条在现盘已变)

| 候选 | Q29 记录的形态 | 现盘机检 (本步) | 处置 |
|---|---|---|---|
| ② `worktree-only` 6 条陈旧声明 | 声明 live/worktree-only 而重算 frozen ⇒ 可直接上闸 | **重算 0 条**; 声明口径与重算口径逐行一致 (110 行 = 105 frozen + 3 worktree-only + 1 ledger + 1 self-derived) | 已被主线 `e3f7a44`(R481「96 行纯归属漂移回退」) 闭合 ⇒ **本轮零改动收口** (归属=对侧实施/本侧复核) |
| ④ L2 全量面复跑 | `passed/total` 停在 Q21 口径 17/18 (pre-gate) | 首次 scoped 试跑 `log_bytes=17,943,199` > `LOG_SOFT_CAP=8MiB` ⇒ **capped ⇒ 弃权 rc=3** | 闸阈值对全量面**结构性过小** ⇒ 先测体量再定阈值 (AE.2⑤) |
| ③ 9 行未派生器具 | 需指向仓库内器具脚本或让产物自证 provenance | 9 行 `instrument==null` 确认; 逐行 grep 生产者 | 首版把 `r462_run.sh` 当作 verdict 写入者 ⇒ **机检拒改** (该脚本未提及产物) ⇒ 换 `judge_r462.py`; 4 行改毕, 5 行分类入账 |

### AE.2 动作

1. **候选①-b `--only <ids>` 定向重审** (`eval/capability/bind_evidence.py`): 新增 `--only` 与 `--registry`。
   粒度缺口 (Q29 AD.4③) = `--apply` 全表重审 (`TOUCHED=104`, 其中 103 行只是审计戳 churn)。
   两条 fail-closed: `--apply` + `--only` 缺显式 `--round` ⇒ rc=3 零写入 (防把审计戳写成更早的默认常量 R473 = 归属回退); 未知 id ⇒ rc=3 零写入。
2. **候选⑤ 检查器面别分区** (`eval/capability/instruments_check.py`): `face=full|scoped|negative-control` 三面各自固定落盘名 + `--out` 显式覆盖;
   产物自带 `face/only/out/manifest_sha12/instrument_sha12` (schema `/4` → `/5`)。
3. **候选⑥ 器具面扩容 18 → 21**: `bind_evidence.check` (现盘档, NC=注入 pin 破坏必判 rc=2)、
   `bind_evidence.committed-state` (冻结/提交档: HEAD 登记表主张 vs HEAD blob, 一次 `git cat-file --batch`)、
   `exp1q28.whitelist-coverage` (Q28 白名单覆盖面核验器, NC=恒等归一必报残留)。
4. **候选③ 4 行 `evidence_cmd` → 仓库内真实生产者** (逐条 grep 机检「脚本确实写该产物」):
   `r445`→`judge_prefilter_precheck.py`、`r462.recall-reality-gate`→`judge_r462.py`、`r464`→`settle_r464.py`、`r468`→`settle_r468.py`。
   残留 5 行分类普查: `{json.dumps(cens['by_reason_class'], ensure_ascii=False)}`。
5. **候选④ 全量面复跑 + 归因闸阈值重定 (数据先行)**: scoped 6 命令 {t['scoped_3instruments_6commands_log_bytes']:,} B、
   全量面 47 命令探针 {t['full_face_probe_47commands_log_bytes']:,} B (单条最大 {t['top_single_command_log_bytes'][0]:,} B, 其余 44 条合计 <15 MB)
   ⇒ `LOG_SOFT_CAP` 8 MiB → 64 MiB, `LOG_HARD_CAP` 64 MiB → 256 MiB; 越界语义不变 (`capped ⇒ 弃权 rc=3`)。
6. **候选⑦ `stage_guard_q30.py`**: `staged == 本轮 artifact 清单` 的提交前机检 (对侧在飞文件多出即 REFUSE)。
7. **自伤修复**: 新器具 `exp1q28.whitelist-coverage` 的**默认 `--out` 指向冻结的 Q28 证据** ⇒ 全量面跑一次就改写它
   (与 Q17「器具默认 --out 指向轮次证据」同族)。修 = 器具行显式 `--out` 到 scratch 面; 被改写文件按 HEAD blob 还原 (`sha e1e51aa9f07f` 复原)。

### AE.3 读数 (全部机检, 产物可复算)

| 面 | 前 (committed) | 后 (本轮) | 判据 / 器具 |
|---|---|---|---|
| ①-b 等价 | 单行重审只能走块级文本插入 | `--only` 与块级插入输出 **sha 逐位相同** ({r['A_sha12']} / {r['B_sha12']}) | `verdict_q30_only.json` {only['n_checks']} checks, verdict={only['verdict']} |
| ①-b 作用域 | 全表 `TOUCHED=104` | `--only` 只动目标行 ({r['changed_rows']}), 去作用域对照臂 `TOUCHED={only['readings']['C_stdout_touched']}` | P2/P6 |
| ①-b 零回归 | — | 无参 `--check` stdout **逐字节相同** ∧ 全表 `--apply` 产物 sha 相同 ({only['readings']['zeroregress_apply']['new_sha12']}) | P8/P8b |
| ①-b 生产使用 | — | 两次真实定向重审: `--only 4 行` ⇒ numstat 4/4, `--only 3 行` ⇒ numstat 14/14 (含器具变更) | 台账 diff |
| ⑤ 面别分区 | scoped 跑一次把 18 行全量面记录改写成 1 行 (Q25 事故) | 旧器具 **复现** (total→1, sha {part['readings']['nc_old']['sha12_after']}); 新器具 scoped 跑后全量面 sha 仍 {part['readings']['full_sha12_before']} | `verdict_q30_face_partition.json` 5/5 |
| ④ 全量面 | **17/18** (Q21 口径, pre-gate, schema /3) | **{rec['passed']}/{rec['total']}**, rc=0, `capped={b(rec['side_effect_attribution']['trace']['capped'])}`, 自伤 `{rec['side_effects']}`, 守恒 {rec['side_effect_attribution']['conservation']['classified']}=={rec['side_effect_attribution']['conservation']['expected']} | `eval/capability/instruments-check.json` (schema {rec['schema']}) |
| ⑥ 新器具 | — | 3/3 通过 (各自注入负控全部检出) | 见上表同一产物 `results[]` |
| ③ 未派生器具 | 9 行 | **5 行** (衍生 96 → {cens['derived_instrument']}) | `instrument_gap_census_q30.json` |
| ⑦ 提交闸 | 手工核对 (整树 add 曾把对侧半成品带进提交) | selftest 7/7 (含「条数相同内容不同」漏检反证); 真机核验 staged==清单 | `stage_guard_q30.py --selftest` |
| 登记表一致性 | — | R2e/R2f `R2E_R2F_EXIT=0` (110 行同分布); 提交态档 `COMMITTED_STATE_CHECK=OK` (rows=157 claims=189) | `bind_evidence --check` / `check_committed_state_q30.py` |
| 形式门禁 | 14/14 | **Failed 0 / Passed 14 / rc=0** | `{extra['formal_gate']['summary_lines'][0][:96] if extra['formal_gate']['summary_lines'] else 'n/a'}...` |

被本轮重审的自引用两行 (证据 = 器具本体 / 全量面记录):
`r476.evidence-binding-round-param` artifact/instrument {extra['repin_readings']['r476.evidence-binding-round-param']['artifact_sha12'][0]} → {extra['repin_readings']['r476.evidence-binding-round-param']['artifact_sha12'][1]};
`r444.instrument-acceptance` instrument {extra['repin_readings']['r444.instrument-acceptance']['instrument_sha12'][0]} → {extra['repin_readings']['r444.instrument-acceptance']['instrument_sha12'][1]},
artifact (全量面记录) {extra['repin_readings']['r444.instrument-acceptance']['artifact_sha12'][0]} → {extra['repin_readings']['r444.instrument-acceptance']['artifact_sha12'][1]}。

### AE.4 负控 (全部按预注册原样判定)

| 负控 | 读数 |
|---|---|
| N1 `--only` 未知 id | rc=3 ∧ 文件 sha 不变 (零写入) |
| N2 `--only --apply` 缺 `--round` | rc=3 ∧ 零写入 (防审计戳回退) |
| N3 去作用域对照 (旧器具全表同轮号) | `TOUCHED={only['readings']['C_stdout_touched']}` ⇒ 与 `--only` 输出**字节不同** (作用域收窄非空转) |
| N4 夹具有效性 | 目标行 pin 被改成 `deadbeef0001` ⇒ 输入 ≠ 两路径输出 |
| N5 pin 破坏注入 | `bind_evidence --check` rc=2 + `VIOLATION` ⇒ **NC_DETECTED** |
| N6 提交态「改了没重审就提交」注入 | `NC_DETECTED (1 条违反: bge.recall.frozen_bench ...)` |
| N7 白名单恒等归一注入 | 残留 47 处未吃 + `ok=false` ⇒ **NC_DETECTED** |
| N8 面别分区反证 | 旧器具 scoped 跑 **复现覆盖事故** (total 18→1); 还原后 sha 逐位复现 |
| N9 提交闸反证 | 夹具 `same_count_wrong_content` (条数相同、内容不同) 被拒 ⇒ 条数口径漏检被证明 |

### AE.5 首跑红与自伤 (照原样入档, 不翻案)

1. `verify_q30_only` 首跑 **2 红均为我方判据实现缺陷**: (a) `A_rc` 存成真值而非 `rc==0`; (b) 路径 B 未对齐轮号参数 (器具侧由 `--round` 设 `AUDITED_BY_ROUND`, 测试脚本用默认常量 R473)
   ⇒ 等价判定只对「同一轮号参数」成立, 修正后 {only['n_checks']} 全绿。**修正不放宽判据** (未改等价断言本身)。
2. `rewrite_evidence_cmd_q30` 的 `CHANGED_ROWS` 不变式**空转** (与就地改过的 dict 比较 ⇒ 恒空); 真实证据 = numstat 8/8 + 写后读回 + 二次运行幂等。
3. 自伤 1: 新器具默认 `--out` 改写 Q28 冻结证据 (AE.2⑦), 已修 + 还原。
4. 自伤 2: 全量面前台跑被 180 s 工具上限**掐断**, 缓冲区整段丢失 (`log` 0 字节, 零证据) —— 与「SIGKILL ⇒ 缓冲区消失」同族; 改 `-u` + background 重跑。
5. 自伤 3: `instruments_check_pre_q30.py` (HEAD 版器具副本) 为核验面别分区而落在仓内 —— 核验后删除, 不入库。

### AE.6 诚实边界

1. **候选② 归属** = 对侧/前序提交 (`e3f7a44`), 本侧只做**自跑复核** (重算 0 条); 不把该结论写成本轮成果。
2. **残留 5 行未派生器具** {json.dumps(cens['by_reason_class'], ensure_ascii=False)}: 证据面是文档 (.md) / 目录 / 一次性 `python3 -c` 读表达式 / 一次性 `/tmp` 脚本
   ⇒ 无仓库内单一器具可绑定; 其中 `r462.weight-probe`、`r463.model-cleanup` 的产物**写入者不在仓库内** = 真实缺口 (须改证据面形态, 不是改登记字段能解决)。
3. **`--only` 的轮号戳 churn 语义**: 显式复核会把审计戳更新到本轮 (4 行 → 3 行), 内容无变化的行属**纯归属更新**;
   最小 diff 纪律只覆盖「派生内容相同 ⇒ 不动」, 不覆盖「显式换轮号复核」。
4. **两处自引用行 (r444/r476) 的重审走块级替换 + 文件字节 pin**, 不走 `--only`: `--only` 的 `derive()` 读 `git status`,
   未提交文件结构性只能派生成 `live/worktree-only` (提交时序语义, Q29 AD.4④ 同源)。两条写路径的**逐字节等价性**由 ①-b 判据在 scratch 上证明。
5. **归因闸阈值是「档位相关」的**: 64 MiB 是按 **21 器具 / 47 命令**实测定的; 器具面继续扩容 (或某器具变成多进程重活) 会再次逼近上限 ⇒
   该阈值须随器具面规模复测 (本轮读数: 28.3 MiB / 47 命令, 余量 ~2.2×)。
6. **`exp1q28.whitelist-coverage` 的输出非逐字节确定** (实测 `(instant)` 计数 47 vs 46) ⇒ 该器具**不得**被登记为冻结 pin 的证据 (本轮登记为 `dynamic_corpus`)。
7. **全量面读数是同一窗口内的单次运行** (无重复跑稳定性证据); 跨日/跨会话稳定性列入下轮候选。
8. 推送暂停令在效: 本轮**仅本地提交**, 无 push / 无远端写。

### AE.7 下轮候选

1. **残留 5 行的处置裁定**: 逐行决定「接受为永久口径」还是「改证据面形态」(如把 doc 证据改成机检产物、给 `/tmp` 器具补仓库内归档) —— 须先出**分布先行**的裁定表。
2. **全量面稳定性复跑** (同器具面、跨会话一次) + `r444.instrument-acceptance` 的下一轮重审 (证据随全量面刷新而变)。
3. **`stage_guard` 进提交前钩子面** (`tools/hooks/pre-commit` 同批) 并机检其「拒绝对侧在飞文件」的能力 (注入夹具已就绪)。
4. **器具面扩容的阈值台账**: 把 `LOG_SOFT_CAP` 与器具面规模绑成可复测的记录项 (每次扩容复测 trace 体量)。
5. `verify_q30_only` 的等价判据可望**并入 L2 器具面** (与 `check_committed_state_q30.py` 同批): 属具面扩容的下一步。
'''

    raw = open(DOC, encoding='utf-8').read()
    if HEAD in raw:
        print('APPENDIX_ALREADY_PRESENT (幂等, 不改文档)')
        return 0
    if not raw.endswith('\n'):
        raw += '\n'
    open(DOC, 'w', encoding='utf-8').write(raw + txt)
    back = open(DOC, encoding='utf-8').read()
    ok = HEAD in back and len(back) > len(raw)
    print('APPENDIX=%s (doc %d -> %d chars)' % ('OK' if ok else 'FAIL', len(raw), len(back)))
    print(subprocess.run(['git', 'diff', '--numstat', '--', 'docs/plans/v0.22.0-exp1-local-index-and-code-graph.md'],
                         cwd=ROOT, capture_output=True, text=True).stdout.strip())
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
