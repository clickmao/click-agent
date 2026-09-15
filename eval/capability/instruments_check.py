#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L2 器具验收面执行器 (R444 · docs/reports/endpoint-and-audit-contract.md L2).

逐条跑 instruments.json: 正控(expect_rc + expect_substr) 与 负控(注入缺陷 ⇒ 必须非零)。
未过 L2 的器具, 其读数不得进台账。产出 eval/capability/instruments-check.json (含器具文件 sha256)。
用法: python3 eval/capability/instruments_check.py [--only id1,id2]
"""
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
MAN = ROOT / 'eval/capability/instruments.json'
OUT = ROOT / 'eval/capability/instruments-check.json'


def sha12(p):
    try:
        return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()[:12]
    except Exception:
        return None


def run(cmd):
    p = subprocess.run(['bash', '-lc', cmd], cwd=str(ROOT), capture_output=True, text=True, timeout=900)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def main():
    man = json.loads(MAN.read_text(encoding='utf-8'))
    only = None
    if '--only' in sys.argv:
        only = set(sys.argv[sys.argv.index('--only') + 1].split(','))
    res, bad = [], 0
    for e in man['instruments']:
        if only and e['id'] not in only:
            continue
        rc, out = run(e['cmd'])
        ok = (rc == e.get('expect_rc', 0)) and (e.get('expect_substr', '') in out)
        rec = {'id': e['id'], 'kind': e['kind'], 'cmd': e['cmd'], 'rc': rc, 'expect_rc': e.get('expect_rc', 0),
               'substr_ok': e.get('expect_substr', '') in out, 'pass': bool(ok), 'sha12': sha12(e['evidence_path']),
               'owner_round': e.get('owner_round'), 'kpi_quad': e.get('kpi_quad')}
        ncs = []
        for key, exp in (('nc_cmd', 'nc_expect'), ('nc_cmd2', 'nc_expect2')):
            if not e.get(key):
                continue
            nrc, nout = run(e[key])
            spec = e.get(exp)
            if spec == 'any':
                nok = True
            elif isinstance(spec, str) and spec.startswith('detect:'):
                nok = (nrc == 0) and (spec[7:] in nout)
            else:
                nok = nrc != 0
            ncs.append({'cmd': e[key], 'rc': nrc, 'expect': str(e.get(exp)), 'pass': bool(nok),
                        'head': nout.strip().splitlines()[-1][:160] if nout.strip() else ''})
        rec['negative_controls'] = ncs
        rec['pass'] = bool(rec['pass'] and all(n['pass'] for n in ncs))
        if not rec['pass']:
            bad += 1
        res.append(rec)
        line = f"{'PASS' if rec['pass'] else 'FAIL'} {e['id']:28s} rc={rc} substr={rec['substr_ok']} nc={[n['rc'] for n in ncs]}"
        print(line)
        if not rec['pass']:
            print('   ', out.strip().splitlines()[-3:] if out.strip() else '')
            for n in ncs:
                if not n['pass']:
                    print('    nc FAIL:', n['cmd'], '->', n['head'])
    doc = {'schema': 'instruments-check/1', 'manifest': 'eval/capability/instruments.json',
           'passed': len(res) - bad, 'total': len(res), 'results': res}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f"\nL2 器具验收面: {len(res) - bad}/{len(res)} 通过; 落盘 {OUT.relative_to(ROOT)}")
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
