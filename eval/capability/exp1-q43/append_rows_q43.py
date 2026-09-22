#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q43 · 登记表追加件：R638 面健康三态归属轮（承 AN.11 候选并轮）。

登记纪律（承 R409 程序化改写铁律 + EXP1-Q42 的 `indent` 教训）：
  ① 写前断言序列化器**逐字节复现**原文件（形态由现盘反解，不硬编码缩进）；
  ② 只追加行、不重排；③ 幂等（id 已存在即跳过）；④ 写后读回校验 + 尾 LF 核对。

用法: python3 eval/capability/exp1-q43/append_rows_q43.py [--apply]
"""
import json
import hashlib
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REG = ROOT / 'docs/verification-registry.json'


def sha12(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()[:12]


def detect_form(raw, doc):
    for indent in (1, 2, 4, None):
        for asc in (False, True):
            for tail in ('\n', ''):
                try:
                    if json.dumps(doc, indent=indent, ensure_ascii=asc) + tail == raw:
                        return {'indent': indent, 'ensure_ascii': asc, 'tail': tail}
                except (TypeError, ValueError):
                    continue
    return None


COVERS = [
    'eval/capability/exp1-q43/dag-r638.md',
    'eval/capability/exp1-q43/prereg_q43.json',
    'eval/capability/exp1-q43/census_q43.py',
    'eval/capability/exp1-q43/census_q43.json',
    'eval/capability/exp1-q43/face_before_q43.txt',
    'eval/capability/exp1-q43/face_scoped2_q43.json',
    'eval/capability/exp1-q43/face_scoped3_q43.json',
    'eval/capability/exp1-q43/formgate_q43b.txt',
    'eval/capability/exp1-q42/verify_replay_archive_q42.py',
    'eval/capability/exp1-q42/nc_prestate_q42.py',
]

ROWS = [
    {
        'id': 'r638.exp1q43-face-health-triage',
        'level': 'L3',
        'owner_round': 'R638',
        'capability': (
            'EXP1-Q43 卫生/器具轮：**器具面红项三态归属**（self / foreign / pre_existing）+ **冻结 pin 定向重审**。'
            '零产品源码改动 / 零新臂 / 零远端 / 零新增夹具语义。'
            '真机全量面读数 = **可判据 19/29 通过**（信息项 2/2 单列，31 器 / 68 命令），'
            '落盘 `eval/capability/instruments-check.json`；与仓内最近登记读数（R516 时代 27/29）**不可相减，只做逐条差集**。'
            '归属：**self 4 条**（两件 Q42 器具加负控臂未刷绑定 ⇒ `hooks.pre-commit` / `bind_evidence.check`；'
            '全量面重写其语义投影件 ⇒ `r444.instrument-acceptance`；面输出污染 ⇒ `exp1q31.stage-guard-hook`）已修；'
            '**foreign 1 条**（`external.contrast-exec-precondition` 冻结 pin 滞后于 R631 器具改动 `af9bb7ae`）定向 repin，'
            '`pin_status` 保持 `frozen`、只刷 `artifact_sha12` `28770b831e52→67fba76283b7`（3 次独立重跑同字节 ⇒ 确定性）；'
            '**pre_existing 6 条**逐条点名结转（`exp1q31.cap-headroom` / `exp1q38.dir-node-archive` / `r444.prefilter-precheck` / '
            '`r444.analyze` / `r446.judge-precheck` / `exp1q2.docref-selftest`）另加 `external.contrast-interaction-kpi` 声明字段异常。'
            'AN.11 候选结论：#6 两器入面（31→33）**被面自身容量闸否决**'
            '（`P2 余量不足: soft_cap/log_bytes=1.318 < K_MIN=2.00 ⇒ 扩面前先复测并抬阈值`）⇒ 登记行不落盘；'
            '#1 序列化形态统一**预注册被证伪**（606 件含 `indent=1`，其中活通路 8 件 ≠ 0）⇒ 零改动；'
            '#5 产物件尾 LF **结转**（R481 以来新增 253 件，220 件缺尾 LF = 87.0%）。'
        ),
        'evidence_cmd': (
            'python3 eval/capability/instruments_check.py && '
            'python3 eval/capability/instruments_check.py --only hooks.pre-commit --out eval/capability/exp1-q43/face_scoped2_q43.json && '
            'python3 eval/capability/instruments_check.py --only exp1q31.cap-headroom,exp1q31.stage-guard-hook,'
            'exp1q38.dir-node-archive,external.contrast-exec-precondition,external.contrast-interaction-kpi '
            '--out eval/capability/exp1-q43/face_scoped3_q43.json && '
            'python3 eval/capability/exp1-q43/census_q43.py && '
            'python3 eval/capability/bind_evidence.py --check && '
            'python3 eval/capability/exp1-q42/verify_replay_archive_q42.py --neg-control && '
            'python3 eval/capability/exp1-q42/nc_prestate_q42.py --neg-control'
        ),
        'evidence_path': 'docs/evidence/RF0001/R638-exp1q43-face-health.md',
        'evidence_generated_with': {
            'evidence_kind': 'artifact',
            'pin_status': 'live',
            'pin_reason': 'worktree-only',
            'artifact_sha12': None,
            'instrument': 'eval/capability/exp1-q43/census_q43.py',
            'instrument_sha12': sha12('eval/capability/exp1-q43/census_q43.py'),
            'binding': 'audit-pin',
            'audited_by_round': 'R638',
        },
        'covers': COVERS,
        'negative_control': (
            '成对/负向控制（现场执行，读数入 `face_scoped2_q43.json` / `face_scoped3_q43.json` / `census_q43.json`）：'
            '① **两件新器具的有牙负控**：`verify_replay_archive_q42.py --neg-control` 只篡改 V1 依赖的输入（一条违规行的原因码）'
            '⇒ rc=**2** 且 `red_checks=[\'V1_scopeA_single_reason_no_false_positive\']`；'
            '`nc_prestate_q42.py --neg-control` 把对照物换成浮动 `HEAD` ⇒ rc=**2** 且 `red_checks` ⊇ `{N1_pre_sha_is_ancestor_and_differs}`。'
            '二者**未捕获时退 0**（⇒ 面侧 `nc_expect:nonzero` 判红）⇒ 非空心。'
            '② **面级成对**：`hooks.pre-commit` 修前 rc=1 → 修后 rc=0（同一命令、同一树态差集只有声明）；'
            '`bind_evidence --check` 违规 2 → 0。'
            '③ **确定性**：`external.contrast-exec-precondition` 的冻结件 3 次独立重跑 sha12 同为 `67fba76283b7`（`repin_preview_q43.txt`）。'
            '④ **归属控制**：`self` 只在单轮动作时间线内成立；`foreign` 钉不可变提交号 `af9bb7ae`（HEAD 祖先）；'
            '其余记 `pre_existing` 且逐条点名，未用「红数下降」掩盖。'
        ),
        'note': (
            '轮次工件: eval/capability/exp1-q43/{dag-r638.md, prereg_q43.json, census_q43.py, census_q43.json, '
            'face_before_q43.txt, face_scoped_q43.json, face_scoped_q43.txt, face_scoped2_q43.json, face_scoped2_q43.txt, '
            'face_scoped3_q43.json, face_scoped3_q43.txt, formgate_q43.txt, formgate_q43b.txt, regtest_q43.txt, '
            'bind_check_before_q43.txt, bind_check_after_q43.txt, bind_apply_q43.txt, repin_preview_q43.txt, repin_apply_q43.txt, '
            'append_rows_q43.py} + eval/capability/exp1-q42/{verify_replay_archive_q42.py, nc_prestate_q42.py}（加 `--neg-control`）'
            ' + docs/evidence/RF0001/R638-exp1q43-face-health.md + 计划面 AN.12/AN.13 + 文献台账 §35。'
            '诚实边界: 面读数取自**脏工作区**（83 件历史未跟踪件在场）⇒ 与干净态不可直接比；'
            '`cap-headroom` 的 log_bytes（76.4 MB）构成**未定因**；两件新器具登记行**未落盘**（扩面受闸）；'
            '零 src/ 改动 ⇒ 无能力分数、无 kpi.jsonl 行（与 Q39–Q41 同例）；未 push（推送暂停令）。'
        ),
    },
]


def main():
    raw = REG.read_text(encoding='utf-8')
    doc = json.loads(raw)
    form = detect_form(raw, doc)
    print('SER_ASSERT=%s (form=%s)' % ('OK' if form else 'FAIL', form))
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
    if not form:
        print('⇒ 形态反解失败 ⇒ 文本插入未实现 (fail-closed)')
        return 3
    if '--apply' not in sys.argv:
        print('DRY-RUN (未加 --apply): 将新增 %d 行: %s' % (len(added), [r['id'] for r in added]))
        return 0
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
