#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXP1-Q30 · 候选⑤ 核验: 面别分区 (定向运行不得覆盖全量面记录)。

判据:
  P1 新器具 scoped 运行 ⇒ 全量面记录 sha **逐位不变** (保护生效) ∧ scoped 面落盘且 face=scoped/only=[...]
  P2 旧器具 (HEAD 版) scoped 运行 ⇒ **复现 Q25 事故**: 全量面记录被改写成 1 行 (sha 变、total 1)
  P3 还原后全量面记录 sha 回到 P1 前的值 (证明 NC 读数来自被覆盖状态, 不是坏仪器)
  P4 scoped 产物自带 manifest_sha12/instrument_sha12 ⇒ 面别与器具版本可机检
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                      check=True).stdout.strip()
Q30 = os.path.join(ROOT, 'eval/capability/exp1-q30')
S = os.path.join(Q30, 'scratch')
FULL = os.path.join(ROOT, 'eval/capability/instruments-check.json')
SCOPED = os.path.join(ROOT, 'eval/capability/instruments-check-scoped.json')
PRE = os.path.join(ROOT, 'eval/capability/instruments_check_pre_q30.py')
NEW = os.path.join(ROOT, 'eval/capability/instruments_check.py')
ONLY = 'bind_evidence.check,bind_evidence.committed-state,exp1q28.whitelist-coverage'


def sha12(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:12]


def run(args):
    p = subprocess.run(['python3'] + args, cwd=ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def main():
    rep = {'round': 'EXP1-Q30', 'checks': {}, 'readings': {}}
    os.makedirs(S, exist_ok=True)
    # 旧器具 (HEAD 版) 落到同目录 ⇒ ROOT 解析一致
    with open(PRE, 'w', encoding='utf-8') as f:
        f.write(subprocess.run(['git', 'show', 'HEAD:eval/capability/instruments_check.py'],
                               cwd=ROOT, capture_output=True, text=True, check=True).stdout)
    backup = os.path.join(S, 'instruments-check-full-backup.json')
    shutil.copy2(FULL, backup)
    sha_full = sha12(FULL)
    rep['readings']['full_sha12_before'] = sha_full
    rep['readings']['full_total_before'] = json.load(open(FULL, encoding='utf-8-sig')).get('total')

    # ---- P2 负控: 旧器具 scoped 运行 ⇒ 覆盖全量面记录 ----
    rc_pre, out_pre = run([os.path.relpath(PRE, ROOT), '--only', 'exp1q17.archive-field-provenance'])
    d_pre = json.load(open(FULL, encoding='utf-8-sig'))
    rep['readings']['nc_old'] = {'rc': rc_pre, 'total_after': d_pre.get('total'),
                                 'face_field': d_pre.get('face'), 'sha12_after': sha12(FULL)}
    rep['checks']['P2_旧器具复现覆盖事故'] = (d_pre.get('total') == 1 and sha12(FULL) != sha_full)

    # ---- P3 还原 ----
    shutil.copy2(backup, FULL)
    rep['checks']['P3_还原到原字节'] = (sha12(FULL) == sha_full)

    # ---- P1 新器具 scoped 运行 ⇒ 全量面记录不受影响 ----
    if os.path.exists(SCOPED):
        os.remove(SCOPED)
    rc_new, out_new = run([os.path.relpath(NEW, ROOT), '--only', ONLY])
    d_sco = json.load(open(SCOPED, encoding='utf-8-sig'))
    rep['readings']['scoped'] = {'rc': rc_new, 'face': d_sco.get('face'), 'only': d_sco.get('only'),
                                 'passed': d_sco.get('passed'), 'total': d_sco.get('total'),
                                 'manifest_sha12': d_sco.get('manifest_sha12'),
                                 'instrument_sha12': d_sco.get('instrument_sha12'),
                                 'schema': d_sco.get('schema'), 'out': d_sco.get('out')}
    rep['checks']['P1_全量面记录不受影响'] = (sha12(FULL) == sha_full)
    rep['checks']['P1b_scoped面独立落盘'] = (d_sco.get('face') == 'scoped'
                                        and d_sco.get('only') == sorted(ONLY.split(','))
                                        and d_sco.get('total') == 3)
    rep['checks']['P4_产物自带面别与器具版本'] = all([d_sco.get('manifest_sha12'),
                                                d_sco.get('instrument_sha12'),
                                                d_sco.get('schema') == 'instruments-check/5',
                                                d_sco.get('out') == 'eval/capability/instruments-check-scoped.json'])
    rep['readings']['new_scoped_stdout_tail'] = out_new.strip().splitlines()[-6:]
    rep['readings']['old_nc_stdout_tail'] = out_pre.strip().splitlines()[-3:]
    rep['verdict'] = 'PASS' if all(rep['checks'].values()) else 'FAIL'
    out = os.path.join(Q30, 'verdict_q30_face_partition.json')
    open(out, 'w', encoding='utf-8').write(json.dumps(rep, ensure_ascii=False, indent=1) + '\n')
    for k, v in rep['checks'].items():
        print('%-30s %s' % (k, 'OK' if v else 'FAIL'))
    print('verdict=%s' % rep['verdict'])
    print(json.dumps(rep['readings'], ensure_ascii=False)[:900])
    return 0 if rep['verdict'] == 'PASS' else 2


if __name__ == '__main__':
    sys.exit(main())
