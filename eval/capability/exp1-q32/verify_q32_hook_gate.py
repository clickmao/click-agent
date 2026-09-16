#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q32 · C3 钩子面机检: 重审闸入 pre-commit 的 6 项验证 (含零回归与两类负控)。

A. 默认关**零回归**: HEAD 版钩子 vs 现盘钩子, 同 staged 集 ⇒ stdout+rc **逐字节相同**;
B. env=1 + 真仓 (干净) ⇒ 放行 rc=0;
C. 负控 1: 注入 stale pin 的**临时登记表** (AGENTFRAMEWORK_REAUDIT_REGISTRY) ⇒ rc=1 拦下;
D. 负控 2: 登记表路径不存在 ⇒ 守卫 rc=3 ⇒ 钩子 fail-closed 拦下 (不静默放行);
E. 空心钩子反证: 去掉 Q32 块的钩子副本 ⇒ 同 C 场景**放行** ⇒ 证明该块是承重的 (不是装饰);
F. 真仓状态快照 (registry sha12 / staged 集 / 钩子 sha12) 一并落盘。
退出码: 0 全过 / 2 断言失败 / 3 环境失败。
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=False).stdout.strip() or os.getcwd()
HOOK = 'tools/hooks/pre-commit'
REG = 'docs/verification-registry.json'


def sha12(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()[:12]


def run_hook(path, env_extra=None, cwd=ROOT):
    env = dict(os.environ)
    for k in ('AGENTFRAMEWORK_REAUDIT_GUARD', 'AGENTFRAMEWORK_REAUDIT_REGISTRY'):
        env.pop(k, None)
    if env_extra:
        env.update(env_extra)
    p = subprocess.run(['bash', path], cwd=cwd, capture_output=True, text=True, env=env)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def main():
    res, bad = {}, 0
    before = '/tmp/q32_hook_before.sh'
    with open(before, 'w') as f:
        f.write(subprocess.run(['git', 'show', 'HEAD:' + HOOK], cwd=ROOT, capture_output=True,
                               text=True).stdout)
    hollow = '/tmp/q32_hook_hollow.sh'
    body = open(os.path.join(ROOT, HOOK), encoding='utf-8').read()
    start = body.find('# EXP1-Q32: 器具/记录 pin 重审闸')
    hollow_body = (body[:start] + 'exit 0\n') if start > 0 else body
    open(hollow, 'w').write(hollow_body)

    # A. 默认关零回归 (逐字节)
    ra, oa = run_hook(before)
    rb, ob = run_hook(os.path.join(ROOT, HOOK))
    res['A_default_off_zero_regression'] = {'rc_before': ra, 'rc_after': rb, 'stdout_identical': oa == ob,
                                            'ok': ra == rb and oa == ob}
    bad += 0 if res['A_default_off_zero_regression']['ok'] else 1
    print('A 默认关零回归: rc %d→%d, stdout 逐字节相同=%s %s'
          % (ra, rb, oa == ob, 'OK' if res['A_default_off_zero_regression']['ok'] else 'FAIL'))

    # B. env=1 + 真仓 (干净) ⇒ 放行
    rc, out = run_hook(os.path.join(ROOT, HOOK), {'AGENTFRAMEWORK_REAUDIT_GUARD': '1'})
    res['B_enabled_clean_registry'] = {'rc': rc, 'ok': rc == 0, 'tail': out[-200:]}
    bad += 0 if rc == 0 else 1
    print('B 开启+真仓: rc=%d %s' % (rc, 'OK' if rc == 0 else 'FAIL'))

    # C/D/E. 负控
    tmp = tempfile.mkdtemp(prefix='q32-hookgate-')
    try:
        doc = json.load(open(os.path.join(ROOT, REG), encoding='utf-8-sig'))
        tgt = None
        for r in doc['rows']:
            g = r.get('evidence_generated_with') or {}
            if g.get('instrument') and g.get('instrument_sha12'):
                r['evidence_generated_with']['instrument_sha12'] = 'deadbeef0000'
                tgt = r['id']
                break
        injected = os.path.join(tmp, 'registry-injected.json')
        json.dump(doc, open(injected, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        rc_c, out_c = run_hook(os.path.join(ROOT, HOOK),
                               {'AGENTFRAMEWORK_REAUDIT_GUARD': '1', 'AGENTFRAMEWORK_REAUDIT_REGISTRY': injected})
        res['C_nc_stale_pin_blocked'] = {'rc': rc_c, 'injected_row': tgt, 'blocked': rc_c != 0,
                                         'ok': rc_c == 1 and 'BLOCKED(EXP1-Q32' in out_c}
        bad += 0 if res['C_nc_stale_pin_blocked']['ok'] else 1
        print('C 负控(注入 stale pin 行=%s): rc=%d 拦下=%s %s'
              % (tgt, rc_c, 'BLOCKED(EXP1-Q32' in out_c, 'OK' if res['C_nc_stale_pin_blocked']['ok'] else 'FAIL'))

        rc_d, out_d = run_hook(os.path.join(ROOT, HOOK),
                               {'AGENTFRAMEWORK_REAUDIT_GUARD': '1',
                                'AGENTFRAMEWORK_REAUDIT_REGISTRY': os.path.join(tmp, 'nope.json')})
        res['D_nc_registry_missing_failclosed'] = {'rc': rc_d, 'ok': rc_d == 1}
        bad += 0 if rc_d == 1 else 1
        print('D 负控(登记表缺失): rc=%d fail-closed=%s %s' % (rc_d, rc_d == 1, 'OK' if rc_d == 1 else 'FAIL'))

        rc_e, out_e = run_hook(hollow, {'AGENTFRAMEWORK_REAUDIT_GUARD': '1',
                                        'AGENTFRAMEWORK_REAUDIT_REGISTRY': injected})
        res['E_hollow_hook_counterproof'] = {'rc': rc_e, 'ok': rc_e == 0,
                                            'note': '去掉 Q32 块的钩子在同场景放行 ⇒ 该块承重'}
        bad += 0 if rc_e == 0 else 1
        print('E 空心钩子反证: rc=%d 放行=%s %s (证明该块是检出它的唯一原因)'
              % (rc_e, rc_e == 0, 'OK' if rc_e == 0 else 'FAIL'))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    staged = subprocess.run(['git', 'diff', '--cached', '--name-only'], cwd=ROOT, capture_output=True,
                            text=True).stdout.split()
    payload = {'round': 'EXP1-Q32', 'schema': 'hook-gate-verdict/1', 'checks': res,
               'n_checks': 5, 'n_failed': bad,
               'registry_sha12': sha12(os.path.join(ROOT, REG)),
               'hook_sha12': sha12(os.path.join(ROOT, HOOK)), 'staged_n': len(staged)}
    with open(os.path.join(ROOT, 'eval/capability/exp1-q32/verdict_q32_hook_gate.json'), 'w',
              encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False, indent=1) + '\n')
    print('HOOK_GATE=%s (%d/%d) 落盘 eval/capability/exp1-q32/verdict_q32_hook_gate.json'
          % ('PASS' if bad == 0 else 'FAIL', 5 - bad, 5))
    return 0 if bad == 0 else 2


if __name__ == '__main__':
    sys.exit(main())
