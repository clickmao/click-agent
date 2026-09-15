#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q19 · L2 登记前置读数: 逐候选跑『正控』与『机械负控』, 只落读数, 不写登记表。

纪律: 先读数后登记 —— 只有 (正控 rc==expect ∧ 负控判红) 双证成立的候选才允许写进
eval/capability/instruments.json; 证不出外部负控入口的候选如实记 pending_nc。

负控两种形态 (与 instruments_check.py 的 nc_expect 语义一致):
  'nonzero'      —— 直接调器具, 期望其**拒绝** (rc!=0)
  'detect:XXX'   —— 调**检测器脚本**, 期望其检出并打印 XXX (rc==0 且含 XXX)
用法: python3 eval/capability/exp1-q19/l2_probe.py
"""
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path('/home/agentuser/AgentFramework')
OUT = ROOT / 'eval/capability/exp1-q19/l2_probe.json'
ABSENT = 'eval/capability/exp1-q19/_absent_corpus.jsonl'                      # 不存在 ⇒ 检验 fail-closed
VOID_ARM = 'eval/capability/exp1-q18/arm_v270_VOID_self_include/citations.jsonl'  # Q18 已判 VOID 的冻结臂

CAND = [
    {
        'id': 'exp1q11.other-bucket-decompose',
        'file': 'eval/capability/exp1-q11/other_bucket_decompose.py',
        'inputs': ['eval/capability/exp1-q10/citations.jsonl',
                   'eval/capability/exp1-q10/attribution_q10.json'],
        'pos': 'python3 eval/capability/exp1-q11/other_bucket_decompose.py --selftest',
        'pos_substr': 'RESULT: PASS',
        'negs': [('absent-corpus', 'nonzero',
                  f'python3 eval/capability/exp1-q11/other_bucket_decompose.py --citations {ABSENT} '
                  '--out eval/capability/exp1-q19/_q11_nc.json')],
    },
    {
        'id': 'exp1q15.unit-axis-guard',
        'file': 'eval/capability/exp1-q15/unit_axis_guard.py',
        'inputs': ['eval/capability/exp1-q10/probe_v260.py',
                   'eval/capability/exp1-q10/citations.jsonl'],
        'pos': 'python3 eval/capability/exp1-q15/unit_axis_guard.py --selftest',
        'pos_substr': 'SELFTEST 10/10 pass',
        'negs': [('absent-cites', 'nonzero',
                  f'python3 eval/capability/exp1-q15/unit_axis_guard.py --run --cites {ABSENT} '
                  '--json eval/capability/exp1-q19/_q15_nc.json'),
                 ('void-arm-cites', 'nonzero',
                  f'python3 eval/capability/exp1-q15/unit_axis_guard.py --run --cites {VOID_ARM} '
                  '--json eval/capability/exp1-q19/_q15_nc2.json')],
    },
    {
        'id': 'exp1q15.unit-axis-guard-q16',
        'file': 'eval/capability/exp1-q16/unit_axis_guard.py',
        'inputs': ['eval/capability/exp1-q10/probe_v260.py',
                   'eval/capability/exp1-q10/citations.jsonl'],
        'pos': 'python3 eval/capability/exp1-q16/unit_axis_guard.py --selftest',
        'pos_substr': 'SELFTEST 14/14 pass',
        'negs': [('absent-cites', 'nonzero',
                  f'python3 eval/capability/exp1-q16/unit_axis_guard.py --run --cites {ABSENT} '
                  '--json eval/capability/exp1-q19/_q16_nc.json')],
    },
    {
        'id': 'exp1q17.archive-field-provenance',
        'file': 'eval/capability/exp1-q17/archive_field_provenance.py',
        'inputs': ['eval/capability/exp1-q10/citations.jsonl',
                   'eval/capability/exp1-q10/attribution_q10.json',
                   'eval/capability/exp1-q16/verdict_q16.json'],
        'pos': 'python3 eval/capability/exp1-q17/archive_field_provenance.py --selftest '
               '--out eval/capability/exp1-q19/l2runs/verdict_q17.json '
               '--fixtures-out eval/capability/exp1-q19/l2runs/selftest_q17.json',
        'pos_substr': 'checks 15/15',
        'negs': [('void-arm-archive', 'nonzero',
                  f'python3 eval/capability/exp1-q17/archive_field_provenance.py --archive {VOID_ARM} '
                  '--out eval/capability/exp1-q19/_q17_nc.json '
                  '--fixtures-out eval/capability/exp1-q19/_q17_nc_fx.json'),
                 ('absent-archive', 'nonzero',
                  f'python3 eval/capability/exp1-q17/archive_field_provenance.py --archive {ABSENT} '
                  '--out eval/capability/exp1-q19/_q17_nc2.json '
                  '--fixtures-out eval/capability/exp1-q19/_q17_nc2_fx.json')],
    },
    {
        'id': 'exp1q18.rebuild-constructor',
        'file': 'eval/capability/exp1-q18/build_q18_probe.py',
        'inputs': ['eval/capability/exp1-q10/probe_v260.py'],
        'pos': 'python3 eval/capability/exp1-q18/build_q18_probe.py',
        'pos_substr': 'BUILDER_OK',
        'negs': [('mutated-source-version', 'detect:NC_OK',
                  'python3 eval/capability/exp1-q19/nc_rebuild_mutated.py')],
    },
    {
        'id': 'exp1q13.index-scope-out-classifier',
        'file': 'eval/capability/exp1-q13/index_scope_out_classify.py',
        'inputs': [],
        'pos': 'python3 eval/capability/exp1-q13/index_scope_out_classify.py --selftest --no-write',
        'pos_substr': '"all_pass": true',
        'negs': [],
        'expect_pending': True,
        'pending_reason': '内部已含 mutated_copy 缺陷对（原/变异语料根对照），但缺**外部可调用**的缺陷注入入口 ⇒ 本轮记 pending_nc，下一轮补入口再登记（不补假负控）',
    },
]


def sha12(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()[:12]


def run(cmd, timeout=600):
    p = subprocess.run(['bash', '-lc', cmd], cwd=str(ROOT), capture_output=True,
                       text=True, timeout=timeout)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def judge(expect, rc, out):
    if expect == 'nonzero':
        return rc != 0
    if isinstance(expect, str) and expect.startswith('detect:'):
        return rc == 0 and expect[7:] in out
    return rc == 0


def main() -> int:
    rows, unpaired = [], 0
    for c in CAND:
        f = ROOT / c['file']
        sha_before = sha12(c['file']) if f.exists() else None
        rc, out = run(c['pos'])
        pos_ok = (rc == 0) and (c['pos_substr'] in out)
        rec = {'id': c['id'], 'file': c['file'], 'file_sha12_before': sha_before,
               'pos_cmd': c['pos'], 'pos_rc': rc, 'pos_substr': c['pos_substr'],
               'pos_substr_found': c['pos_substr'] in out, 'pos_pass': bool(pos_ok),
               'pos_tail': out.strip().splitlines()[-3:] if out.strip() else [],
               'inputs': [], 'negs': []}
        for p in c['inputs']:
            rec['inputs'].append({'path': p, 'sha12': sha12(p) if (ROOT / p).exists() else None})
        for name, expect, cmd in c['negs']:
            nrc, nout = run(cmd)
            rec['negs'].append({'name': name, 'expect': expect, 'cmd': cmd, 'rc': nrc,
                                'nok': bool(judge(expect, nrc, nout)),
                                'tail': nout.strip().splitlines()[-3:] if nout.strip() else []})
        rec['file_sha12_after'] = sha12(c['file'])
        rec['file_unchanged_by_pos'] = (rec['file_sha12_before'] == rec['file_sha12_after'])
        rec['verified_pair'] = bool(pos_ok and rec['negs'] and
                                    all(n['nok'] for n in rec['negs']) and
                                    rec['file_unchanged_by_pos'])
        rec['pending_nc'] = bool(c.get('expect_pending'))
        if not rec['verified_pair']:
            unpaired += 1
        rows.append(rec)
        print(f"{'PAIR-OK ' if rec['verified_pair'] else 'PAIR-NO '} {rec['id']:34s} "
              f"pos_rc={rc} substr={rec['pos_substr_found']} "
              f"nc={[(n['name'], n['rc'], n['nok']) for n in rec['negs']]} "
              f"file_unchanged={rec['file_unchanged_by_pos']}")
        if not pos_ok:
            print('    pos tail:', rec['pos_tail'])
        for n in rec['negs']:
            if not n['nok']:
                print('    nc tail:', n['name'], n['tail'])

    doc = {'schema': 'exp1-l2-probe/1', 'owner_round': 'EXP1-Q19',
           'manifest': 'eval/capability/instruments.json', 'candidates': rows,
           'verified_pairs': sum(1 for r in rows if r['verified_pair']),
           'total_candidates': len(rows), 'unpaired': unpaired}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f"\nL2 候选双证: {doc['verified_pairs']}/{len(rows)} 双证成立; 落盘 {OUT.relative_to(ROOT)}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
