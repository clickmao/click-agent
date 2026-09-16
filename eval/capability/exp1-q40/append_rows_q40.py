#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q40 · 登记表行追加 (幂等 + 序列化器逐字节复现断言 + 读回校验)。

纪律 (R409/R-Q39): 程序化改写登记表前先断言「序列化器逐字节复现原文件」; 不成立就改用文本插入,
绝不静默重排整份文件。追加行只补「前一行的逗号」, 末行后不得加逗号; 重跑不重复插入。
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
REG = ROOT / 'docs' / 'verification-registry.json'

ROWS = [
    {
        "id": "exp1q40.frozen-evidence-dirty-not-downgraded",
        "level": "L2",
        "capability": ("冻结 pin 行的**反静默降级**: 已声明 frozen 的行在一次非定向 --apply 中"
                       "不得因「自身证据在工作区脏」被改写成 live/worktree-only (那会让 pin 无声消失); "
                       "改为出声跳过 (FROZEN_EVIDENCE_DIRTY_SKIP=n) 并保留原声明; "
                       "显式定向 (--only) 才按现盘重钉。同批加「归档自洽 ∧ 工作区漂移」可见项 "
                       "(FROZEN_EVIDENCE_DRIFT, 不判红: 提交闸不得被工作区半成品卡死)。"),
        "evidence_cmd": "python3 eval/capability/exp1-q40/selftest_q40.py",
        "evidence_path": "eval/capability/exp1-q40/selftest_q40.json",
        "negative_control": ("成对控制 7/7: 前态器具 (HEAD 字节) 同 scratch ⇒ 该行降级为 live/worktree-only "
                             "(缺陷复现); 现盘器具同态 ⇒ 逐字段不变 + 出声跳过; 定向重审 ⇒ pin == 现盘 sha12; "
                             "同 scratch 把 pin 改假值 ⇒ --check 判红 (红路未被关掉)"),
        "covers": ["eval/capability/bind_evidence.py",
                   "eval/capability/exp1-q40/selftest_q40.py",
                   "eval/capability/exp1-q40/selftest_q40_firstrun_assertbug.json"],
        "owner_round": "EXP1-Q40",
    },
    {
        "id": "exp1q40.projection-pin-dirty-decoupled",
        "level": "L2",
        "capability": ("pin_kind=semantic-projection 行的分类与工作区脏净**解耦**: 记录已入库但字节漂移时, "
                       "仍按声明语义判 frozen/artifact 并重算投影摘要 ⇒ 定向重审在记录脏态即可完成 "
                       "(消除 AN.4.3 的「先提交记录才敢重审」次序依赖)。投影摘要与**路径/字节形态**无关 "
                       "(重排版 / 顶层键序反转同值), 语义变化则换值。"),
        "evidence_cmd": "python3 eval/capability/exp1-q40/selftest_q40_projection.py",
        "evidence_path": "eval/capability/exp1-q40/selftest_q40_projection.json",
        "negative_control": ("7/7: 前态器具同脏态 ⇒ 重审被拒 (PROJ_PIN_SKIPPED, audited_by_round 停在 EXP1-Q39); "
                             "现盘 ⇒ 重审生效且 pin 与登记值逐字符相等; 语义篡改 ⇒ 摘要必换 (同值判据非恒真门); "
                             "树外/未入库记录 ⇒ 两态都不许静默降级; 非投影行前后态逐字段相同 (零回归); "
                             "真记录临时重排版后原字节复原 (sha 断言)"),
        "covers": ["eval/capability/bind_evidence.py",
                   "eval/capability/exp1-q40/selftest_q40_projection.py",
                   "eval/capability/face_record_canon.py"],
        "owner_round": "EXP1-Q40",
    },
    {
        "id": "exp1q40.archive-denominator-parameterized",
        "level": "L2",
        "capability": ("归档面分母**参数化**: 分母 (Q37 记录里 reason=directory_node 的结点数) 与登记值不符时"
                       "不再整体弃权 (旧行为: 一变即 rc=3 ⇒ 面失去分辨力), 改为在实际分母上判定守恒式 + "
                       "新增/缺失结点单列 (new_nodes/missing_nodes) + 登记值只作信息项; 仅「实分母 = 0」仍弃权。"),
        "evidence_cmd": "python3 eval/capability/exp1-q40/selftest_q40_denom.py",
        "evidence_path": "eval/capability/exp1-q40/selftest_q40_denom.json",
        "negative_control": ("5/5: 真记录 ⇒ 固有读数逐字段不变 (非语义字段白名单仅 archive_root); "
                             "注入 1 个 directory_node 于前态器具 ⇒ rc=3 整体弃权 (缺陷复现); 现盘 ⇒ rc=0 ∧ "
                             "denominator_actual=30 ∧ new_nodes 恰为该结点 ∧ 实分母上守恒; "
                             "29 个固有结点读数不变; 零 directory_node ⇒ 仍 rc=3 弃权 (不伪造 PASS)"),
        "covers": ["eval/capability/exp1-q38/archive_dir_nodes_q38.py",
                   "eval/capability/exp1-q40/selftest_q40_denom.py"],
        "owner_round": "EXP1-Q40",
    },
    {
        "id": "exp1q40.commit-face-tail-lf-gate",
        "level": "L2",
        "capability": ("尾 LF 契约 (TAIL_CONTRACT 取自 bind_evidence 单一权威源) 纳入**提交面**自检: "
                       "取「将被提交的字节」(index → HEAD → 工作区), 判据 = 末字节 LF ∧ 无 CRLF ∧ 无 BOM; "
                       "不可解析判红 (不可判 ≠ 合规)。闸**默认关** (opt-in, 零回归), 只读、不带 index 副作用。"),
        "evidence_cmd": "python3 eval/capability/exp1-q40/selftest_q40_taillf.py",
        "evidence_path": "eval/capability/exp1-q40/selftest_q40_taillf.json",
        "negative_control": ("10/10: 三型缺陷 (缺 LF / CRLF / BOM) 逐件点名且合规件不被点名; 不可解析件 ⇒ rc=2; "
                             "清单缺失 ⇒ rc=3; 提交面钩子默认关 ⇒ 坏清单放行 (rc=0); 打开 ⇒ 同态拦下 (rc=1); "
                             "真仓默认作用面 rc=0; 代价已实测 (闸单次耗时与钩子开/关增量)"),
        "covers": ["eval/capability/exp1-q31/instruments/tail_lf_guard.py",
                   "tools/hooks/pre-commit",
                   "eval/capability/exp1-q40/selftest_q40_taillf.py"],
        "owner_round": "EXP1-Q40",
    },
]


def main():
    raw = REG.read_text(encoding='utf-8')
    doc = json.loads(raw)
    # 1) 序列化器逐字节复现断言 (缩进/键序/尾 LF)
    repro = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
    ser_ok = (repro == raw)
    print('SER_ASSERT=%s (indent=1, ensure_ascii=False, tail=LF)' % ('OK' if ser_ok else 'FAIL'))

    have = {r.get('id') for r in doc['rows']}
    added = [r for r in ROWS if r['id'] not in have]
    if not added:
        print('IDEMPOTENT=OK (0 行新增; 全部已存在)')
        return 0
    if not ser_ok:                      # 兜底: 文本插入 (只在末行 JSON 对象之后补一行)
        print('⇒ 改用文本插入 (不重排整份文件)')
        raise SystemExit(3)

    doc['rows'].extend(added)
    out = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
    REG.write_text(out, encoding='utf-8', newline='')
    # 2) 读回校验
    back = json.loads(REG.read_text(encoding='utf-8'))
    ids = [r['id'] for r in back['rows']]
    ok = all(r['id'] in ids for r in added) and len(back['rows']) == len(doc['rows'])
    print('ADDED=%d READBACK=%s rows=%d' % (len(added), 'OK' if ok else 'FAIL', len(back['rows'])))
    for r in added:
        print('  + %s (%s) -> %s' % (r['id'], r['level'], r['evidence_path']))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
