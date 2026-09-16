#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q42 · 登记表行追加 (exp1q41.* 三条能力) —— 幂等 + 序列化器逐字节复现断言 + 读回校验。

纪律 (R409/R-Q39/EXP1-Q40): 程序化改写登记表前先断言「序列化器逐字节复现原文件」; 不成立即改用文本插入,
绝不静默重排整份文件。追加行只补「前一行的逗号」, 末行后不得加逗号; 重跑不重复插入。
另加: 每条新行的 evidence_path / covers 全部**存在性 fail-closed** (不存在的证据 = 不得登记)。
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
REG = ROOT / 'docs' / 'verification-registry.json'

ROWS = [
    {
        "id": "exp1q41.tail-lf-gate-promoted-default-on",
        "level": "L2",
        "capability": ("提交面尾 LF 闸 **转正为默认开** (`${AGENTFRAMEWORK_TAIL_LF_GUARD:-1}`): 关闸改为"
                       "**显式 opt-out** (值 `0`)。转正同时履行**期望时效义务** —— 原控制「默认档放行坏清单」"
                       "在转正后即过期 (刷新前首跑实测 E5 FAIL / 9-10), 已改为「默认档 ⇒ 拦下 (rc=1)」并"
                       "**新增显式关闸臂** (E5b: 显式 0 ⇒ rc=0 放行) 承担「关闸真不跑」的机制断言; "
                       "两臂期望 rc **相反** ⇒ 不可同时空过。判据不放宽 (只换过期期望)。"),
        "evidence_cmd": "python3 eval/capability/exp1-q40/selftest_q40_taillf.py",
        "evidence_path": "eval/capability/exp1-q40/selftest_q40_taillf.json",
        "negative_control": ("前态控制 5/5 (`nc_prestate_q42.py`: 前态 sha ecd363d 为 HEAD 祖先 ∧ 仅含旧 check 名 "
                             "⇒ 归档 E5 FAIL 可归属前态字节; 现盘含新名 ∧ 显式关闸臂; 归档 mtime < 现盘; "
                             "两臂期望 rc 相反) ∧ 器具 11/11 (E5 默认档 rc=1 / E5b 显式关 rc=0 / E6 显式开 rc=1 / "
                             "E7 合规 rc=0 / E8 真仓 violations=0)。"),
        "covers": ["eval/capability/exp1-q31/instruments/tail_lf_guard.py",
                   "tools/hooks/pre-commit",
                   "eval/capability/exp1-q40/selftest_q40_taillf.py",
                   "eval/capability/exp1-q42/nc_prestate_q42.py"],
        "owner_round": "EXP1-Q41",
    },
    {
        "id": "exp1q41.tail-lf-replay-falsepositive-zero",
        "level": "L2",
        "capability": ("尾 LF 契约的**全历史回放分类** (当前版判据 × 历史字节; 预注册判据 FAIL 照原样保留, 分类读数"
                       "标 `checks_posthoc`): 37 处违规**全部**为单一原因码 `tail_lf_missing` (无 CRLF/BOM 型) "
                       "⇒ 「合法但含标记」样本**误报 = 0**; 契约引入点**机取** (`git log -S TAIL_CONTRACT`, 禁写死) "
                       "= e9445d4 ⇒ 36 契约前 / 1 契约后; 相邻提交尾 LF 形态 {True:10, False:27} ⇒ 非规范态成簇。"
                       "扩面读数: 200 提交 / 4529 文本 blob / 1405 违规 ⇒ 命中率 0.5950 > 阈 0.02 ⇒ "
                       "**BROADEN_REJECTED** (作用面维持声明常量, 不预建扩面)。"),
        "evidence_cmd": "python3 eval/capability/exp1-q42/verify_replay_archive_q42.py",
        "evidence_path": "eval/capability/exp1-q42/replay_archive_verify_q42.json",
        "negative_control": ("证据件形态本身的负控: `replay_q41_scopeA_classified.json` 含 HEAD 相关字段 "
                             "(`head_ct`/`post_contract_window.*`) ⇒ 重跑**字节必变** (实测 sha 由 c6dbd4d1 变 "
                             "48f65d03) ⇒ 该件**不得作冻结 pin** (否则下轮必报 FROZEN_EVIDENCE_DRIFT), "
                             "证据改取输入不变归档 + 确定性校验器 (V6 同输入重算两遍字节相同)。"
                             "回放器自身缺陷的负控留痕: D1 违规列表**截断归档** (首版 `viol[:20]` ⇒ 报 37 而归档 20, "
                             "分类器静默在子集上工作; 修后全量归档, V2 断言总体不缩小); D2 「下一次触碰」**方向反** "
                             "(`--skip=1` 逆序 ⇒ 取到上一次; 修后 `--reverse` 全序定位 index∓1); D3 写侧运行时探针 "
                             "**VOID** (scratch 与源逐字节相同 ⇒ 写入器根本没写, 靠守恒断言抓到) ⇒ 写侧结论改由静态派生承担。"),
        "covers": ["eval/capability/exp1-q41/tail_lf_replay_q41.py",
                   "eval/capability/exp1-q41/classify_q41.py",
                   "eval/capability/exp1-q41/replay_q41_scopeA.json",
                   "eval/capability/exp1-q41/replay_q41.json",
                   "eval/capability/exp1-q42/verify_replay_archive_q42.py"],
        "owner_round": "EXP1-Q41",
    },
    {
        "id": "exp1q41.drift-notice-paired-controls",
        "level": "L2",
        "capability": ("冻结 pin 的「**归档自洽 ∧ 工作区漂移**」**通知件** (可见项, 永不判红 —— 提交闸不得被工作区"
                       "半成品卡死): 漂移只出通知行 + 计数, 不阻断提交; 真仓干净态**零输出** (零噪声)。与"
                       "「脏净解耦的重审」成对使用 (字节漂移可重审 ≠ 记录树外/未入库)。"),
        "evidence_cmd": "python3 eval/capability/exp1-q41/selftest_q41_drift.py",
        "evidence_path": "eval/capability/exp1-q41/selftest_q41_drift.json",
        "negative_control": ("成对控制 4/4: 夹具注入 (HEAD≠现盘, 现场选取 `eval/bge/r404/csharp-fusion-replay.json`) "
                             "⇒ `FROZEN_EVIDENCE_DRIFT=1` ∧ 通知件 2 行可见 ∧ 退出码 0; 真仓干净态 ⇒ 漂移 0 ∧ "
                             "零输出; 同 scratch 假 pin ⇒ rc=2 (红路未被关掉); **真登记表零写入** (sha12 前后相等)。"),
        "covers": ["eval/capability/exp1-q41/selftest_q41_drift.py",
                   "eval/capability/exp1-q41/commit_face_notice_q41.py",
                   "eval/capability/bind_evidence.py"],
        "owner_round": "EXP1-Q41",
    },
]


def detect_form(raw, doc):
    """形态反解 (与 bind_evidence.detect_json_form 同一纪律): 形态的唯一权威 = 现盘文件。

    EXP1-Q42 实证: 本族脚本长期硬编码 indent=1, 而登记表现盘自 R500 起为 indent=2 ⇒ 硬编码形态的
    写侧要么 fail-closed 拒写 (通路死亡), 要么静默重排整份文件。反解失败 ⇒ 仍 fail-closed (rc=3)。
    """
    tail = "\n" if raw.endswith("\n") else ""
    for indent in (1, 2, 4, None):
        for asc in (False, True):
            try:
                if json.dumps(doc, indent=indent, ensure_ascii=asc) + tail == raw:
                    return {'indent': indent, 'ensure_ascii': asc, 'tail': tail}
            except (TypeError, ValueError):
                continue
    return None


def main():
    raw = REG.read_text(encoding='utf-8')
    doc = json.loads(raw)
    # 1) 序列化器逐字节复现断言 (形态**由现盘反解**, 不硬编码缩进)
    form = detect_form(raw, doc)
    print('SER_ASSERT=%s (form=%s)' % ('OK' if form else 'FAIL', form))

    # 2) 证据存在性 fail-closed
    missing = []
    for r in ROWS:
        for rel in [r['evidence_path']] + list(r['covers']):
            if not (ROOT / rel).exists():
                missing.append('%s -> %s' % (r['id'], rel))
    if missing:
        print('EVIDENCE_MISSING=%d ⇒ 拒绝登记' % len(missing))
        for m in missing:
            print('  ! %s' % m)
        return 3

    have = {r.get('id') for r in doc['rows']}
    added = [r for r in ROWS if r['id'] not in have]
    if not added:
        print('IDEMPOTENT=OK (0 行新增; 全部已存在)')
        return 0
    if not form:                        # 兜底: 只做文本插入, 不重排整份文件
        print('⇒ 形态反解失败 ⇒ 改用文本插入 (本脚本未实现, fail-closed)')
        return 3

    doc['rows'].extend(added)
    out = json.dumps(doc, indent=form['indent'], ensure_ascii=form['ensure_ascii']) + form['tail']
    REG.write_text(out, encoding='utf-8', newline='')
    back = json.loads(REG.read_text(encoding='utf-8'))
    ids = [r['id'] for r in back['rows']]
    ok = all(r['id'] in ids for r in added) and len(back['rows']) == len(doc['rows'])
    tail_ok = REG.read_bytes().endswith(b'\n')
    print('ADDED=%d READBACK=%s rows=%d tail_LF=%s' % (len(added), 'OK' if ok else 'FAIL',
                                                       len(back['rows']), tail_ok))
    for r in added:
        print('  + %s (%s) -> %s' % (r['id'], r['level'], r['evidence_path']))
    return 0 if (ok and tail_ok) else 2


if __name__ == '__main__':
    sys.exit(main())
