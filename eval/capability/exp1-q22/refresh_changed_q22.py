#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q22 · 刷新本轮被改动器具行里的字节派生字段 (version / instrument_sha12)。

与 Q21 同源纪律: 只接受**显式 allowlist** (本轮确实改动的器具路径), 不静默刷新;
写前断言「序列化器逐字节复现原文件」(否则拒绝改写 —— 防整份重排把真实改动淹进 diff);
写后读回核对 + 报告残留漂移 (其他行若有漂移即列出)。
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
    readback_ok = all(sha12(c['evidence_path']) == c['after']['instrument_sha12'] for c in changed)
    rep = {'apply': apply, 'allowlist': CHANGED, 'refreshed': changed, 'residual_drift': residual,
           'readback_ok': readback_ok, 'pass': bool(changed and not residual and readback_ok)}
    (HERE / 'refresh_changed_q22.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1) + '\n',
                                                   encoding='utf-8')
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    return 0 if rep['pass'] else 3


if __name__ == '__main__':
    sys.exit(main())
