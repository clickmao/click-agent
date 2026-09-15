#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q21 · 刷新**本轮被改动的器具**行里的字节派生字段 (version / instrument_sha12)。

为什么需要: 登记行里的 `version`/`instrument_sha12` 由器具文件字节派生 ⇒ 本侧一旦改动器具文件
(instruments_check.py 增加输入面语义机检), 该行立刻 DRIFT。**不许静默刷新**——本脚本只接受
显式 allowlist(本轮确实改动的器具路径), 并把 before→after 逐条记入报告与证据。
"""
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REG = ROOT / 'eval/capability/instruments.json'
CHANGED = ['eval/capability/instruments_check.py']      # 本轮显式改动清单 (只此一项)


def sha12(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()[:12]


def main():
    apply = '--apply' in sys.argv
    raw = REG.read_text(encoding='utf-8')
    man = json.loads(raw)
    if apply and (json.dumps(man, ensure_ascii=False, indent=1) + '\n') != raw:
        print('SERIALIZER-NOT-BYTE-IDENTICAL: 拒绝改写')
        return 2
    changed = []
    for row in man['instruments']:
        ep = row.get('evidence_path')
        if ep not in CHANGED:
            continue
        got = sha12(ep)
        before = {'version': row.get('version'), 'version_source': row.get('version_source'),
                  'instrument_sha12': row.get('instrument_sha12')}
        if before['instrument_sha12'] != got:
            row['instrument_sha12'] = got
            if str(before['version']).startswith('content-sha12:') or before['version_source'] == 'content-sha12':
                row['version'] = 'content-sha12:' + got
                row['version_source'] = 'content-sha12'
            changed.append({'id': row['id'], 'evidence_path': ep, 'before': before,
                            'after': {'version': row.get('version'),
                                      'version_source': row.get('version_source'),
                                      'instrument_sha12': row.get('instrument_sha12')}})
    if apply:
        REG.write_text(json.dumps(man, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    back = json.loads(REG.read_text(encoding='utf-8'))
    residual = [{'id': r['id'], 'evidence_path': r['evidence_path']}
                for r in back['instruments'] if r.get('evidence_path') and r.get('instrument_sha12')
                and r['evidence_path'] not in CHANGED and r['instrument_sha12'] != sha12(r['evidence_path'])]
    rep = {'apply': apply, 'allowlist': CHANGED, 'refreshed': changed, 'residual_drift': residual,
           'pass': bool(changed and not residual)}
    (HERE / 'refresh_changed_q21.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1) + '\n',
                                                   encoding='utf-8')
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    return 0 if rep['pass'] else 3


if __name__ == '__main__':
    sys.exit(main())
