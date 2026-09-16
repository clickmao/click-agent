#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q42 · 文档收口: 计划文档追加 AN.10/AN.11 + improvements.md 顶部加节 (幂等 + 读回校验)。

纪律: 只做**锚点文本插入/追加**, 不重排; 幂等 (重跑不重复插入); 读回校验字段存在。
"""
import hashlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
PLAN = ROOT / 'docs/plans/v0.22.0-exp1-local-index-and-code-graph.md'
IMP = ROOT / 'docs/improvements.md'

AN = """
### AN.10 EXP1-Q42 读数 (AN.9 候选 1/2/4/5/6 并轮 + 转正副作用的**根因修复**)

本轮范围 = AN.9 的 1/2/4/5/6 **全部并入一轮** (候选 3 属对侧)。预注册 `eval/capability/exp1-q42/prereg_q42.json`
(`written_before_any_measurement: true`, M1–M6; 附 `ordering_note`: 内存/占位闸读数与过期探测首跑发生在预注册**之前**,
属**触发探测/环境读数**, 非本轮判据)。

| 候选 | 器具/动作 | 真机读数 | 判据 |
|---|---|---|---|
| AN.9 #1 登记 | `append_rows_q42.py` + `bind_evidence --apply --only` (4 行) + `decl_sweep --apply` | rows **214→217**; numstat 登记表 **80/5** ∧ instruments **2/2**; `RE_AUDITED=1`; `bind_evidence --check` **rc=0** | **M2 PASS** |
| AN.9 #2 形式门禁 | `dotnet test --filter VerificationForm\\|SkillGeneralization\\|DevPlanDocRef` | Failed **0** / Passed **14** / rc=0 (827 ms) | **M3 PASS** |
| AN.9 #4 真实观测窗口 | 真提交 **4e50ba8** 的提交面 | `TAIL_LF_GUARD contract=R481-tail-lf targets=2 violations=0 unresolved=0` ∧ `TAIL_LF_GUARD=OK` ⇒ **拦截 0 次** | **M4 PASS** |
| AN.9 #5 漂移通知件现场 | `commit_face_notice_q41.py --log` (真仓 green check) | **0 行** (干净态零噪声); 现场**未产生** >0 事件 | **M5 未达** (诚实结转) |
| AN.9 #6 扩面收口 | `verify_replay_archive_q42.py` (输入不变归档) | 37 违规**单原因码** / 1405·4529=0.595 > 阈 0.02 ⇒ 维持不扩 | **M6 PASS** |
| (自捕) 期望时效 | `selftest_q40_taillf` 首跑 | **E5 FAIL / 9-10** —— 原期望「默认档放行坏清单」在转正后**过期** | 触发 M1 |

**M1 收口 (转正的期望时效义务)**: E5 改为「默认档 ⇒ 拦下 (rc=1)」并**新增 E5b 显式关闸臂** (显式 `0` ⇒ rc=0 放行);
刷新后 **11/11 PASS**。前态/现态成对负控 **5/5** (`nc_prestate_q42.py`: 前态钉 **ecd363d** 且为 HEAD 祖先 ∧
**仅含旧 check 名** ⇒ 归档的 E5 FAIL 可归属前态字节; 现盘含新名 ∧ 关闸臂; 归档 mtime < 现盘; 两臂期望 rc **相反**)
⇒ **换掉过期期望, 不是放宽判据**。

**根因修复 (本轮最承重, 与候选 1/2 同源)**: `bind_evidence.py` 序列化器**硬编码 `indent=1`**, 而登记表自 **R500** 起
现盘为 `indent=2` (r500 写侧 + R502 rebind 沿用) ⇒ `--apply` 恒 `SER_ASSERT=FAIL` ⇒ **rc=3 = 能力登记通路死亡**
(这才是 AN.9 #1「未做」的真实成因, 不是「对侧在飞」的连带)。修法 = **形态的唯一权威 = 现盘文件**: 新增
`detect_json_form()` 逐字节反解 (indent∈{1,2,4,None} × ensure_ascii∈{False,True}), 命中即按现盘形态写回,
反解失败**仍 fail-closed**。实证: `SER_ASSERT=OK (indent=2, ensure_ascii=False, tail=LF — 形态由现盘反解)`;
定向重审 5 行; 登记表 numstat **80/5** (若沿用旧硬编码写盘 = 5305 行整份重排, 即「静默重排掩盖真实改动」形态);
`r476.evidence-binding-round-param` (器具 = bind_evidence.py) 定向重审 + `decl_sweep --apply` (`RE_AUDITED=1`, numstat 2/2)。

**证据件纪律 (自捕)**: `replay_q41_scopeA_classified.json` 含 **HEAD 相关字段** (`head_ct` / `post_contract_window.*`)
⇒ 重跑**字节必变** (实测 sha `c6dbd4d1`→`48f65d03`) ⇒ 该件**不得作冻结 pin** (否则下轮必报 `FROZEN_EVIDENCE_DRIFT` 噪声)。
处置: 证据改取**输入不变**归档 `replay_q41_scopeA.json` + **确定性校验器** `verify_replay_archive_q42.py`
(只读冻结字节、不读 HEAD、无时间戳; V6 = 同输入重算两遍字节相同, READBACK=OK), classified 件复原到 HEAD 字节。

**两态机制断言 (转正后的关闸语义)**: 默认档/显式 `1` ⇒ 坏清单**拦下** (rc=1 ∧ 报文含闸名); 显式 `0` ⇒ 同坏清单**放行**
(rc=0 ∧ 无闸报文) ⇒ 「关闸真不跑」由 E5b 承担, 两臂期望 rc 相反 ⇒ 不可同时空过。

**诚实边界**: ① M5 的现场 >0 事件**不可达** (真仓干净态) ⇒ 候选**继续结转**, 绝不用夹具读数顶替现场读数;
② 形态分叉**仍在仓内** (普查: 60+ 历史脚本硬编码 `indent=1`, 本轮只修**活通路** `bind_evidence.py`; 其余为已执行的每轮脚本)
⇒ 形态统一须**独立预注册轮** (5305 行形态 diff 会改前后可比性); ③ 转正后真实复核窗口仍小 (契约后 1 次复发, n=1);
④ 写侧**运行时**探针仍 **VOID** ⇒ 「写入器规范」目前仍由静态派生 + 真仓两态 rc=0 承担;
⑤ 本轮未写 `kpi.jsonl` (与 Q39–Q41 同例: 器具/登记轮不是 KPI 序列, 读数落计划文档 + 证据目录);
⑥ 未 push (推送暂停令)。

### AN.11 EXP1-Q42 下轮候选 (逐项: 做/未做 + 原因)

1. **登记表序列化形态统一 (`indent=1` vs `indent=2`)** —— **未做**: 需**独立预注册轮** (5305 行形态 diff 会改可比性);
   本轮只修活通路并留普查读数 (60+ 脚本硬编码 indent=1)。
2. **H6 漂移通知件在真实提交面上的 >0 现场事件** —— **未做**: 真仓干净态不产生该事件; 夹具读数**不得**顶替现场读数 (候选结转)。
3. **写侧运行时探针 (写入器规范) 的运行时读数** —— **未做**: 上轮 VOID 后由静态派生承担;
   重开条件 = 出现可观测的真实写入路径 (非 scratch 副本)。
4. **AN.7 #1 对侧 `r494.capability-face-readonly-audit` P1 闭合** —— **未做**: 属对侧。
5. **产物件写入习惯 (1154 `.json` + 237 `.jsonl` 缺尾 LF)** —— **未做**: 属扩面否决的**重开条件** (写入器统一补尾 LF 后再评估)。
6. **新器具进器具面** (`verify_replay_archive_q42.py` / `nc_prestate_q42.py` 未登记进 `instruments.json` 的 29 件面) ——
   **未做**: 需 `kpi_quad` + 负控对 (`nc_cmd`/`nc_expect`) 设计, 属扩面候选。
"""

IMP_SECTION = """## EXP1-Q42 · 2026-09-17 · 状态: **完成（登记通路复活 + 转正期望时效收口）** · 主题: 尾 LF 闸转正的副作用收口 + exp1q41.* 能力登记

**起因**: EXP1-Q41 把提交面尾 LF 闸由 opt-in **转正为默认开**, 而既有控制件 `selftest_q40_taillf` 的 E5 期望
(「默认档放行坏清单」) 随转正**过期** —— EXP1-Q42 首跑实测 **E5 FAIL / 9-10** (改前真机留档, 非事后追认)。

| 项 | 读数 | 判据 |
|---|---|---|
| 期望时效收口 | E5 → 「默认档拦下」+ 新增 E5b「显式关闸放行」⇒ **11/11 PASS**; 前态负控 **5/5** | PASS |
| 能力登记 | 登记表 **214→217** 行 (`exp1q41.*` ×3, 各带成对控制); `bind_evidence --check` rc=**0** | PASS |
| 形式门禁 | `dotnet test` (VerificationForm\\|SkillGeneralization\\|DevPlanDocRef): Failed **0** / Passed **14** | PASS |
| 真提交面 (4e50ba8) | `TAIL_LF_GUARD contract=R481-tail-lf targets=2 violations=0 unresolved=0` ∧ `TAIL_LF_GUARD=OK` ⇒ 拦截 **0** | PASS |
| 漂移通知件现场 | 真仓干净态 **0 行**; >0 现场事件**不可达** | 未达 (结转) |

**根因修复 (本轮最承重)**: `bind_evidence.py` 序列化器**硬编码 `indent=1`**, 而登记表自 **R500** 起现盘为 `indent=2`
(r500 写侧 + R502 rebind 沿用) ⇒ `--apply` 恒 `SER_ASSERT=FAIL` / rc=3 ⇒ **能力登记通路死亡** (AN.9 #1 的真实成因)。
修法 = 形态的**唯一权威 = 现盘文件**: `detect_json_form()` 逐字节反解 (indent∈{1,2,4,None} × ensure_ascii∈{False,True}),
命中按现盘形态写回, 反解失败仍 fail-closed。登记表改动量 numstat **80/5** (旧硬编码路径会是 5305 行整份重排)。

**证据件纪律 (自捕)**: `replay_q41_scopeA_classified.json` 含 HEAD 字段 (`head_ct` / `post_contract_window.*`)
⇒ 重跑字节必变 (sha `c6dbd4d1`→`48f65d03`) ⇒ **不得作冻结 pin**; 证据改取**输入不变**归档 + 确定性校验器
(`eval/capability/exp1-q42/verify_replay_archive_q42.py`, V6 = 同输入重算两遍字节相同)。

**诚实边界**: ① H6 的 >0 现场事件真仓不可达 (夹具读数不顶替现场读数 ⇒ 候选结转); ② 形态分叉仍在仓内
(60+ 历史脚本硬编码 `indent=1`, 本轮只修活通路) ⇒ 形态统一须独立预注册轮; ③ 转正后真实复核窗口 n=1; ④ 未 push。

"""


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def main():
    plan_raw = PLAN.read_text(encoding='utf-8')
    imp_raw = IMP.read_text(encoding='utf-8')
    plan_before, imp_before = sha(PLAN), sha(IMP)

    if 'AN.10 EXP1-Q42' in plan_raw:
        print('PLAN=IDEMPOTENT (AN.10 已存在)')
    else:
        PLAN.write_text(plan_raw.rstrip('\n') + '\n' + AN, encoding='utf-8', newline='')
        print('PLAN=APPENDED (AN.10 + AN.11)')

    if 'EXP1-Q42 · 2026-09-17' in imp_raw:
        print('IMP=IDEMPOTENT (EXP1-Q42 节已存在)')
    else:
        anchor = '## v0.98.3 · R502'
        if anchor not in imp_raw:
            print('IMP=ANCHOR_MISSING ⇒ 拒绝插入 (fail-closed)')
            return 3
        i = imp_raw.index(anchor)
        IMP.write_text(imp_raw[:i] + IMP_SECTION + imp_raw[i:], encoding='utf-8', newline='')
        print('IMP=INSERTED (顶部, 锚点 %s)' % anchor)

    ok_all = True
    for p, name, fields in ((PLAN, 'PLAN', ['AN.10 EXP1-Q42', 'AN.11 EXP1-Q42', 'M4 PASS', 'M5 未达']),
                            (IMP, 'IMP', ['EXP1-Q42 · 2026-09-17', '登记通路死亡', '80/5'])):
        t = p.read_text(encoding='utf-8')
        miss = [f for f in fields if f not in t]
        tail_lf = p.read_bytes().endswith(b'\n')
        print('%s readback: missing=%s tail_LF=%s sha %s->%s' % (name, miss or 'none', tail_lf,
                                                                 plan_before if name == 'PLAN' else imp_before,
                                                                 sha(p)))
        ok_all = ok_all and not miss and tail_lf
    return 0 if ok_all else 2


if __name__ == '__main__':
    sys.exit(main())
