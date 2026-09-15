#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""L2 器具验收面执行器 (R444 · docs/reports/endpoint-and-audit-contract.md L2).

逐条跑 instruments.json: 正控(expect_rc + expect_substr) 与 负控(注入缺陷 ⇒ 必须判红)。
未过 L2 的器具, 其读数不得进台账。产出 eval/capability/instruments-check.json (含器具文件 sha256)。

EXP1-Q19 扩展 (L2 全字段机检, 契约 §L2):
  * `version`            —— 器具版本: 器具内声明值, 或 'content-sha12:<hash>' (由文件字节派生)
  * `version_source`     —— 'declared' | 'content-sha12'  (机检: 与 version 形态一致)
  * `instrument_sha12`   —— 器具文件 sha256[:12]; 机检**重算比对** (漂移 ⇒ 判红)
  * `input_fingerprint`  —— [{path, sha12}] 输入语料指纹; 机检**重算比对** + 路径必须存在
  * `kpi_quad`           —— 口径四元组 (registry schema: 单位/分母/真值源/口径档)
  自检: `--fingerprint-drift-inject` 在内存中篡改首条被选行的指纹期望值 ⇒ 机检必须判红 (rc!=0)。
        这是**机检规范自身**的注入缺陷负控 —— 不配负控的机检是空心的。

用法: python3 eval/capability/instruments_check.py [--only id1,id2] [--fingerprint-drift-inject]
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
MAN = ROOT / 'eval/capability/instruments.json'
OUT = ROOT / 'eval/capability/instruments-check.json'
OUT_DRIFT = ROOT / 'eval/capability/instruments-check-drift.json'   # 负控模式独立命名空间 (不得覆盖正控证据)
L2_QUAD_KEYS = ('单位', '分母', '真值源', '口径档')


def sha12(p):
    try:
        return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()[:12]
    except Exception:
        return None


def run(cmd):
    p = subprocess.run(['bash', '-lc', cmd], cwd=str(ROOT), capture_output=True, text=True, timeout=900)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


# 器具自身合法写点 (白名单): 全量面**不得**弄脏既有轮次产物 —— 实测事故: q17 的 `--selftest`
# 默认 `--out` 指向轮次证据 `verdict_q17.json`, 跑一次就把 C12 确定性块抹掉 (证据降级)。
FACE_OUTPUTS = {'eval/capability/instruments-check.json', 'eval/capability/instruments-check-drift.json'}
SCRATCH_PREFIXES = ('eval/capability/exp1-q19/l2runs/', 'eval/capability/exp1-q20/l2runs/')


def dirt_set():
    p = subprocess.run(['git', 'status', '--porcelain', '--', 'eval', 'docs'],
                       cwd=str(ROOT), capture_output=True, text=True)
    out = set()
    for ln in (p.stdout or '').splitlines():
        parts = ln.strip().split(None, 1)
        if len(parts) == 2:
            out.add(parts[1].strip().strip('"'))
    return out


def check_l2_fields(e):
    """返回 (ok, detail)。机检字段缺失/漂移一律判红, 不放宽。"""
    d = {}
    ver = e.get('version')
    vsrc = e.get('version_source')
    if not isinstance(ver, str) or not ver:
        d['version'] = 'MISSING'
    elif vsrc == 'declared':
        d['version'] = 'declared:' + ver if not ver.startswith('content-sha12:') else 'BAD_FORM'
    elif vsrc == 'content-sha12':
        d['version'] = ('ok' if ver == 'content-sha12:' + (sha12(e.get('evidence_path')) or '')
                        else 'DRIFT')
    else:
        d['version'] = 'BAD_SOURCE'

    want = e.get('instrument_sha12')
    got = sha12(e.get('evidence_path'))
    d['instrument_sha12'] = 'ok' if (want and got and want == got) else f'DRIFT(want={want} got={got})'

    fps = e.get('input_fingerprint')
    if not isinstance(fps, list):
        d['input_fingerprint'] = 'MISSING'
    else:
        bad = []
        for it in fps:
            p = (it or {}).get('path')
            w = (it or {}).get('sha12')
            if not p:
                bad.append('NO_PATH')
                continue
            g = sha12(p)
            if g is None:
                bad.append(f'MISSING_FILE:{p}')
            elif w != g:
                bad.append(f'DRIFT:{p}(want={w} got={g})')
        d['input_fingerprint'] = 'ok(n=%d)' % len(fps) if not bad else ';'.join(bad)

    quad = e.get('kpi_quad')
    d['kpi_quad'] = ('ok' if isinstance(quad, dict) and all(k in quad for k in L2_QUAD_KEYS)
                     else 'MISSING_KEYS')
    return all(v.startswith('ok') or v.startswith('declared:') for v in d.values()), d


DECL_RE = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*VERSION[A-Za-z0-9_]*)\s*=\s*"([^"]+)"', re.M)


def declared_version(path):
    try:
        txt = (ROOT / path).read_text(encoding='utf-8', errors='replace')
    except Exception:
        return None
    m = DECL_RE.search(txt)
    return m.group(2) if m else None


def main():
    man = json.loads(MAN.read_text(encoding='utf-8'))
    only = None
    if '--only' in sys.argv:
        only = set(sys.argv[sys.argv.index('--only') + 1].split(','))
    drift_inject = '--fingerprint-drift-inject' in sys.argv
    dirt_before = dirt_set()
    res, bad, injected = [], 0, False
    for e in man['instruments']:
        if only and e['id'] not in only:
            continue
        rc, out = run(e['cmd'])
        ok = (rc == e.get('expect_rc', 0)) and (e.get('expect_substr', '') in out)
        l2_ok, l2 = check_l2_fields(e)
        if drift_inject and not injected:
            # 机检自身的注入缺陷负控: 只改**内存中的期望值**, 不动文件
            fps = e.get('input_fingerprint') or []
            if fps:
                fps[0]['sha12'] = 'deadbeef0000'
                l2_ok, l2 = check_l2_fields(e)
                injected = True
                l2['DRIFT_INJECTED'] = 'expect-FAIL'
        rec = {'id': e['id'], 'kind': e['kind'], 'cmd': e['cmd'], 'rc': rc, 'expect_rc': e.get('expect_rc', 0),
               'substr_ok': e.get('expect_substr', '') in out, 'pass': bool(ok), 'sha12': sha12(e['evidence_path']),
               'owner_round': e.get('owner_round'), 'kpi_quad': e.get('kpi_quad'),
               'l2_fields': l2, 'l2_ok': bool(l2_ok)}
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
        rec['pass'] = bool(rec['pass'] and l2_ok and all(n['pass'] for n in ncs))
        if not rec['pass']:
            bad += 1
        res.append(rec)
        line = (f"{'PASS' if rec['pass'] else 'FAIL'} {e['id']:28s} rc={rc} substr={rec['substr_ok']} "
                f"nc={[n['rc'] for n in ncs]} l2={l2}")
        print(line)
        if not rec['pass']:
            print('   ', out.strip().splitlines()[-3:] if out.strip() else '')
            for n in ncs:
                if not n['pass']:
                    print('    nc FAIL:', n['cmd'], '->', n['head'])
    new_dirt = sorted(p for p in (dirt_set() - dirt_before)
                      if p not in FACE_OUTPUTS and not p.startswith(SCRATCH_PREFIXES))
    if new_dirt:
        bad += 1
        print('SIDE-EFFECT: 全量面弄脏既有产物 (证据降级风险) ⇒', new_dirt)
    doc = {'schema': 'instruments-check/2', 'manifest': 'eval/capability/instruments.json',
           'l2_field_checks': True, 'drift_injected': bool(drift_inject and injected),
           'side_effects': new_dirt,
           'passed': len(res) - bad, 'total': len(res), 'results': res}
    target = OUT_DRIFT if drift_inject else OUT
    target.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f"\nL2 器具验收面: {len(res) - bad}/{len(res)} 通过; 落盘 {target.relative_to(ROOT)}")
    if drift_inject and not injected:
        print('DRIFT-INJECT-NOT-APPLIED: 被选行无 input_fingerprint ⇒ 负控未施加 (判红)')
        return 1
    if drift_inject:
        print('DRIFT-INJECT-APPLIED: 机检已判红 (见上表 DRIFT) —— 负控成立')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
