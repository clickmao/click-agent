#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q35 · 面规模台账追加 (键集与既有行逐键对齐; 幂等 = 同 round+face_record 不重复追加)。

为什么不用 face_cap_headroom.py --append: 该器具把台账行的 `round` **硬编码**为 EXP1-Q31
(源码 line 99) ⇒ 跨轮追加会把本轮的读数记到 Q31 名下 (归属错标)。修它等于改共享器具 ⇒ 器具 sha 变
⇒ 登记表 pin/面记录口径全链需重跑 (按纪律**不顺手改**, 登记为下轮候选)。本轮先落正确归属的行。
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CAP = os.path.dirname(HERE)
ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      cwd=HERE, check=False).stdout.strip() or os.getcwd()
LEDGER = 'eval/capability/face-scale-ledger.jsonl'
ROUND = 'EXP1-Q35'


def main():
    led = os.path.join(ROOT, LEDGER)
    rows = [json.loads(l) for l in open(led, encoding='utf-8-sig').read().splitlines() if l.strip()]
    keys = set(rows[-1].keys())
    face = json.load(open(os.path.join(ROOT, 'eval/capability/instruments-check.json'),
                          encoding='utf-8-sig'))
    man = json.load(open(os.path.join(ROOT, 'eval/capability/instruments.json'), encoding='utf-8-sig'))
    tr = face['side_effect_attribution']['trace']
    soft = 100663296
    sys.path.insert(0, os.path.join(CAP, 'exp1-q22'))
    import importlib.util
    spec = importlib.util.spec_from_file_location('seg', os.path.join(CAP, 'exp1-q22/side_effect_gate.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    soft = getattr(m, 'LOG_SOFT_CAP', soft)
    hard = getattr(m, 'LOG_HARD_CAP', 268435456)
    row = {'round': ROUND, 'face_record': 'eval/capability/instruments-check.json',
           'face_manifest_sha12': face['manifest_sha12'], 'instrument_sha12': face['instrument_sha12'],
           'n_instruments': len(man['instruments']),
           'n_commands': sum(1 + (1 if e.get('nc_cmd') else 0) + (1 if e.get('nc_cmd2') else 0)
                             for e in man['instruments']),
           'log_bytes': tr['log_bytes'], 'capped': tr['capped'],
           'soft_cap': soft, 'hard_cap': hard,
           'headroom': round(soft / tr['log_bytes'], 3), 'k_min': 2.0,
           'kpi_quad': rows[-1]['kpi_quad'],
           'note': ('轮号由本轮显式给定 (面规模器具的 --append 硬编码 EXP1-Q31 ⇒ 已登记为下轮修项); '
                    '读数为本轮面记录实测')}
    assert set(row.keys()) - {'note'} == keys, set(row.keys()) ^ keys
    if any(r.get('round') == ROUND and r.get('face_record') == row['face_record'] for r in rows):
        print('LEDGER_IDEMPOTENT=OK (同键已存在)')
        return 0
    with open(led, 'a', encoding='utf-8') as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + '\n')
    back = [json.loads(l) for l in open(led, encoding='utf-8-sig').read().splitlines() if l.strip()]
    ok = len(back) == len(rows) + 1 and back[-1]['round'] == ROUND
    print('LEDGER_APPENDED rows=%d readback=%s headroom=%s' % (len(back), 'OK' if ok else 'MISMATCH',
                                                              row['headroom']))
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())
